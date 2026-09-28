from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from lessondigest import ingest as ingest_stage
from lessondigest import summarizer
from lessondigest.asr.base import AsrOptions, AsrProvider, build_asr
from lessondigest.chunking import chunk_transcript
from lessondigest.config import AppConfig
from lessondigest.deliver.base import Deliverer
from lessondigest.deliver.file import FileDeliverer
from lessondigest.domain import RunMeta, RunStatus, utc_now_iso
from lessondigest.errors import LessonDigestError, MissingArtifactError
from lessondigest.logging_setup import get_logger
from lessondigest.metrics import MetricsCollector
from lessondigest.storage import FilesystemStorage
from lessondigest.summarize.base import LlmProvider, build_llm
from lessondigest.validate import validate_digest

log = get_logger("pipeline")

STAGES = ("ingest", "asr", "summarize", "validate", "deliver")


@dataclass
class RunResult:
    run_id: str
    status: RunStatus
    digest_md: Path | None = None
    digest_json: Path | None = None
    warnings: list[str] = field(default_factory=list)
    skipped_stages: list[str] = field(default_factory=list)


class Pipeline:
    def __init__(
        self,
        config: AppConfig,
        *,
        storage: FilesystemStorage | None = None,
        asr: AsrProvider | None = None,
        llm: LlmProvider | None = None,
        deliverer: Deliverer | None = None,
    ) -> None:
        self.config = config
        self.storage = storage or FilesystemStorage(config.paths)
        self.asr = asr
        self.llm = llm
        self.deliverer = deliverer or FileDeliverer()

    def run(
        self,
        *,
        audio: Path | str | None = None,
        run_id: str | None = None,
        subject: str | None = None,
        from_stage: str = "auto",
        force: bool = False,
        open_result: bool = False,
    ) -> RunResult:
        if from_stage not in ("auto", *STAGES):
            raise LessonDigestError(f"Неизвестный этап --from: {from_stage}")
        if not audio and not run_id:
            raise LessonDigestError("Укажите --audio или --run")

        if isinstance(self.deliverer, FileDeliverer):
            self.deliverer.open_result = open_result

        start_index = 0 if from_stage == "auto" else STAGES.index(from_stage)

        meta: RunMeta | None = None
        if run_id:
            meta = self.storage.load_run_meta(run_id)
            audio_path = self.storage.resolve(meta.audio_raw)
            checksum = meta.checksum_sha256
            if subject:
                meta.subject = ingest_stage.slugify_subject(subject)
        else:
            source = Path(audio)  # type: ignore[arg-type]
            ingest_stage.validate_source(source)
            checksum = ingest_stage.sha256_file(source)
            run_id = ingest_stage.make_run_id(subject, checksum)
            audio_path = source

        metrics = MetricsCollector(run_id)
        skipped: list[str] = []
        warnings: list[str] = []
        run_meta_path = self.storage.run_dir(run_id) / "run.json"
        is_new_run = not run_meta_path.exists()
        if not is_new_run and meta is None:
            meta = self.storage.load_run_meta(run_id)
        if meta is None:
            meta = RunMeta(run_id=run_id, subject=ingest_stage.slugify_subject(subject), status=RunStatus.CREATED)

        try:
            if start_index <= STAGES.index("ingest") and (is_new_run or force):
                with metrics.time("ingest"):
                    if audio is None:
                        raise MissingArtifactError("Для этапа ingest нужен --audio", stage="ingest")
                    result = ingest_stage.ingest(audio, subject, self.config.paths, checksum=checksum)
                    meta = ingest_stage.build_meta(result, subject, self.config.paths)
                    meta.status = RunStatus.INGESTING
                    audio_path = result.raw_path
            else:
                skipped.append("ingest")

            self._save_meta(meta)

            if self._should_run("asr", start_index, force, artifact=self.storage.transcript_path(run_id)):
                if audio_path is None or not Path(audio_path).exists():
                    raise MissingArtifactError(f"Аудио недоступно: {audio_path}", stage="asr")
                asr = self.asr or build_asr(self.config.asr)
                meta.status = RunStatus.ASR_RUNNING
                meta.progress = 0.0
                meta.progress_stage = "asr"
                self._save_meta(meta)
                with metrics.time("asr"):
                    transcript = asr.transcribe(
                        Path(audio_path),
                        AsrOptions.from_config(self.config.asr),
                        self._reporter(meta, "asr"),
                    )
                if not transcript.text.strip():
                    raise MissingArtifactError("Пустой транскрипт", stage="asr")
                self.storage.save_transcript(run_id, transcript)
                meta.asr_provider = transcript.provider or self.config.asr.provider
                meta.asr_model = transcript.model or self.config.asr.model
                meta.transcript_txt = self.storage.relative(self.storage.transcript_path(run_id))
                if transcript.segments:
                    meta.transcript_segments = self.storage.relative(self.storage.transcript_segments_path(run_id))
                meta.status = RunStatus.ASR_DONE
                meta.progress = 1.0
                metrics.set("transcript_chars", transcript.char_count())
                metrics.set("asr_elapsed_sec", transcript.elapsed_sec)
            else:
                skipped.append("asr")

            self._save_meta(meta)

            if self._should_run("summarize", start_index, force, artifact=self.storage.digest_json_path(run_id)):
                transcript = self.storage.load_transcript(run_id)
                chunking = chunk_transcript(transcript.text, transcript.segments, self.config.chunking)
                if len(chunking.chunks) > 1:
                    self.storage.save_chunks(run_id, chunking)
                    meta.chunks_json = self.storage.relative(self.storage.chunks_path(run_id))
                llm = self.llm or build_llm(self.config.llm, self.config.secrets)
                meta.status = RunStatus.SUMMARIZING
                meta.progress = None
                meta.progress_stage = "summarize"
                self._save_meta(meta)
                with metrics.time("summarize"):
                    digest, markdown, _ = summarizer.summarize(
                        transcript.text,
                        config=self.config,
                        llm=llm,
                        chunking=chunking,
                        on_progress=self._reporter(meta, "summarize"),
                    )
                md_path, json_path = self.storage.save_digest(run_id, digest, markdown)
                meta.digest_md = self.storage.relative(md_path)
                meta.digest_json = self.storage.relative(json_path)
                meta.llm_provider = getattr(llm, "name", self.config.llm.provider)
                meta.llm_model = digest.model or self.config.llm.model
                meta.prompt_version = digest.prompt_version
                meta.status = RunStatus.DIGEST_READY
                meta.progress = 1.0
                metrics.set("digest_chunks", len(chunking.chunks))
                metrics.set("digest_chars", len(markdown))
            else:
                skipped.append("summarize")

            meta.warnings = self._validate(run_id, warnings)
            self._save_meta(meta)

            if meta.digest_md:
                md_path = self.storage.resolve(meta.digest_md)
                json_path = self.storage.resolve(meta.digest_json)
                if md_path and md_path.exists():
                    digest = self.storage.load_digest(run_id)
                    with metrics.time("deliver"):
                        self.deliverer.deliver(run_id, digest, md_path, json_path or md_path)
                    meta.status = RunStatus.DELIVERED
                    meta.progress = 1.0
                    meta.progress_stage = "deliver"
                    self._save_meta(meta)
                else:
                    skipped.append("deliver")
            else:
                skipped.append("deliver")

            metrics.set("audio_duration_sec", meta.duration_sec)
            meta.timings = dict(metrics.timings)
            self._save_meta(meta)
            self.storage.save_metrics(run_id, metrics.snapshot(status=meta.status.value))

            return RunResult(
                run_id=run_id,
                status=meta.status,
                digest_md=self.storage.resolve(meta.digest_md),
                digest_json=self.storage.resolve(meta.digest_json),
                warnings=meta.warnings,
                skipped_stages=skipped,
            )
        except LessonDigestError as exc:
            meta.status = RunStatus.FAILED
            meta.error = f"[{getattr(exc, 'stage', 'unknown')}] {exc}"
            meta.updated_at = utc_now_iso()
            meta.timings = dict(metrics.timings)
            self._save_meta(meta)
            try:
                self.storage.save_metrics(run_id, metrics.snapshot(status=RunStatus.FAILED.value))
            except Exception:  # pragma: no cover
                pass
            raise

    def _validate(self, run_id: str, fallback: list[str]) -> list[str]:
        try:
            digest = self.storage.load_digest(run_id)
            transcript = self.storage.load_transcript(run_id)
            return validate_digest(digest, transcript.text)
        except LessonDigestError:
            return fallback

    def _reporter(self, meta: RunMeta, stage: str):
        state = {"last_time": 0.0, "last_value": -1.0}

        def report(value: float) -> None:
            value = max(0.0, min(1.0, float(value)))
            now = time.monotonic()
            significant = abs(value - state["last_value"]) >= 0.02 or value in (0.0, 1.0)
            if not significant:
                return
            if now - state["last_time"] < 0.4 and value not in (0.0, 1.0):
                return
            state["last_time"] = now
            state["last_value"] = value
            meta.progress = value
            meta.progress_stage = stage
            self._save_meta(meta)

        return report

    def _save_meta(self, meta: RunMeta) -> None:
        meta.updated_at = utc_now_iso()
        self.storage.save_run_meta(meta)

    @staticmethod
    def _should_run(
        stage: str,
        start_index: int,
        force: bool,
        *,
        artifact: Path | None = None,
    ) -> bool:
        if STAGES.index(stage) < start_index:
            return False
        if stage in ("validate", "deliver"):
            return True
        if force:
            return True
        return artifact is None or not artifact.exists()
