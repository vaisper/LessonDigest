from __future__ import annotations

from lessondigest.domain import Digest

EMPTY = "В транскрипте не обнаружено"


def render_digest_md(digest: Digest) -> str:
    lines: list[str] = [f"# {digest.topic}", ""]

    lines.append("## Ключевые понятия")
    lines.extend([f"- {item}" for item in digest.concepts] or ["- Нет данных"])
    lines.append("")

    lines.append("## Главные тезисы")
    lines.extend([f"{i}. {item}" for i, item in enumerate(digest.key_points, start=1)] or ["1. Нет данных"])
    lines.append("")

    lines.append("## Формулы и правила")
    lines.extend([f"- {item}" for item in digest.formulas] or ["- Нет данных"])
    lines.append("")

    lines.append("## Домашнее задание")
    lines.append(digest.homework if digest.homework else EMPTY)
    if digest.homework:
        lines.append(f"\n_Уверенность: {digest.homework_confidence.value}_")
    lines.append("")

    lines.append("## Вопросы для уточнения")
    lines.extend([f"- {item}" for item in digest.questions] or ["- Нет данных"])
    lines.append("")

    lines.append("---")
    lines.append(
        f"_Сгенерировано LessonDigest · prompt {digest.prompt_version} · model {digest.model}_"
    )
    return "\n".join(lines)
