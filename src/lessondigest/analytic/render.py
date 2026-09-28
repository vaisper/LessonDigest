from __future__ import annotations

from lessondigest.domain import AnalyticResult


def render_analytic_md(result: AnalyticResult) -> str:
    lines: list[str] = ["# Аналитика транскрипта (TF-IDF + TextRank)", ""]

    lines.append("## Ключевые термины")
    lines.extend([f"- {term}" for term in result.key_terms] or ["- Нет данных"])
    lines.append("")

    lines.append("## Ключевые предложения")
    lines.extend(
        [f"{index}. {sentence}" for index, sentence in enumerate(result.key_sentences, start=1)]
        or ["1. Нет данных"]
    )
    lines.append("")

    lines.append("## Кандидаты домашки")
    lines.extend([f"- {item}" for item in result.homework_candidates] or ["- Нет данных"])
    lines.append(f"\n_Уверенность: {result.homework_confidence}_")
    lines.append("")

    sentences = int(result.stats.get("sentences", 0))
    tokens = int(result.stats.get("tokens", 0))
    lines.append(
        f"_Метод: {result.method} · {result.elapsed_sec} c · предложений: {sentences} · токенов: {tokens}_"
    )
    return "\n".join(lines)
