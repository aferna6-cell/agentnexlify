"""
Leakage check for the independent validation-v3 split.

Uses the same detectors as `ml/routing/leakage.py` when that module is
importable (exact / normalised / Jaccard / n-gram / template family). On a
main-only checkout those files are not present, so this module also carries
the Milestone-6 detector implementations and reads compact ask fingerprints
from `authoring/baselines/reference-asks-v3-leakage.json`.

Drop rules for v3 (workstream A):

  * exact text match (Milestone-5 key or normalised key)
  * token Jaccard >= 0.8
  * template_id collision with train / frozen / v1 / v2
  * pair_id collision with train / frozen / v1 / v2

N-gram cosine leftovers are *reported* and not used as a drop rule unless the
caller asks. A generator collision closes the whole `template_id` (and any
`pair_id` that would be split).
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

AUTHORING = Path(__file__).resolve().parent
REPO = AUTHORING.parents[2]
BASELINE_PATH = AUTHORING / "baselines" / "reference-asks-v3-leakage.json"

JACCARD_THRESHOLD = 0.80
NGRAM_THRESHOLD = 0.85
NGRAM_N = 4

# Live paths — used when PR #693 (or a later merge) is on the branch.
LIVE_PATHS = {
    "train": REPO / "ml/routing/data/train-v1.jsonl",
    "frozen": REPO / "agent-service/evals/datasets/action-eval-v1.json",
    "validation_v1": REPO / "agent-service/evals/datasets/validation/validation-v1.json",
    "validation_v2": REPO / "agent-service/evals/datasets/validation/validation-v2.json",
}

try:
    import leakage as _upstream  # type: ignore
except ImportError:
    _upstream = None

_QUOTES = {ord(c): "'" for c in "‘’ʼ`´"}
_QUOTES.update({ord(c): '"' for c in "“”"})
_DASHES = {ord(c): "-" for c in "‐‑‒–—―"}


def normalise(text: str) -> str:
    if _upstream is not None:
        return _upstream.normalise(text)
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def exact_key(text: str) -> str:
    if _upstream is not None:
        return _upstream.exact_key(text)
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
class RefRow:
    split: str
    ask: str
    ref_id: str | None
    template_id: str | None
    pair_id: str | None


@dataclass
class Hit:
    detector: str
    similarity: float
    v3_id: str | None
    v3_ask: str
    v3_template: str | None
    v3_pair: str | None
    ref_split: str
    ref_id: str | None
    ref_ask: str
    ref_template: str | None
    ref_pair: str | None


def _eval_cases(payload: dict) -> list[dict]:
    return list(payload.get("cases") or [])


def _load_live_split(name: str, path: Path) -> list[RefRow] | None:
    if not path.exists():
        return None
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return [
            RefRow(
                split=name,
                ask=r["ask"],
                ref_id=r.get("id"),
                template_id=r.get("template_id"),
                pair_id=r.get("pair_id"),
            )
            for r in rows
        ]
    payload = json.loads(path.read_text())
    out: list[RefRow] = []
    for c in _eval_cases(payload):
        out.append(
            RefRow(
                split=name,
                ask=c["ask"],
                ref_id=c.get("id"),
                template_id=c.get("template_id"),
                pair_id=c.get("pair_id"),
            )
        )
    return out


def load_reference_splits(baseline_path: Path = BASELINE_PATH) -> dict[str, list[RefRow]]:
    """
    Prefer live files when present (so a checkout that already has train / frozen
    / v1 / v2 is checked against those bytes). Fall back to the vendored
    fingerprints so this check runs on main, where those files are not yet
    merged.
    """
    baseline = json.loads(baseline_path.read_text())
    key_map = {
        "train": "train",
        "frozen": "frozen",
        "validation_v1": "validation_v1",
        "validation_v2": "validation_v2",
    }
    loaded: dict[str, list[RefRow]] = {}
    for name, bkey in key_map.items():
        live = _load_live_split(name, LIVE_PATHS[name])
        if live is not None:
            loaded[name] = live
            continue
        rows = []
        for r in baseline[bkey]:
            rows.append(
                RefRow(
                    split=name,
                    ask=r["ask"],
                    ref_id=r.get("id"),
                    template_id=r.get("template_id"),
                    pair_id=r.get("pair_id"),
                )
            )
        loaded[name] = rows
    return loaded


def reference_id_sets(refs: dict[str, list[RefRow]]) -> dict[str, set[str]]:
    templates: set[str] = set()
    pairs: set[str] = set()
    for rows in refs.values():
        for r in rows:
            if r.template_id:
                templates.add(r.template_id)
            if r.pair_id:
                pairs.add(r.pair_id)
    return {"template_id": templates, "pair_id": pairs}


def find_text_hits(
    candidates: Sequence[dict],
    refs: dict[str, list[RefRow]],
    *,
    jaccard_threshold: float = JACCARD_THRESHOLD,
    ngram_threshold: float = NGRAM_THRESHOLD,
) -> list[Hit]:
    hits: list[Hit] = []
    for split, rows in refs.items():
        exact_index: dict[str, int] = {}
        norm_index: dict[str, int] = {}
        r_tokens = [tokens(r.ask) for r in rows]
        r_grams = [char_ngrams(r.ask) for r in rows]
        for i, r in enumerate(rows):
            exact_index.setdefault(exact_key(r.ask), i)
            norm_index.setdefault(normalise(r.ask), i)

        for c in candidates:
            ask = c["ask"]
            cid = c.get("id")
            tmpl = c.get("template_id")
            pair = c.get("pair_id")

            def add(detector: str, sim: float, ri: int) -> None:
                ref = rows[ri]
                hits.append(
                    Hit(
                        detector=detector,
                        similarity=round(sim, 4),
                        v3_id=cid,
                        v3_ask=ask,
                        v3_template=tmpl,
                        v3_pair=pair,
                        ref_split=split,
                        ref_id=ref.ref_id,
                        ref_ask=ref.ask,
                        ref_template=ref.template_id,
                        ref_pair=ref.pair_id,
                    )
                )

            ei = exact_index.get(exact_key(ask))
            if ei is not None:
                add("EXACT", 1.0, ei)
            ni = norm_index.get(normalise(ask))
            if ni is not None:
                add("NORMALISED", 1.0, ni)

            c_toks = tokens(ask)
            c_grams = char_ngrams(ask)
            best_j = (0.0, -1)
            best_n = (0.0, -1)
            for j, r in enumerate(rows):
                sj = jaccard(c_toks, r_tokens[j])
                if sj > best_j[0]:
                    best_j = (sj, j)
                sn = cosine(c_grams, r_grams[j])
                if sn > best_n[0]:
                    best_n = (sn, j)
            if best_j[0] >= jaccard_threshold:
                add("JACCARD", best_j[0], best_j[1])
            if best_n[0] >= ngram_threshold:
                add("NGRAM", best_n[0], best_n[1])
    return hits


def find_id_hits(candidates: Sequence[dict], refs: dict[str, list[RefRow]]) -> list[Hit]:
    ids = reference_id_sets(refs)
    hits: list[Hit] = []
    for c in candidates:
        if c.get("template_id") and c["template_id"] in ids["template_id"]:
            hits.append(
                Hit(
                    detector="TEMPLATE_ID",
                    similarity=1.0,
                    v3_id=c.get("id"),
                    v3_ask=c["ask"],
                    v3_template=c.get("template_id"),
                    v3_pair=c.get("pair_id"),
                    ref_split="id_index",
                    ref_id=None,
                    ref_ask="",
                    ref_template=c.get("template_id"),
                    ref_pair=None,
                )
            )
        if c.get("pair_id") and c["pair_id"] in ids["pair_id"]:
            hits.append(
                Hit(
                    detector="PAIR_ID",
                    similarity=1.0,
                    v3_id=c.get("id"),
                    v3_ask=c["ask"],
                    v3_template=c.get("template_id"),
                    v3_pair=c.get("pair_id"),
                    ref_split="id_index",
                    ref_id=None,
                    ref_ask="",
                    ref_template=None,
                    ref_pair=c.get("pair_id"),
                )
            )
    return hits


DROP_DETECTORS = {"EXACT", "NORMALISED", "JACCARD", "TEMPLATE_ID", "PAIR_ID"}


@dataclass
class FilterResult:
    kept: list[dict]
    dropped: list[dict]
    drop_reasons: dict[str, int]
    closed_templates: list[str]
    closed_pairs: list[str]
    leftover_near_duplicates: list[dict]
    hits: list[Hit]

    def as_report(self) -> dict:
        by_detector = Counter(h.detector for h in self.hits)
        by_split = Counter(h.ref_split for h in self.hits if h.detector in DROP_DETECTORS)
        return {
            "n_authored": len(self.kept) + len(self.dropped),
            "n_kept": len(self.kept),
            "n_dropped": len(self.dropped),
            "drop_reasons": dict(self.drop_reasons),
            "closed_templates": self.closed_templates,
            "closed_pairs": self.closed_pairs,
            "hits_by_detector": dict(by_detector),
            "drop_hits_by_ref_split": dict(by_split),
            "leftover_near_duplicates": self.leftover_near_duplicates,
            "example_drops": [
                {
                    "id": c.get("id"),
                    "template_id": c.get("template_id"),
                    "reasons": c.get("_drop_reasons"),
                }
                for c in self.dropped[:20]
            ],
        }


def filter_colliding_templates(
    candidates: Sequence[dict],
    refs: dict[str, list[RefRow]] | None = None,
) -> FilterResult:
    """
    Close any template_id that has a drop-rule hit. Then close any pair_id
    whose remaining halves would be split (one kept, one gone).
    """
    refs = refs or load_reference_splits()
    text_hits = find_text_hits(candidates, refs)
    id_hits = find_id_hits(candidates, refs)
    hits = text_hits + id_hits

    drop_hits = [h for h in hits if h.detector in DROP_DETECTORS]
    closed_templates = sorted({h.v3_template for h in drop_hits if h.v3_template})
    reasons_by_template: dict[str, set[str]] = {}
    for h in drop_hits:
        if h.v3_template:
            reasons_by_template.setdefault(h.v3_template, set()).add(
                f"{h.detector}@{h.ref_split}"
            )

    # First pass: drop closed templates.
    surviving: list[dict] = []
    dropped: list[dict] = []
    for c in candidates:
        tmpl = c.get("template_id")
        if tmpl and tmpl in closed_templates:
            row = dict(c)
            row["_drop_reasons"] = sorted(reasons_by_template.get(tmpl, {"template_closed"}))
            dropped.append(row)
        else:
            surviving.append(dict(c))

    # Second pass: do not split a hard-negative pair across kept/dropped.
    kept_pairs = {c.get("pair_id") for c in surviving if c.get("pair_id")}
    dropped_pairs = {c.get("pair_id") for c in dropped if c.get("pair_id")}
    split_pairs = sorted(p for p in (kept_pairs & dropped_pairs) if p)
    if split_pairs:
        still: list[dict] = []
        for c in surviving:
            if c.get("pair_id") in split_pairs:
                row = dict(c)
                row["_drop_reasons"] = [f"PAIR_SPLIT:{c['pair_id']}"]
                dropped.append(row)
            else:
                still.append(c)
        surviving = still

    # Internal exact-duplicate asks: close those templates too.
    seen_norm: dict[str, str] = {}
    internal_close: set[str] = set()
    for c in surviving:
        key = exact_key(c["ask"])
        if key in seen_norm:
            if c.get("template_id"):
                internal_close.add(c["template_id"])
            if seen_norm[key]:
                internal_close.add(seen_norm[key])
        else:
            seen_norm[key] = c.get("template_id") or ""
    if internal_close:
        still = []
        for c in surviving:
            if c.get("template_id") in internal_close:
                row = dict(c)
                row["_drop_reasons"] = ["INTERNAL_DUPLICATE_ASK"]
                dropped.append(row)
            else:
                still.append(c)
        surviving = still
        closed_templates = sorted(set(closed_templates) | internal_close)

    leftover = [
        asdict(h)
        for h in hits
        if h.detector == "NGRAM"
        and h.v3_template not in closed_templates
        and (h.v3_id in {c.get("id") for c in surviving})
    ]

    reason_counts: Counter[str] = Counter()
    for row in dropped:
        for r in row.get("_drop_reasons") or ["unknown"]:
            reason_counts[r.split("@")[0].split(":")[0]] += 1

    return FilterResult(
        kept=surviving,
        dropped=dropped,
        drop_reasons=dict(reason_counts),
        closed_templates=closed_templates,
        closed_pairs=split_pairs,
        leftover_near_duplicates=leftover,
        hits=hits,
    )


def leftover_jaccard_below_threshold(
    kept: Sequence[dict],
    refs: dict[str, list[RefRow]],
    *,
    floor: float = 0.55,
    ceiling: float = JACCARD_THRESHOLD,
) -> list[dict]:
    """Near-duplicates that survived the drop rule, for the report."""
    out: list[dict] = []
    for c in kept:
        c_toks = tokens(c["ask"])
        best = (0.0, None, None, None)
        for split, rows in refs.items():
            for r in rows:
                sj = jaccard(c_toks, tokens(r.ask))
                if sj > best[0]:
                    best = (sj, split, r.ask, r.ref_id)
        if floor <= best[0] < ceiling:
            out.append(
                {
                    "id": c.get("id"),
                    "ask": c["ask"],
                    "jaccard": round(best[0], 4),
                    "ref_split": best[1],
                    "ref_ask": best[2],
                    "ref_id": best[3],
                }
            )
    return sorted(out, key=lambda r: -r["jaccard"])
