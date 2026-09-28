from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lessondigest.config import ProjectPaths
from lessondigest.domain import (
    AnalyticResult,
    ChunkingResult,
    Digest,
    HumanEvaluation,
    RunMeta,
    TranscriptResult,
)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class FilesystemStorage:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def run_dir(self, run_id: str) -> Path:
        return self.paths.runs / run_id

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.paths.root).as_posix()
        except ValueError:
            return str(path)

    def resolve(self, stored: str | None) -> Path | None:
        if not stored:
            return None
        path = Path(stored)
        return path if path.is_absolute() else (self.paths.root / path)

    def save_run_meta(self, meta: RunMeta) -> Path:
        path = self.run_dir(meta.run_id) / "run.json"
        write_json(path, meta.model_dump(mode="json"))
        return path

    def load_run_meta(self, run_id: str) -> RunMeta:
        path = self.run_dir(run_id) / "run.json"
        if not path.exists():
            from lessondigest.errors import MissingArtifactError

            raise MissingArtifactError(f"run.json не найден для run_id={run_id}", stage="ingest")
        return RunMeta.model_validate(read_json(path))

    def list_runs(self) -> list[str]:
        if not self.paths.runs.exists():
            return []
        return sorted(p.name for p in self.paths.runs.iterdir() if (p / "run.json").exists())

    def transcript_path(self, run_id: str) -> Path:
        return self.paths.transcripts / f"{run_id}.txt"

    def transcript_segments_path(self, run_id: str) -> Path:
        return self.paths.transcripts / f"{run_id}.segments.json"

    def chunks_path(self, run_id: str) -> Path:
        return self.paths.transcripts / f"{run_id}.chunks.json"

    def analytic_json_path(self, run_id: str) -> Path:
        return self.paths.transcripts / f"{run_id}.analytic.json"

    def analytic_md_path(self, run_id: str) -> Path:
        return self.paths.digests / f"{run_id}.analytic.md"

    def digest_md_path(self, run_id: str) -> Path:
        return self.paths.digests / f"{run_id}.md"

    def digest_json_path(self, run_id: str) -> Path:
        return self.paths.digests / f"{run_id}.json"

    def metrics_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "metrics.json"

    def save_transcript(self, run_id: str, result: TranscriptResult) -> Path:
        text_path = self.transcript_path(run_id)
        _atomic_write_text(text_path, result.text.strip() + "\n")
        seg_path = self.transcript_segments_path(run_id)
        if result.segments is not None:
            write_json(seg_path, [s.model_dump(mode="json") for s in result.segments])
        elif seg_path.exists():
            seg_path.unlink()
        return text_path

    def load_transcript(self, run_id: str) -> TranscriptResult:
        from lessondigest.errors import MissingArtifactError

        text_path = self.transcript_path(run_id)
        if not text_path.exists():
            raise MissingArtifactError(f"Транскрипт не найден: {text_path}", stage="asr")
        segments = None
        seg_path = self.transcript_segments_path(run_id)
        if seg_path.exists():
            from lessondigest.domain import TranscriptSegment

            segments = [TranscriptSegment.model_validate(item) for item in read_json(seg_path)]
        return TranscriptResult(text=text_path.read_text(encoding="utf-8").strip(), segments=segments)

    def save_chunks(self, run_id: str, result: ChunkingResult) -> Path:
        path = self.chunks_path(run_id)
        write_json(path, result.model_dump(mode="json"))
        return path

    def load_chunks(self, run_id: str) -> ChunkingResult | None:
        path = self.chunks_path(run_id)
        if not path.exists():
            return None
        return ChunkingResult.model_validate(read_json(path))

    def save_analytic(self, run_id: str, result: AnalyticResult, raw_markdown: str) -> tuple[Path, Path]:
        json_path = self.analytic_json_path(run_id)
        write_json(json_path, result.model_dump(mode="json"))
        md_path = self.analytic_md_path(run_id)
        _atomic_write_text(md_path, raw_markdown.strip() + "\n")
        return json_path, md_path

    def load_analytic(self, run_id: str) -> AnalyticResult:
        from lessondigest.errors import MissingArtifactError

        path = self.analytic_json_path(run_id)
        if not path.exists():
            raise MissingArtifactError(f"Аналитика не найдена: {path}", stage="analytic")
        return AnalyticResult.model_validate(read_json(path))

    def save_digest(self, run_id: str, digest: Digest, raw_markdown: str) -> tuple[Path, Path]:
        json_path = self.digest_json_path(run_id)
        write_json(json_path, digest.model_dump(mode="json"))
        md_path = self.digest_md_path(run_id)
        _atomic_write_text(md_path, raw_markdown.strip() + "\n")
        return md_path, json_path

    def load_digest(self, run_id: str) -> Digest:
        from lessondigest.errors import MissingArtifactError

        path = self.digest_json_path(run_id)
        if not path.exists():
            raise MissingArtifactError(f"Дайджест не найден: {path}", stage="summarize")
        return Digest.model_validate(read_json(path))

    def save_metrics(self, run_id: str, metrics: dict[str, Any]) -> Path:
        path = self.metrics_path(run_id)
        write_json(path, metrics)
        return path

    def save_evaluation(self, evaluation: HumanEvaluation) -> Path:
        path = self.paths.digests_eval / f"{evaluation.run_id}.json"
        write_json(path, evaluation.model_dump(mode="json"))
        return path

    def list_evaluations(self) -> list[HumanEvaluation]:
        if not self.paths.digests_eval.exists():
            return []
        items: list[HumanEvaluation] = []
        for path in sorted(self.paths.digests_eval.glob("*.json")):
            items.append(HumanEvaluation.model_validate(read_json(path)))
        return items
