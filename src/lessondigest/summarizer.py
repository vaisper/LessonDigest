from __future__ import annotations

import json
from collections.abc import Callable

from lessondigest.chunking import chunk_transcript
from lessondigest.config import AppConfig
from lessondigest.domain import ChunkingResult, Digest
from lessondigest.errors import LlmError
from lessondigest.logging_setup import get_logger
from lessondigest.summarize.base import LlmOptions, LlmProvider, build_llm
from lessondigest.summarize.parse import digest_from_llm, digest_from_payload, extract_json_object
from lessondigest.summarize.render import render_digest_md

log = get_logger("summarizer")

REDUCE_INSTRUCTION = """Ниже — JSON-конспекты последовательных частей одного урока.
Слей их в один итоговый конспект на русском. Верни СТРОГО тот же JSON-формат.
Правила:
- Не выдумывай факты, которых нет в частях.
- Если домашнее задание упоминается в нескольких частях, предпочти тот вариант, который
  встречается в ПОСЛЕДНЕЙ части (домашку обычно задают в конце урока).
- Если домашка не упоминается нигде — homework=null, homework_confidence=absent.

Части урока:
{{PARTS}}
"""


def build_prompt(template: str, transcript: str) -> str:
    return template.replace("{{TRANSCRIPT}}", transcript)


def summarize(
    transcript: str,
    *,
    config: AppConfig,
    llm: LlmProvider | None = None,
    chunking: ChunkingResult | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[Digest, str, ChunkingResult]:
    llm = llm or build_llm(config.llm, config.secrets)
    template = config.load_prompt_template()
    options = LlmOptions.from_config(config.llm)

    chunks = chunking or chunk_transcript(transcript, None, config.chunking)
    if not chunks.chunks:
        raise LlmError("Нет текста для суммаризации")

    if len(chunks.chunks) == 1:
        if on_progress:
            on_progress(0.0)
        result = llm.complete(build_prompt(template, chunks.chunks[0].text), options)
        digest = digest_from_llm(result.text, prompt_version=config.llm.prompt_version, model=result.model)
        if on_progress:
            on_progress(1.0)
        return digest, render_digest_md(digest), chunks

    log.info("Map-reduce по %d чанкам", len(chunks.chunks))
    part_payloads: list[dict] = []
    model_used = options.model
    total = len(chunks.chunks)
    for index, chunk in enumerate(chunks.chunks):
        result = llm.complete(build_prompt(template, chunk.text), options)
        model_used = result.model or model_used
        part_payloads.append(extract_json_object(result.text))
        if on_progress:
            on_progress(0.9 * (index + 1) / total)

    parts_text = "\n\n".join(
        f"--- Часть {i + 1} ---\n{json.dumps(payload, ensure_ascii=False)}"
        for i, payload in enumerate(part_payloads)
    )
    reduce_prompt = REDUCE_INSTRUCTION.replace("{{PARTS}}", parts_text)
    reduce_result = llm.complete(reduce_prompt, options)
    digest = digest_from_llm(
        reduce_result.text,
        prompt_version=config.llm.prompt_version,
        model=reduce_result.model or model_used,
    )
    if on_progress:
        on_progress(1.0)
    return digest, render_digest_md(digest), chunks


def digest_from_text_payload(payload: dict, *, prompt_version: str, model: str) -> Digest:
    return digest_from_payload(payload, prompt_version=prompt_version, model=model)
