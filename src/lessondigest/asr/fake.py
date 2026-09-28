from __future__ import annotations

import time
from pathlib import Path

from lessondigest.asr.base import AsrOptions, ProgressCallback
from lessondigest.domain import TranscriptResult
from lessondigest.errors import AsrError

DEFAULT_TEXT = (
    "Сегодня на уроке мы разобрали квадратные уравнения. "
    "Дискриминант вычисляется по формуле D равно b в квадрате минус четыре a c. "
    "Если дискриминант больше нуля, уравнение имеет два корня. "
    "Домашнее задание: параграф двенадцать, номера триста сорок пять и триста сорок шесть."
)


class FakeAsr:
    name = "fake"

    def __init__(self, text: str | None = None, model: str = "fake-asr") -> None:
        self._text = text
        self.model = model

    def _resolve_text(self, audio_path: Path) -> str:
        if self._text:
            return self._text
        for suffix in (".transcript.txt", ".txt"):
            sidecar = audio_path.with_suffix(suffix)
            if sidecar.exists():
                return sidecar.read_text(encoding="utf-8")
        return DEFAULT_TEXT

    def transcribe(
        self,
        audio_path: Path,
        options: AsrOptions,
        on_progress: ProgressCallback | None = None,
    ) -> TranscriptResult:
        started = time.perf_counter()
        if on_progress:
            on_progress(0.5)
        text = self._resolve_text(Path(audio_path)).strip()
        if not text:
            raise AsrError("FakeAsr: пустой текст")
        if on_progress:
            on_progress(1.0)
        return TranscriptResult(
            text=text,
            segments=None,
            language=options.language,
            provider=self.name,
            model=self.model,
            elapsed_sec=time.perf_counter() - started,
        )
