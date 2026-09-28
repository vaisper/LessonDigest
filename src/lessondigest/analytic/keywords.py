from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer

from lessondigest.analytic.preprocess import lemmas


def extract_key_terms(
    sentences: list[str],
    *,
    top_k: int = 12,
    ngram_max: int = 2,
    background: list[str] | None = None,
) -> list[str]:
    docs = [sentence for sentence in sentences if sentence.strip()]
    if not docs:
        return []

    corpus = list(background or []) + docs
    vectorizer = TfidfVectorizer(
        analyzer="word",
        tokenizer=lemmas,
        token_pattern=None,
        preprocessor=None,
        lowercase=False,
        ngram_range=(1, max(1, ngram_max)),
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(corpus)
    names = vectorizer.get_feature_names_out()

    lesson_rows = matrix[len(corpus) - len(docs) :]
    scores = lesson_rows.sum(axis=0).A1

    ranked = sorted(zip(names, scores), key=lambda item: item[1], reverse=True)
    terms: list[str] = []
    for term, score in ranked:
        if score <= 0:
            break
        terms.append(term)
        if len(terms) >= top_k:
            break
    return terms
