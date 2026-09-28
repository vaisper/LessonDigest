from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import markdown as md
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from lessondigest import __version__, ingest as ingest_stage
from lessondigest.config import AppConfig
from lessondigest.errors import LessonDigestError
from lessondigest.logging_setup import get_logger
from lessondigest.storage import FilesystemStorage
from lessondigest.web.jobs import JobQueue
from lessondigest.web.page import PAGE

log = get_logger("web.app")

MAX_UPLOAD_BYTES = 300 * 1024 * 1024


def create_app(config: AppConfig) -> FastAPI:
    storage = FilesystemStorage(config.paths)
    config.paths.ensure()
    jobs = JobQueue(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        jobs.start()
        log.info("Веб-интерфейс запущен. Проект: %s", config.paths.root)
        yield
        jobs.stop()

    app = FastAPI(title="LessonDigest", version=__version__, lifespan=lifespan)
    app.state.config = config
    app.state.storage = storage
    app.state.jobs = jobs

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(PAGE)

    @app.get("/api/runs")
    async def list_runs() -> JSONResponse:
        return JSONResponse(jobs.list_runs())

    @app.post("/api/runs", status_code=202)
    async def create_run(
        file: UploadFile = File(...),
        subject: str = Form(""),
    ) -> JSONResponse:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ingest_stage.AUDIO_EXTENSIONS:
            allowed = ", ".join(sorted(ingest_stage.AUDIO_EXTENSIONS))
            raise HTTPException(status_code=400, detail=f"Формат {suffix or '?'} не поддерживается. Разреши: {allowed}")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Пустой файл")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Файл слишком большой (лимит 300 МБ)")

        checksum = ingest_stage.sha256_bytes(data)
        run_id = ingest_stage.make_run_id(subject, checksum)
        target = config.paths.audio_incoming / f"{run_id}{suffix}"
        target.write_bytes(data)

        job = jobs.submit(run_id, subject.strip(), target)
        return JSONResponse({"run_id": run_id, "status": job.status}, status_code=202)

    @app.get("/api/runs/{run_id}")
    async def run_status(run_id: str) -> JSONResponse:
        if not _known(storage, jobs, run_id):
            raise HTTPException(status_code=404, detail="Прогон не найден")
        return JSONResponse(jobs.describe(run_id))

    @app.get("/api/runs/{run_id}/digest")
    async def run_digest(run_id: str) -> JSONResponse:
        try:
            digest = storage.load_digest(run_id)
        except LessonDigestError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        md_path = storage.digest_md_path(run_id)
        raw = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        html = md.markdown(raw, extensions=["extra", "sane_lists"])
        return JSONResponse(
            {
                "topic": digest.topic,
                "homework": digest.homework,
                "homework_confidence": digest.homework_confidence.value,
                "concepts": digest.concepts,
                "key_points": digest.key_points,
                "formulas": digest.formulas,
                "questions": digest.questions,
                "markdown": raw,
                "html": html,
            }
        )

    @app.get("/api/runs/{run_id}/digest.md", response_class=PlainTextResponse)
    async def run_digest_md(run_id: str) -> PlainTextResponse:
        path = storage.digest_md_path(run_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Дайджест не найден")
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")

    @app.get("/api/runs/{run_id}/transcript", response_class=PlainTextResponse)
    async def run_transcript(run_id: str) -> PlainTextResponse:
        path = storage.transcript_path(run_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Транскрипт не найден")
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")

    return app


def _known(storage: FilesystemStorage, jobs: JobQueue, run_id: str) -> bool:
    if jobs.get(run_id) is not None:
        return True
    return (storage.run_dir(run_id) / "run.json").exists()
