from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pymorphy3
from razdel import sentenize, tokenize

_DATA = Path(__file__).resolve().parent / "data" / "stopwords_ru.txt"
_WORD = re.compile(r"^[а-яёa-z][а-яёa-z\-]{1,}$")


@lru_cache(maxsize=1)
def _morph() -> pymorphy3.MorphAnalyzer:
    return pymorphy3.MorphAnalyzer()


@lru_cache(maxsize=1)
def stopwords() -> frozenset[str]:
    if not _DATA.exists():
        return frozenset()
    words = [
        line.strip().lower()
        for line in _DATA.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return frozenset(words)


def split_sentences(text: str) -> list[str]:
    return [sentence.text.strip() for sentence in sentenize(text or "") if sentence.text.strip()]


@lru_cache(maxsize=50000)
def lemma(word: str) -> str:
    return _morph().parse(word)[0].normal_form


def lemmas(text: str) -> list[str]:
    result: list[str] = []
    for token in tokenize(text or ""):
        word = token.text.lower().strip()
        if not _WORD.match(word):
            continue
        base = lemma(word)
        if base in stopwords():
            continue
        result.append(base)
    return result


def sentence_lemmas(sentences: list[str]) -> list[list[str]]:
    return [lemmas(sentence) for sentence in sentences]
