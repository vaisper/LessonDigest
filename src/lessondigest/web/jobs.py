from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path

from lessondigest.config import AppConfig
from lessondigest.domain import RunStatus, utc_now_iso
from lessondigest.errors import LessonDigestError
from lessondigest.logging_setup import get_logger
from lessondigest.pipeline import Pipeline
from lessondigest.storage import FilesystemStorage

log = get_logger("web.jobs")

JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_FAILED = "failed"

GROUP = {
    RunStatus.CREATED.value: "queued",
    RunStatus.INGESTING.value: "running",
    RunStatus.ASR_RUNNING.value: "running",
    RunStatus.ASR_DONE.value: "running",
    RunStatus.SUMMARIZING.value: "running",
    RunStatus.DIGEST_READY.value: "done",
    RunStatus.DELIVERED.value: "done",
    RunStatus.FAILED.value: "failed",
}

LABEL = {
    "queued": "в очереди",
    JOB_QUEUED: "в очереди",
    RunStatus.CREATED.value: "создан",
    RunStatus.INGESTING.value: "принимаю файл",
    RunStatus.ASR_RUNNING.value: "распознаю речь",
    RunStatus.ASR_DONE.value: "транскрипт готов",
    RunStatus.SUMMARIZING.value: "делаю конспект",
    RunStatus.DIGEST_READY.value: "дайджест готов",
    RunStatus.DELIVERED.value: "готово",
    JOB_DONE: "готово",
    RunStatus.FAILED.value: "ошибка",
    JOB_FAILED: "ошибка",
    JOB_RUNNING: "в работе",
}


def _percent(stage: str | None, status: str, progress: float | None) -> int | None:
    if status == JOB_DONE:
        return 100
    if status == JOB_FAILED:
        return None
    if status == JOB_QUEUED:
        return 0
    if stage == RunStatus.INGESTING.value:
        return 5
    if stage == RunStatus.ASR_RUNNING.value:
        return None if progress is None else 5 + int(80 * progress)
    if stage == RunStatus.ASR_DONE.value:
        return 85
    if stage == RunStatus.SUMMARIZING.value:
        return None if progress is None else 85 + int(13 * progress)
    if stage in (RunStatus.DIGEST_READY.value, RunStatus.DELIVERED.value):
        return 100
    return None


@dataclass
class Job:
    run_id: str
    subject: str
    source_path: Path
    status: str = JOB_QUEUED
    error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)


class JobQueue:
    def __init__(self, config: AppConfig, pipeline_factory=None) -> None:
        self.config = config
        self.storage = FilesystemStorage(config.paths)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._pipeline_factory = pipeline_factory or (lambda: Pipeline(config))

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._loop, name="lessondigest-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._queue.put(None)
        if self._worker:
            self._worker.join(timeout=5)

    def submit(self, run_id: str, subject: str, source_path: Path) -> Job:
        with self._lock:
            existing = self._jobs.get(run_id)
            if existing and existing.status in (JOB_QUEUED, JOB_RUNNING):
                return existing
            job = Job(run_id=run_id, subject=subject, source_path=Path(source_path))
            self._jobs[run_id] = job
        self._queue.put(run_id)
        log.info("Задача принята: %s (%s)", run_id, subject or "без предмета")
        return job

    def get(self, run_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(run_id)

    def _loop(self) -> None:
        while True:
            run_id = self._queue.get()
            if run_id is None:
                return
            job = self.get(run_id)
            if job is None:
                continue
            job.status = JOB_RUNNING
            try:
                pipeline = self._pipeline_factory()
                result = pipeline.run(audio=job.source_path, subject=job.subject)
                job.status = JOB_DONE
                log.info("Задача выполнена: %s -> %s", run_id, result.status.value)
            except LessonDigestError as exc:
                job.status = JOB_FAILED
                job.error = str(exc)
                log.error("Задача %s провалена: %s", run_id, exc)
            except Exception as exc:  # pragma: no cover
                job.status = JOB_FAILED
                job.error = f"{type(exc).__name__}: {exc}"
                log.exception("Неожиданная ошибка в задаче %s", run_id)
            finally:
                try:
                    job.source_path.unlink(missing_ok=True)
                except OSError:
                    pass
                self._queue.task_done()

    def describe(self, run_id: str) -> dict:
        job = self.get(run_id)
        meta = None
        try:
            meta = self.storage.load_run_meta(run_id)
        except LessonDigestError:
            meta = None

        if meta is not None:
            stage = meta.status.value
            status = GROUP.get(stage, JOB_RUNNING)
            if job is not None and job.status == JOB_FAILED:
                status = JOB_FAILED
        else:
            stage = None
            status = job.status if job is not None else "unknown"

        error = None
        warnings: list[str] = []
        duration = None
        subject = job.subject if job else ""
        created_at = job.created_at if job else ""
        if meta is not None:
            error = meta.error
            warnings = meta.warnings
            duration = meta.duration_sec
            subject = meta.subject
            created_at = meta.created_at
        elif job is not None:
            error = job.error

        return {
            "run_id": run_id,
            "subject": subject,
            "status": status,
            "stage": stage,
            "stage_label": LABEL.get(stage or status, status),
            "progress": meta.progress if meta is not None else None,
            "percent": _percent(stage, status, meta.progress if meta is not None else None),
            "error": error,
            "warnings": warnings,
            "duration_sec": duration,
            "created_at": created_at,
            "digest_available": self.storage.digest_json_path(run_id).exists(),
        }

    def list_runs(self) -> list[dict]:
        ids = set(self.storage.list_runs())
        with self._lock:
            ids.update(self._jobs.keys())
        return [self.describe(run_id) for run_id in sorted(ids, reverse=True)]
