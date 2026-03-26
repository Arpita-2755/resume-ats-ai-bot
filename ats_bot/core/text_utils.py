from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "no",
    "not",
    "of",
    "on",
    "or",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "will",
    "with",
    "you",
    "your",
    "we",
    "our",
    "have",
    "has",
    "had",
    "can",
    "must",
    "should",
    "required",
    "requirement",
    "requirements",
    "preferred",
    "plus",
    "ability",
    "experience",
    "work",
    "working",
    "years",
    "year",
    "using",
    "strong",
    "good",
    "excellent",
    "knowledge",
    "skills",
    "skill",
    "role",
    "job",
    "position",
    "team",
    "company",
    "candidate",
    "etc",
}


def normalize_text(text: str) -> str:
    text = text.replace("\u2022", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#\-.]{1,}", normalize_text(text))


def extract_keywords(text: str, limit: int = 30) -> list[str]:
    tokens = tokenize_words(text)
    tokens = [token for token in tokens if token not in STOPWORDS and len(token) > 2]
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]

