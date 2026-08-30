"""In-process BM25 used by retrieve_business_context.

Kept in backend/ so production does not import ml/.
"""

import math
import re
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-z0-9]+")


def _stem(token: str) -> str:
    """Light English stem so alignment/alignments and cancel/cancelled share a term."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("lled"):
        return token[:-3]  # cancelled -> cancel
    if len(token) > 5 and token.endswith("sses"):
        return token[:-2]  # passes -> pass
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(text.lower())]


@dataclass(frozen=True)
class Scored:
    index: int
    score: float


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(d) for d in documents]
        self.n = len(self.docs)
        self.avgdl = (sum(len(d) for d in self.docs) / self.n) if self.n else 0.0
        self.df: dict[str, int] = {}
        for doc in self.docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, query: str) -> list[Scored]:
        q = tokenize(query)
        if not q or not self.docs:
            return []
        out: list[Scored] = []
        for i, doc in enumerate(self.docs):
            if not doc:
                continue
            tf: dict[str, int] = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            dl = len(doc)
            for term in q:
                if term not in tf:
                    continue
                idf = self._idf(term)
                freq = tf[term]
                s += idf * (freq * (self.k1 + 1)) / (
                    freq + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                )
            if s > 0:
                out.append(Scored(i, s))
        out.sort(key=lambda x: (-x.score, x.index))
        return out
