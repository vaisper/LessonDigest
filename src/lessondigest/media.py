from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from lessondigest.domain import MediaInfo
from lessondigest.errors import IngestError
from lessondigest.logging_setup import get_logger

log = get_logger("media")

_TOOL_CACHE: dict[str, str | None] = {}


def _find_tool(name: str) -> str | None:
    if name in _TOOL_CACHE:
        return _TOOL_CACHE[name]

    resolved: str | None = None
    override = os.environ.get(f"LESSONDIGEST_{name.upper()}_BIN")
    if override and Path(override).exists():
        resolved = override
    if not resolved:
        resolved = shutil.which(name)
    if not resolved:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            packages = Path(local) / "Microsoft" / "WinGet" / "Packages"
            if packages.exists():
                matches = sorted(packages.glob(f"Gyan.FFmpeg*/**/bin/{name}.exe"))
                if matches:
                    resolved = str(matches[-1])
                    log.debug("Найден %s через winget: %s", name, resolved)

    _TOOL_CACHE[name] = resolved
    return resolved


def ffprobe_executable() -> str | None:
    return _find_tool("ffprobe")


def ffmpeg_executable() -> str | None:
    return _find_tool("ffmpeg")


def has_ffmpeg() -> bool:
    return ffprobe_executable() is not None


def probe(path: Path) -> MediaInfo:
    exe = ffprobe_executable()
    if not exe:
        log.debug("ffprobe не найден в PATH — метаданные аудио недоступны")
        return MediaInfo()
    cmd = [
        exe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except OSError as exc:
        log.warning("ffprobe не запустился: %s", exc)
        return MediaInfo()
    if completed.returncode != 0:
        log.warning("ffprobe вернул код %s: %s", completed.returncode, completed.stderr.strip())
        return MediaInfo()
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return MediaInfo()

    fmt = payload.get("format") or {}
    streams = payload.get("streams") or []
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration = _to_float(fmt.get("duration")) or _to_float(audio.get("duration"))
    return MediaInfo(
        duration_sec=duration,
        sample_rate=_to_int(audio.get("sample_rate")),
        channels=_to_int(audio.get("channels")),
        codec=audio.get("codec_name"),
        format_name=fmt.get("format_name"),
    )


def normalize_to_wav(src: Path, dst: Path, *, sample_rate: int = 16000) -> Path:
    exe = ffmpeg_executable()
    if not exe:
        raise IngestError("ffmpeg не найден в PATH — нормализация недоступна")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe,
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-vn",
        str(dst),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if completed.returncode != 0:
        raise IngestError(f"ffmpeg завершился с кодом {completed.returncode}: {completed.stderr.strip()}")
    return dst


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    parsed = _to_float(value)
    return int(parsed) if parsed is not None else None
