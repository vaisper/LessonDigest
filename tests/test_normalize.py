from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.summarize.normalize import (  # noqa: E402
    normalize_field,
    normalize_math,
    normalize_text,
)
from lessondigest.summarize.parse import digest_from_payload  # noqa: E402


class NormalizeMathTest(unittest.TestCase):
    def test_strips_dollar_wrappers(self) -> None:
        self.assertEqual(normalize_math("$F = ma$"), "F = ma")

    def test_power_and_subscript(self) -> None:
        self.assertEqual(normalize_math("D = b^{2} - 4ac"), "D = b² - 4ac")
        self.assertEqual(normalize_math("x_{1,2} = 3"), "x₁,₂ = 3")

    def test_operators(self) -> None:
        self.assertEqual(normalize_math("a \\cdot b"), "a · b")
        self.assertEqual(normalize_math("A \\times B"), "A × B")
        self.assertEqual(normalize_math("\\frac{a}{b}"), "a / b")
        self.assertEqual(normalize_math("\\sqrt{D}"), "√(D)")
        self.assertEqual(normalize_math("x \\leq y"), "x ≤ y")

    def test_minus_sign(self) -> None:
        self.assertEqual(normalize_math("x \u2212 y"), "x - y")


class NormalizeTextTest(unittest.TestCase):
    def test_removes_markdown(self) -> None:
        self.assertEqual(normalize_text("**жирный** текст"), "жирный текст")
        self.assertEqual(normalize_text("`код`"), "код")

    def test_removes_bullet_prefix(self) -> None:
        self.assertEqual(normalize_text("- пункт"), "пункт")
        self.assertEqual(normalize_text("1. пункт"), "пункт")

    def test_field_combines_both(self) -> None:
        self.assertEqual(normalize_field("$F = m \\cdot a$"), "F = m · a")


class ParseNormalizationTest(unittest.TestCase):
    def test_digest_payload_is_normalized(self) -> None:
        payload = {
            "topic": "**Физика**",
            "formulas": ["$E = m c^{2}$", "- F_{g} = m g"],
            "homework": "параграф 5",
            "homework_confidence": "high",
        }
        digest = digest_from_payload(payload, prompt_version="v1_1", model="test")
        self.assertEqual(digest.topic, "Физика")
        self.assertEqual(digest.formulas, ["E = m c²", "F_g = m g"])


if __name__ == "__main__":
    unittest.main()
