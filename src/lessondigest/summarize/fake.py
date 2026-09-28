from __future__ import annotations

import json
import re
import time

from lessondigest.summarize.base import LlmOptions, LlmResult

HOMEWORK_MARKERS = ("домашн", "задани", "параграф", "упражнени")
TRANSCRIPT_BLOCK = re.compile(r'"""(.*?)"""', re.DOTALL)


class FakeLlm:
    name = "fake"

    def __init__(self, model: str = "fake-llm") -> None:
        self.model = model

    def complete(self, prompt: str, options: LlmOptions) -> LlmResult:
        started = time.perf_counter()
        match = TRANSCRIPT_BLOCK.search(prompt)
        transcript = (match.group(1) if match else prompt).strip()
        lowered = transcript.lower()
        has_homework = any(marker in lowered for marker in HOMEWORK_MARKERS)

        homework = None
        confidence = "absent"
        if has_homework:
            homework = transcript[-300:].strip()
            confidence = "medium"

        payload = {
            "topic": "Тестовый урок (fake LLM)",
            "concepts": ["ключевое понятие — определение из транскрипта"],
            "key_points": [
                "Первый тезис из транскрипта",
                "Второй тезис из транскрипта",
                "Третий тезис из транскрипта",
            ],
            "formulas": ["D = b^2 - 4ac"] if "дискриминант" in lowered else [],
            "homework": homework,
            "homework_confidence": confidence,
            "questions": ["Проверить конспект по учебнику"],
        }
        return LlmResult(
            text=json.dumps(payload, ensure_ascii=False),
            model=self.model,
            tokens_in=len(prompt) // 4,
            tokens_out=len(json.dumps(payload)) // 4,
            elapsed_sec=time.perf_counter() - started,
        )
