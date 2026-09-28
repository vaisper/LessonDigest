from __future__ import annotations

import hashlib
import re
import shutil
from datetime import date
from pathlib import Path

from lessondigest.config import ProjectPaths
from lessondigest.domain import MediaInfo, RunMeta, RunStatus
from lessondigest.errors import IngestError
from lessondigest.logging_setup import get_logger
from lessondigest import media

log = get_logger("ingest")

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".opus", ".aac", ".mp4"}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify_subject(subject: str | None) -> str:
    raw = (subject or "lesson").strip().lower()
    raw = re.sub(r"[^0-9a-zа-я]+", "_", raw, flags=re.IGNORECASE)
    raw = raw.strip("_")
    return raw or "lesson"


def make_run_id(subject: str | None, checksum: str, *, on_date: date | None = None) -> str:
    day = (on_date or date.today()).strftime("%Y%m%d")
    short = hashlib.sha256(f"{checksum}:{slugify_subject(subject)}:{day}".encode()).hexdigest()[:6]
    return f"{day}_{slugify_subject(subject)}_{short}"


class IngestResult:
    def __init__(
        self,
        run_id: str,
        raw_path: Path,
        checksum: str,
        media_info: MediaInfo,
        original_name: str,
    ) -> None:
        self.run_id = run_id
        self.raw_path = raw_path
        self.checksum = checksum
        self.media_info = media_info
        self.original_name = original_name


def validate_source(source: Path) -> None:
    if not source.exists():
        raise IngestError(f"Файл не найден: {source}")
    if not source.is_file():
        raise IngestError(f"Ожидался файл, получено: {source}")
    if source.stat().st_size == 0:
        raise IngestError(f"Файл пустой: {source}")
    if source.suffix.lower() not in AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(AUDIO_EXTENSIONS))
        raise IngestError(f"Расширение {source.suffix!r} не поддерживается. Разрешены: {allowed}")


def ingest(
    source: Path | str,
    subject: str | None,
    paths: ProjectPaths,
    *,
    checksum: str | None = None,
    copy: bool = True,
) -> IngestResult:
    source = Path(source)
    validate_source(source)
    digest = checksum or sha256_file(source)
    run_id = make_run_id(subject, digest)
    paths.ensure()
    raw_path = paths.audio_raw / f"{run_id}{source.suffix.lower()}"

    if copy and (not raw_path.exists() or sha256_file(raw_path) != digest):
        shutil.copy2(source, raw_path)
        log.info("Скопировано в %s", raw_path)

    media_info = media.probe(raw_path if raw_path.exists() else source)
    if media_info.duration_sec and media_info.duration_sec > 3600:
        log.warning("Длительность %.1f мин > 60 мин", media_info.duration_sec / 60)

    return IngestResult(run_id, raw_path, digest, media_info, source.name)


def build_meta(result: IngestResult, subject: str | None, paths: ProjectPaths) -> RunMeta:
    return RunMeta(
        run_id=result.run_id,
        subject=slugify_subject(subject),
        status=RunStatus.INGESTING,
        source_original_name=result.original_name,
        checksum_sha256=result.checksum,
        duration_sec=result.media_info.duration_sec,
        media=result.media_info,
        audio_raw=paths_root_relative(paths, result.raw_path),
    )


def paths_root_relative(paths: ProjectPaths, path: Path) -> str:
    try:
        return path.resolve().relative_to(paths.root).as_posix()
    except ValueError:
        return str(path)
