from __future__ import annotations

import networkx as nx
from networkx.algorithms.link_analysis.pagerank_alg import pagerank
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from lessondigest.analytic.preprocess import lemmas

SIMILARITY_THRESHOLD = 0.05


def rank_sentences(
    sentences: list[str],
    *,
    top_n: int = 7,
    min_chars: int = 40,
) -> list[str]:
    candidates = [
        (index, sentence)
        for index, sentence in enumerate(sentences)
        if len(sentence) >= min_chars and lemmas(sentence)
    ]
    if not candidates:
        return []

    texts = [sentence for _, sentence in candidates]
    if len(texts) == 1:
        return [texts[0]]

    vectorizer = TfidfVectorizer(
        analyzer="word",
        tokenizer=lemmas,
        token_pattern=None,
        preprocessor=None,
        lowercase=False,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    similarity = cosine_similarity(matrix)

    graph = nx.Graph()
    graph.add_nodes_from(range(len(texts)))
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            weight = float(similarity[i, j])
            if weight > SIMILARITY_THRESHOLD:
                graph.add_edge(i, j, weight=weight)

    if graph.number_of_edges() == 0:
        scores = {i: 1.0 for i in range(len(texts))}
    else:
        scores = pagerank(graph, weight="weight")

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_n]
    chosen = sorted(index for index, _ in ranked)
    return [texts[index] for index in chosen]
