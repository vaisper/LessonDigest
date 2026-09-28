from __future__ import annotations

MARKERS: tuple[tuple[str, str], ...] = (
    ("домашн", "high"),
    ("на дом", "high"),
    ("парагр", "medium"),
    ("§", "medium"),
    ("упражнени", "medium"),
    ("задани", "medium"),
    ("задач", "medium"),
    ("номер", "low"),
    ("№", "low"),
    ("подготов", "low"),
    ("выучить", "low"),
    ("повторить", "low"),
)

_PRIORITY = {"high": 3, "medium": 2, "low": 1}


def _confidence(sentence: str) -> str | None:
    lowered = sentence.lower()
    found: str | None = None
    for marker, level in MARKERS:
        if marker in lowered:
            if found is None or _PRIORITY[level] > _PRIORITY[found]:
                found = level
    return found


def detect_homework(sentences: list[str]) -> tuple[list[str], str]:
    matches = [(index, _confidence(sentence)) for index, sentence in enumerate(sentences)]
    matches = [(index, conf) for index, conf in matches if conf]
    if not matches:
        return [], "absent"

    last_index, last_conf = max(matches, key=lambda item: (_PRIORITY[item[1]], item[0]))
    candidates = [sentences[last_index]]
    if last_index + 1 < len(sentences) and len(sentences[last_index + 1]) < 220:
        candidates.append(sentences[last_index + 1])

    result: list[str] = []
    for candidate in candidates:
        if candidate not in result:
            result.append(candidate)
    return result, last_conf or "low"
