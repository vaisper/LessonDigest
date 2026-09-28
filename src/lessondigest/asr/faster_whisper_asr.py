from __future__ import annotations

import time
from pathlib import Path

from lessondigest.asr.base import AsrOptions, ProgressCallback
from lessondigest.domain import TranscriptResult, TranscriptSegment
from lessondigest.errors import AsrError
from lessondigest.logging_setup import get_logger

log = get_logger("asr.faster_whisper")


class FasterWhisperAsr:
    name = "faster_whisper"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "small"
        self._cache: dict[tuple[str, str, str], object] = {}

    def _load(self, options: AsrOptions):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise AsrError(
                "faster-whisper не установлен. Установите: pip install faster-whisper"
            ) from exc
        key = (options.model, options.device, options.compute_type)
        if key not in self._cache:
            log.info(
                "Загружаю Whisper %s (%s, %s)", options.model, options.device, options.compute_type
            )
            self._cache[key] = WhisperModel(
                options.model, device=options.device, compute_type=options.compute_type
            )
        return self._cache[key]

    def transcribe(
        self,
        audio_path: Path,
        options: AsrOptions,
        on_progress: ProgressCallback | None = None,
    ) -> TranscriptResult:
        model = self._load(options)
        self.model = options.model
        started = time.perf_counter()
        if on_progress:
            on_progress(0.0)
        try:
            segments, info = model.transcribe(
                str(audio_path),
                language=options.language,
                beam_size=options.beam_size,
                vad_filter=options.vad,
            )
            total = float(getattr(info, "duration", 0.0) or 0.0)
            collected: list[TranscriptSegment] = []
            parts: list[str] = []
            for segment in segments:
                piece = (segment.text or "").strip()
                if not piece:
                    continue
                parts.append(piece)
                collected.append(
                    TranscriptSegment(start=float(segment.start), end=float(segment.end), text=piece)
                )
                if on_progress and total > 0:
                    on_progress(min(float(segment.end) / total, 1.0))
        except Exception as exc:
            raise AsrError(f"Whisper transcription failed: {exc}") from exc

        if on_progress:
            on_progress(1.0)

        elapsed = time.perf_counter() - started
        text = " ".join(parts).strip()
        if not text:
            raise AsrError("ASR вернул пустой текст — проверьте аудио")
        return TranscriptResult(
            text=text,
            segments=collected or None,
            language=getattr(info, "language", options.language) or options.language,
            provider=self.name,
            model=options.model,
            elapsed_sec=elapsed,
        )
