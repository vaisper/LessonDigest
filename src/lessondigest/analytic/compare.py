from __future__ import annotations

import re

from lessondigest.analytic.preprocess import lemmas
from lessondigest.domain import AnalyticResult, Digest

_NUMBER = re.compile(r"\d+")


def _lemma_set(text: str) -> set[str]:
    return set(lemmas(text))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def terms_in_texts(terms: list[str], texts: list[str]) -> float:
    if not terms:
        return 0.0
    target_sets = [_lemma_set(text) for text in texts]
    covered = 0
    for term in terms:
        term_lemmas = _lemma_set(term)
        if term_lemmas and any(term_lemmas <= target for target in target_sets):
            covered += 1
    return covered / len(terms)


def texts_hit_by_terms(texts: list[str], terms: list[str]) -> float:
    if not texts:
        return 0.0
    term_sets = [_lemma_set(term) for term in terms]
    covered = 0
    for text in texts:
        text_lemmas = _lemma_set(text)
        if any(term_lemmas and term_lemmas <= text_lemmas for term_lemmas in term_sets):
            covered += 1
    return covered / len(texts)


def sentence_coverage(
    source_sentences: list[str],
    target_texts: list[str],
    threshold: float = 0.25,
) -> float:
    if not source_sentences:
        return 0.0
    target_sets = [_lemma_set(text) for text in target_texts]
    covered = 0
    for sentence in source_sentences:
        sentence_lemmas = _lemma_set(sentence)
        best = max((_jaccard(sentence_lemmas, target) for target in target_sets), default=0.0)
        if best >= threshold:
            covered += 1
    return covered / len(source_sentences)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compare_terms(our_terms: list[str], llm_concepts: list[str]) -> dict[str, float]:
    precision = terms_in_texts(our_terms, llm_concepts)
    recall = texts_hit_by_terms(llm_concepts, our_terms)
    return {
        "terms_our": float(len(our_terms)),
        "terms_llm": float(len(llm_concepts)),
        "terms_precision": round(precision, 3),
        "terms_recall": round(recall, 3),
        "terms_f1": round(_f1(precision, recall), 3),
    }


def compare_sentences(our_sentences: list[str], llm_key_points: list[str]) -> dict[str, float]:
    precision = sentence_coverage(our_sentences, llm_key_points)
    recall = sentence_coverage(llm_key_points, our_sentences)
    return {
        "sentences_precision": round(precision, 3),
        "sentences_recall": round(recall, 3),
        "sentences_f1": round(_f1(precision, recall), 3),
    }


def grounded_ratio(text: str | None, transcript: str) -> float:
    numbers = set(_NUMBER.findall(text or ""))
    if not numbers:
        return 1.0
    transcript_numbers = set(_NUMBER.findall(transcript or ""))
    return round(len(numbers & transcript_numbers) / len(numbers), 3)


def compare_digest(
    analytic: AnalyticResult,
    digest: Digest,
    transcript: str,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    metrics.update(compare_terms(analytic.key_terms, digest.concepts))
    metrics.update(compare_sentences(analytic.key_sentences, digest.key_points))
    metrics["homework_grounded"] = grounded_ratio(digest.homework, transcript)
    if digest.formulas:
        metrics["formulas_grounded"] = grounded_ratio(" ".join(digest.formulas), transcript)
    return metrics
