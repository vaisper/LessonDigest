from __future__ import annotations

import re

from lessondigest.config import ChunkingConfig
from lessondigest.domain import Chunk, ChunkingResult, TranscriptSegment

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def estimate_tokens(text: str, chars_per_token: float = 2.5) -> float:
    if chars_per_token <= 0:
        chars_per_token = 2.5
    return len(text) / chars_per_token


def chunk_transcript(
    text: str,
    segments: list[TranscriptSegment] | None,
    config: ChunkingConfig,
) -> ChunkingResult:
    text = text.strip()
    if not text:
        return ChunkingResult(chunks=[], strategy="empty")

    tokens = estimate_tokens(text, config.chars_per_token)
    if not config.enabled or len(text) <= config.soft_char_limit:
        return ChunkingResult(
            chunks=[Chunk(index=0, text=text)],
            strategy=f"single(tokens~{tokens:.0f})",
        )

    if segments:
        chunks = _chunk_by_segments(segments, config)
        if chunks:
            return ChunkingResult(chunks=chunks, strategy="segments")
    return ChunkingResult(chunks=_chunk_by_sentences(text, config), strategy="sentences")


def _chunk_by_segments(segments: list[TranscriptSegment], config: ChunkingConfig) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_chars = 0
    start_sec: float | None = None
    end_sec: float | None = None

    def flush() -> None:
        nonlocal buffer, buffer_chars, start_sec, end_sec
        if not buffer:
            return
        body = " ".join(buffer).strip()
        body = _with_overlap(body, chunks, config.overlap_chars)
        chunks.append(
            Chunk(index=len(chunks), text=body, start_sec=start_sec, end_sec=end_sec)
        )
        buffer = []
        buffer_chars = 0
        start_sec = None
        end_sec = None

    for segment in segments:
        piece = segment.text.strip()
        if not piece:
            continue
        if buffer_chars and buffer_chars + len(piece) > config.soft_char_limit:
            flush()
        if start_sec is None:
            start_sec = segment.start
        end_sec = segment.end
        buffer.append(piece)
        buffer_chars += len(piece) + 1
    flush()
    return chunks


def _chunk_by_sentences(text: str, config: ChunkingConfig) -> list[Chunk]:
    sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()]
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_chars = 0

    def flush() -> None:
        nonlocal buffer, buffer_chars
        if not buffer:
            return
        body = " ".join(buffer).strip()
        body = _with_overlap(body, chunks, config.overlap_chars)
        chunks.append(Chunk(index=len(chunks), text=body))
        buffer = []
        buffer_chars = 0

    for sentence in sentences:
        if buffer_chars and buffer_chars + len(sentence) > config.soft_char_limit:
            flush()
        buffer.append(sentence)
        buffer_chars += len(sentence) + 1
    flush()
    return chunks


def _with_overlap(body: str, chunks: list[Chunk], overlap_chars: int) -> str:
    if not chunks or overlap_chars <= 0:
        return body
    tail = chunks[-1].text[-overlap_chars:]
    return f"{tail} {body}".strip()
