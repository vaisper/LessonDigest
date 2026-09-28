from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lessondigest.analytic.compare import compare_terms, grounded_ratio  # noqa: E402
from lessondigest.analytic.engine import analyze  # noqa: E402
from lessondigest.analytic.homework import detect_homework  # noqa: E402
from lessondigest.analytic.keywords import extract_key_terms  # noqa: E402
from lessondigest.analytic.preprocess import lemmas, split_sentences  # noqa: E402
from lessondigest.analytic.render import render_analytic_md  # noqa: E402
from lessondigest.analytic.textrank import rank_sentences  # noqa: E402
from lessondigest.config import AnalyticConfig  # noqa: E402

ALGEBRA = (
    "Сегодня мы разобрали квадратные уравнения. "
    "Дискриминант вычисляется по формуле D равно b в квадрате минус четыре a c. "
    "Если дискриминант больше нуля, уравнение имеет два корня. "
    "Теорема Виета связывает корни с коэффициентами. "
    "Домашнее задание: параграф двенадцать, номера триста сорок пять и триста сорок шесть."
)


class PreprocessTest(unittest.TestCase):
    def test_split_sentences(self) -> None:
        sentences = split_sentences("Первое. Второе предложение! Третье?")
        self.assertEqual(len(sentences), 3)

    def test_lemmas_drop_stopwords(self) -> None:
        result = lemmas("И это уравнение имеет два корня")
        self.assertIn("уравнение", result)
        self.assertNotIn("и", result)
        self.assertNotIn("это", result)


class KeywordsTest(unittest.TestCase):
    def test_terms_include_topic_word(self) -> None:
        terms = extract_key_terms(split_sentences(ALGEBRA), top_k=10)
        joined = " ".join(terms)
        self.assertIn("дискриминант", joined)


class TextRankTest(unittest.TestCase):
    def test_returns_subset_in_order(self) -> None:
        sentences = split_sentences(ALGEBRA)
        ranked = rank_sentences(sentences, top_n=2, min_chars=10)
        self.assertTrue(ranked)
        self.assertTrue(all(s in sentences for s in ranked))
        positions = [sentences.index(s) for s in ranked]
        self.assertEqual(positions, sorted(positions))


class HomeworkTest(unittest.TestCase):
    def test_prefers_last_mention(self) -> None:
        sentences = [
            "Задание на дом будет позже.",
            "Мы обсудили теорему.",
            "Домашнее задание: параграф двенадцать, номера триста сорок пять.",
        ]
        candidates, confidence = detect_homework(sentences)
        self.assertEqual(confidence, "high")
        self.assertIn("параграф", candidates[0].lower())

    def test_absent(self) -> None:
        candidates, confidence = detect_homework(["Мы разобрали тему."])
        self.assertEqual(candidates, [])
        self.assertEqual(confidence, "absent")

    def test_high_confidence_beats_later_weak_mention(self) -> None:
        sentences = [
            "Домашнее задание: параграф двенадцать, номера триста сорок пять.",
            "Усно подготовьте ответ на вопрос.",
            "Спасибо за внимание, урок окончен.",
        ]
        candidates, confidence = detect_homework(sentences)
        self.assertEqual(confidence, "high")
        self.assertIn("параграф", candidates[0].lower())


class CompareTest(unittest.TestCase):
    def test_terms_overlap(self) -> None:
        metrics = compare_terms(["дискриминант", "теорема виета"], ["дискриминант", "корни"])
        self.assertGreater(metrics["terms_precision"], 0)
        self.assertLessEqual(metrics["terms_precision"], 1)

    def test_grounded_ratio(self) -> None:
        transcript = "параграф 12 номера 345 и 346"
        self.assertEqual(grounded_ratio("Параграф 12, номера 345", transcript), 1.0)
        self.assertLess(grounded_ratio("Параграф 99, номера 345", transcript), 1.0)


class EngineTest(unittest.TestCase):
    def test_analyze_returns_result(self) -> None:
        result = analyze(ALGEBRA, AnalyticConfig())
        self.assertTrue(result.key_terms)
        self.assertTrue(result.key_sentences)
        self.assertIn("параграф", " ".join(result.homework_candidates).lower())
        self.assertGreater(result.stats.get("sentences", 0), 0)
        markdown = render_analytic_md(result)
        self.assertIn("Ключевые термины", markdown)


if __name__ == "__main__":
    unittest.main()
