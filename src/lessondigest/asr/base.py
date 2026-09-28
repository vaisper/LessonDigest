from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from lessondigest.config import AsrConfig
from lessondigest.domain import TranscriptResult
from lessondigest.errors import AsrError

ProgressCallback = Callable[[float], None]


class AsrOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: str = "ru"
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    vad: bool = True

    @classmethod
    def from_config(cls, config: AsrConfig) -> "AsrOptions":
        return cls(
            language=config.language,
            model=config.model,
            device=config.device,
            compute_type=config.compute_type,
            beam_size=config.beam_size,
            vad=config.vad,
        )


@runtime_checkable
class AsrProvider(Protocol):
    name: str
    model: str

    def transcribe(
        self,
        audio_path: Path,
        options: AsrOptions,
        on_progress: ProgressCallback | None = None,
    ) -> TranscriptResult: ...


def build_asr(config: AsrConfig) -> AsrProvider:
    provider = (config.provider or "").strip().lower()
    if provider in {"faster_whisper", "faster-whisper", "whisper"}:
        from lessondigest.asr.faster_whisper_asr import FasterWhisperAsr

        return FasterWhisperAsr()
    if provider in {"fake", "stub", "none"}:
        from lessondigest.asr.fake import FakeAsr

        return FakeAsr()
    raise AsrError(f"Неизвестный ASR provider: {config.provider!r}")
