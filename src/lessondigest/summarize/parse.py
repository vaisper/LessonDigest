from __future__ import annotations

import json
import re
from typing import Any

from lessondigest.domain import Digest, HomeworkConfidence
from lessondigest.errors import LlmError
from lessondigest.summarize.normalize import normalize_field, normalize_text

FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

CONFIDENCE_ALIASES = {
    "high": HomeworkConfidence.HIGH,
    "высокая": HomeworkConfidence.HIGH,
    "medium": HomeworkConfidence.MEDIUM,
    "средняя": HomeworkConfidence.MEDIUM,
    "low": HomeworkConfidence.LOW,
    "низкая": HomeworkConfidence.LOW,
    "absent": HomeworkConfidence.ABSENT,
    "none": HomeworkConfidence.ABSENT,
    "нет": HomeworkConfidence.ABSENT,
    "отсутствует": HomeworkConfidence.ABSENT,
}


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = FENCE.sub("", text.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LlmError("LLM не вернула JSON-объект")
    snippet = cleaned[start : end + 1]
    try:
        payload = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise LlmError(f"Не удалось разобрать JSON от LLM: {exc}") from exc
    if not isinstance(payload, dict):
        raise LlmError("LLM вернула JSON не-объект")
    return payload


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = normalize_field(value)
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        items = [normalize_field(str(item)) for item in value]
        return [item for item in items if item]
    return [normalize_field(str(value))]


def digest_from_payload(payload: dict[str, Any], *, prompt_version: str, model: str) -> Digest:
    confidence = payload.get("homework_confidence")
    if isinstance(confidence, str):
        confidence = CONFIDENCE_ALIASES.get(confidence.strip().lower(), HomeworkConfidence.ABSENT)
    elif not isinstance(confidence, HomeworkConfidence):
        confidence = HomeworkConfidence.ABSENT

    homework = payload.get("homework")
    if isinstance(homework, str):
        homework = normalize_text(homework)
        if homework.lower() in {"null", "none", "нет", "не упоминалось", "-"}:
            homework = None
    if not homework:
        homework = None
        if confidence is not HomeworkConfidence.ABSENT:
            confidence = HomeworkConfidence.ABSENT

    topic = normalize_text(str(payload.get("topic") or "")) or "Без темы"

    return Digest(
        topic=topic,
        concepts=_as_str_list(payload.get("concepts")),
        key_points=_as_str_list(payload.get("key_points")),
        formulas=_as_str_list(payload.get("formulas")),
        homework=homework,
        homework_confidence=confidence,
        questions=_as_str_list(payload.get("questions")),
        prompt_version=prompt_version,
        model=model,
    )


def digest_from_llm(text: str, *, prompt_version: str, model: str) -> Digest:
    return digest_from_payload(extract_json_object(text), prompt_version=prompt_version, model=model)
