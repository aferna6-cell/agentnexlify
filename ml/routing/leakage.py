"""
Leakage control for the routing experiment.

Milestone 5 shipped two detectors: exact match on normalised text, and token
Jaccard. Both are still here. Milestone 6 adds three more, because the first two
share a blind spot — they are **bag-of-words** tests, and a bag of words cannot
see word order. "Email Sarah about the brake quote" and "About the brake quote,
email Sarah" are Jaccard 1.0 and would be caught; but a training template that
was reworded rather than reordered can sit just under the threshold while still
being the same sentence with two synonyms swapped.

The five detectors, weakest assumption first:

  EXACT           identical after lowercasing and stripping punctuation.
  NORMALISED      identical after additionally collapsing whitespace, unifying
                  quote/dash characters, and stripping a trailing full stop.
                  Catches "email sarah." vs "Email Sarah" — different bytes,
                  same sentence.
  JACCARD         token overlap >= threshold. Order-blind, catches reorderings
                  and small edits.
  NGRAM           character 4-gram cosine similarity >= threshold. Order-aware,
                  and it survives morphology: "invoicing wallace" and "invoice
                  wallace" share almost every 4-gram. This is the detector that
                  catches a reworded template.
  TEMPLATE_FAMILY where the training row carries `template_id`, any evaluation
                  ask that trips ANY detector against ANY row of that template
                  implicates the WHOLE family. One slot-fill colliding means the
                  template can generate the collision, so the exposure is the
                  template, not the single row.

Nothing here drops anything. It reports. `build_dataset.py` owns the decision to
drop a colliding training row, and it prints the count when it does — a detector
that silently deletes its own findings cannot be audited, and a leakage report
whose headline number is "0" because the evidence was removed before counting is
worse than no report.

    python ml/routing/leakage.py                  # all splits, human-readable
    python ml/routing/leakage.py --json           # machine-readable
    python ml/routing/leakage.py --validation-version v2
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

import datasets

#: Token-overlap threshold. Two asks at 0.8 share four fifths of their
#: vocabulary: that is a copy with the names changed, not a shared topic.
JACCARD_THRESHOLD = 0.80
#: Character 4-gram cosine threshold. Deliberately higher than the Jaccard bar:
#: character n-grams overlap far more readily between unrelated English
#: sentences (every "the", "ing", "tion"), so 0.8 here would fire constantly.
NGRAM_THRESHOLD = 0.85
NGRAM_N = 4

_QUOTES = {ord(c): "'" for c in "‘’ʼ`´"}
_QUOTES.update({ord(c): '"' for c in "“”"})
_DASHES = {ord(c): "-" for c in "‐‑‒–—―"}


def normalise(text: str) -> str:
    """Lowercase, unify unicode punctuation, strip non-alphanumerics, collapse space."""
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def exact_key(text: str) -> str:
    """The Milestone-5 key: lowercase, punctuation to spaces. Kept bit-compatible."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def tokens(text: str) -> frozenset[str]:
    return frozenset(normalise(text).split())


def char_ngrams(text: str, n: int = NGRAM_N) -> Counter:
    s = f" {normalise(text)} "
    return Counter(s[i : i + n] for i in range(max(0, len(s) - n + 1)))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = a.keys() & b.keys()
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True)
class Collision:
    detector: str
    similarity: float
    train_index: int
    train_ask: str
    train_template: str | None
    eval_id: str | None
    eval_ask: str

    def line(self) -> str:
        return (
            f"  [{self.detector}] sim={self.similarity:.3f}"
            f"  template={self.train_template}\n"
            f"      train: {self.train_ask[:88]!r}\n"
            f"      eval : {self.eval_ask[:88]!r}  ({self.eval_id})"
        )


def _fingerprints(asks: Sequence[str]) -> tuple[list[frozenset[str]], list[Counter]]:
    return [tokens(a) for a in asks], [char_ngrams(a) for a in asks]


def find_collisions(
    train: datasets.Split,
    other: datasets.Split,
    jaccard_threshold: float = JACCARD_THRESHOLD,
    ngram_threshold: float = NGRAM_THRESHOLD,
) -> list[Collision]:
    """
    Every train/eval pair that any detector flags.

    One Collision per (train row, detector) at most — the first eval ask that
    trips a given detector is enough to establish the exposure, and listing all
    of them buries the finding. A single train row can appear under more than
    one detector, which is informative: EXACT and NGRAM both firing is a
    verbatim copy, NGRAM alone is a rewording.
    """
    t_tokens, t_grams = _fingerprints(train.asks)
    o_tokens, o_grams = _fingerprints(other.asks)
    o_ids = other.ids or [None] * len(other.asks)

    exact_index: dict[str, int] = {}
    norm_index: dict[str, int] = {}
    for i, a in enumerate(other.asks):
        exact_index.setdefault(exact_key(a), i)
        norm_index.setdefault(normalise(a), i)

    found: list[Collision] = []

    def add(detector: str, sim: float, ti: int, oi: int) -> None:
        found.append(Collision(
            detector=detector, similarity=round(sim, 4), train_index=ti,
            train_ask=train.asks[ti],
            train_template=(train.groups[ti] if train.groups else None),
            eval_id=o_ids[oi], eval_ask=other.asks[oi],
        ))

    for i, ask in enumerate(train.asks):
        hit = exact_index.get(exact_key(ask))
        if hit is not None:
            add("EXACT", 1.0, i, hit)
        hit = norm_index.get(normalise(ask))
        if hit is not None:
            add("NORMALISED", 1.0, i, hit)

        best_j = (0.0, -1)
        best_n = (0.0, -1)
        for j in range(len(other.asks)):
            sj = jaccard(t_tokens[i], o_tokens[j])
            if sj > best_j[0]:
                best_j = (sj, j)
            sn = cosine(t_grams[i], o_grams[j])
            if sn > best_n[0]:
                best_n = (sn, j)
        if best_j[0] >= jaccard_threshold:
            add("JACCARD", best_j[0], i, best_j[1])
        if best_n[0] >= ngram_threshold:
            add("NGRAM", best_n[0], i, best_n[1])

    return found


def template_families(collisions: Iterable[Collision], train: datasets.Split) -> dict:
    """
    Widen each collision from the row to the template that produced it.

    A generator template that can emit one colliding sentence can emit others;
    the honest unit of exposure is therefore the template family and its size,
    not the single row that happened to trip the detector.
    """
    if not train.groups:
        return {"available": False, "reason": "training split carries no template_id metadata"}

    size = Counter(train.groups)
    implicated: dict[str, set[str]] = defaultdict(set)
    for c in collisions:
        if c.train_template:
            implicated[c.train_template].add(c.detector)

    rows = sorted(
        ({"template_id": t, "family_size": size[t], "detectors": sorted(d)}
         for t, d in implicated.items()),
        key=lambda r: -r["family_size"],
    )
    return {
        "available": True,
        "templates_total": len(size),
        "templates_implicated": len(rows),
        "rows_exposed": sum(r["family_size"] for r in rows),
        "families": rows,
    }


def report(validation_version: str = "v3") -> dict:
    train = datasets.load_train()
    validation = datasets.load_validation(validation_version)
    test = datasets.load_test()

    pairs = {
        "train_vs_validation": find_collisions(train, validation),
        "train_vs_test": find_collisions(train, test),
        "validation_vs_test": find_collisions(validation, test),
    }

    out: dict = {
        "thresholds": {"jaccard": JACCARD_THRESHOLD, "ngram_cosine": NGRAM_THRESHOLD, "ngram_n": NGRAM_N},
        "sizes": {"train": len(train), f"validation({validation_version})": len(validation), "test": len(test)},
        "detectors": ["EXACT", "NORMALISED", "JACCARD", "NGRAM", "TEMPLATE_FAMILY"],
        "pairs": {},
        "note": (
            "Nothing is dropped here. build_dataset.py drops colliding TRAINING rows at "
            "generation time and prints the count; this report is the independent check that "
            "it worked, run against the splits as they now stand."
        ),
    }
    clean = True
    for name, cols in pairs.items():
        by_detector = Counter(c.detector for c in cols)
        fam = template_families(cols, train) if name.startswith("train") else {"available": False,
                                                                              "reason": "not a training split"}
        out["pairs"][name] = {
            "collisions": len(cols),
            "by_detector": dict(by_detector),
            "template_families": fam,
            "examples": [asdict(c) for c in cols[:20]],
        }
        clean = clean and not cols
    out["clean"] = clean
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validation-version", default="v3", choices=["v3"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rep = report(args.validation_version)
    if args.json:
        print(json.dumps(rep, indent=2))
        return

    print("Leakage report")
    print(f"  thresholds: jaccard>={rep['thresholds']['jaccard']}  "
          f"ngram{rep['thresholds']['ngram_n']}-cosine>={rep['thresholds']['ngram_cosine']}")
    for k, v in rep["sizes"].items():
        print(f"  {k:<22}{v}")
    for name, p in rep["pairs"].items():
        print(f"\n{name}: {p['collisions']} collision(s)")
        if p["by_detector"]:
            print("  by detector: " + ", ".join(f"{k}={v}" for k, v in sorted(p["by_detector"].items())))
        fam = p["template_families"]
        if fam.get("available") and fam["templates_implicated"]:
            print(f"  template families implicated: {fam['templates_implicated']}"
                  f"/{fam['templates_total']}  ({fam['rows_exposed']} rows exposed)")
        for c in p["examples"]:
            print(Collision(**c).line())
    print(f"\nclean: {rep['clean']}")


if __name__ == "__main__":
    main()
