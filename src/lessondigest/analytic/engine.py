from __future__ import annotations

import time

from lessondigest.analytic import homework as homework_detector
from lessondigest.analytic import keywords, textrank
from lessondigest.analytic.preprocess import lemmas, split_sentences
from lessondigest.config import AnalyticConfig
from lessondigest.domain import AnalyticResult


def analyze(
    text: str,
    config: AnalyticConfig,
    *,
    run_id: str = "",
    background: list[str] | None = None,
) -> AnalyticResult:
    started = time.perf_counter()
    sentences = split_sentences(text)

    key_terms = keywords.extract_key_terms(
        sentences,
        top_k=config.top_terms,
        ngram_max=config.ngram_max,
        background=background,
    )
    key_sentences = textrank.rank_sentences(
        sentences,
        top_n=config.top_sentences,
        min_chars=config.min_sentence_chars,
    )
    homework_candidates, confidence = homework_detector.detect_homework(sentences)

    all_lemmas = lemmas(text)
    stats = {
        "sentences": float(len(sentences)),
        "tokens": float(len(all_lemmas)),
        "unique_lemmas": float(len(set(all_lemmas))),
    }

    return AnalyticResult(
        run_id=run_id,
        key_terms=key_terms,
        key_sentences=key_sentences,
        homework_candidates=homework_candidates,
        homework_confidence=confidence,
        elapsed_sec=round(time.perf_counter() - started, 3),
        stats=stats,
    )
