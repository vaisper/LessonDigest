from __future__ import annotations

import re

from lessondigest.domain import Digest, HomeworkConfidence

HOMEWORK_MARKERS = ("домашн", "задани", "параграф", "упражнени", "на дом")


def validate_digest(digest: Digest, transcript_text: str) -> list[str]:
    warnings: list[str] = []

    if not digest.topic or digest.topic == "Без темы":
        warnings.append("Не определена тема урока")

    if not digest.key_points:
        warnings.append("Пустой список главных тезисов")
    elif len(digest.key_points) < 3:
        warnings.append(f"Мало тезисов: {len(digest.key_points)}")

    if not digest.concepts:
        warnings.append("Не выделены ключевые понятия")

    lowered = transcript_text.lower()
    markers_found = [m for m in HOMEWORK_MARKERS if m in lowered]
    if markers_found and digest.homework_confidence is HomeworkConfidence.ABSENT:
        warnings.append(
            "В транскрипте есть маркеры домашки "
            f"({', '.join(markers_found)}), но дайджест сообщает об отсутствии"
        )
    if digest.homework and digest.homework_confidence is HomeworkConfidence.ABSENT:
        warnings.append("Домашка заполнена, но уверенность absent")

    digest_len = len(digest.model_dump_json())
    if len(transcript_text) >= 2000 and digest_len > len(transcript_text):
        warnings.append("Дайджест длиннее транскрипта — возможна простыня")
    if transcript_text and digest_len < 40:
        warnings.append("Подозрительно короткий дайджест")

    return warnings


def has_homework_markers(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(marker, lowered) for marker in HOMEWORK_MARKERS)
