from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.domain import HomeworkConfidence  # noqa: E402
from lessondigest.summarize.parse import (  # noqa: E402
    digest_from_llm,
    digest_from_payload,
    extract_json_object,
)
from lessondigest.summarize.render import render_digest_md  # noqa: E402
from lessondigest.validate import validate_digest  # noqa: E402


class ParseRenderTest(unittest.TestCase):
    def test_extract_json_from_fences(self) -> None:
        raw = '```json\n{"topic": "Тест", "key_points": ["a"]}\n```'
        payload = extract_json_object(raw)
        self.assertEqual(payload["topic"], "Тест")

    def test_digest_from_llm(self) -> None:
        raw = (
            '{"topic":"Квадратные уравнения","concepts":["дискриминант"],'
            '"key_points":["a","b","c"],"formulas":["D=b^2-4ac"],'
            '"homework":"§12 №345","homework_confidence":"high","questions":["q"]}'
        )
        digest = digest_from_llm(raw, prompt_version="v1", model="test")
        self.assertEqual(digest.homework, "§12 №345")
        self.assertIs(digest.homework_confidence, HomeworkConfidence.HIGH)
        self.assertEqual(digest.prompt_version, "v1")

    def test_confidence_alias_and_null_homework(self) -> None:
        digest = digest_from_payload(
            {"topic": "Урок", "homework": None, "homework_confidence": "высокая"},
            prompt_version="v1",
            model="m",
        )
        self.assertIsNone(digest.homework)
        self.assertIs(digest.homework_confidence, HomeworkConfidence.ABSENT)

    def test_render_has_sections(self) -> None:
        digest = digest_from_payload({"topic": "Тема", "key_points": ["1"]}, prompt_version="v1", model="m")
        markdown = render_digest_md(digest)
        for section in ("## Ключевые понятия", "## Главные тезисы", "## Домашнее задание", "## Вопросы"):
            self.assertIn(section, markdown)

    def test_validate_warns_on_missed_homework(self) -> None:
        digest = digest_from_payload({"topic": "Тема", "key_points": ["1", "2", "3"], "concepts": ["c"]}, prompt_version="v1", model="m")
        warnings = validate_digest(digest, "На дом задание параграф 5.")
        self.assertTrue(any("маркеры домашки" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
