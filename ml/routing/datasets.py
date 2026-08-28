"""
Dataset loading and leakage control for the routing experiment.

Three splits, three different permissions:

  train       ml/routing/data/train-v1.jsonl        fit freely
  validation  agent-service/evals/datasets/validation/validation-v1.json
                                                    select models, tune, inspect
  test        agent-service/evals/datasets/action-eval-v1.json
                                                    measure once, at the end

The frozen test split is the same 215-case action benchmark the engine is
scored against. It is loaded here read-only and only for the final comparison.
Nothing in this module lets a fitting routine reach it: `load_test` is the one
function that touches it and every trainer takes its data from `load_train`.

Leakage is checked empirically rather than asserted. Two independent tests:
exact match on normalised text, and near-duplicate match on token Jaccard
similarity. Writing "I did not look at the test set" in a comment is not a
control; a script that fails the build if an ask overlaps is.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRAIN_PATH = Path(__file__).resolve().parent / "data" / "train-v1.jsonl"
VALIDATION_PATH = REPO / "agent-service/evals/datasets/validation/validation-v1.json"
TEST_PATH = REPO / "agent-service/evals/datasets/action-eval-v1.json"

TRAIN_VERSION = "routing-train-v1"
VALIDATION_VERSION = "action-eval-validation-v1"
TEST_VERSION = "action-eval-v1"

#: The eight routable departments. `none` is deliberately NOT a class: the
#: orchestrator decides out-of-scope, destructive and system-meta asks
#: deterministically, before any classifier runs. A model that could predict
#: "none" would be a model with an opinion about policy.
DEPARTMENTS = [
    "accounting", "admin_records", "customer_service", "invoicing",
    "marketing", "operations", "people", "sales",
]


@dataclass(frozen=True)
class Split:
    name: str
    version: str
    asks: list[str]
    labels: list[str]
    #: Per-case ids where the source provides them (validation/test), else None.
    ids: list[str] | None = None
    #: Template provenance, present for the generated training split only.
    #: Used as the cross-validation grouping key so a template cannot appear in
    #: both a fit fold and a scoring fold.
    groups: list[str] | None = None

    def __len__(self) -> int:
        return len(self.asks)


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_normalise(text).split())


def load_train() -> Split:
    rows = [json.loads(line) for line in TRAIN_PATH.read_text().splitlines() if line.strip()]
    return Split(
        "train", TRAIN_VERSION,
        [r["ask"] for r in rows],
        [r["department_label"] for r in rows],
        groups=[r.get("template_id", "ungrouped") for r in rows],
    )


def _load_eval_split(path: Path, name: str, version: str) -> Split:
    data = json.loads(path.read_text())
    cases = [c for c in data["cases"] if c["expected_department"] in DEPARTMENTS]
    return Split(
        name, version,
        [c["ask"] for c in cases],
        [c["expected_department"] for c in cases],
        [c["id"] for c in cases],
    )


def load_validation() -> Split:
    return _load_eval_split(VALIDATION_PATH, "validation", VALIDATION_VERSION)


def load_test() -> Split:
    """
    The frozen split. Call this ONCE, in the final comparison.

    Cases labelled `none` are excluded: those are decided by deterministic
    orchestrator policy before routing, so scoring a department classifier on
    them would measure something it is not permitted to influence.
    """
    return _load_eval_split(TEST_PATH, "test", TEST_VERSION)


# --- Leakage control ---------------------------------------------------------

@dataclass(frozen=True)
class Overlap:
    train_index: int
    train_ask: str
    other_id: str | None
    other_ask: str
    similarity: float


def find_overlaps(train: Split, other: Split, threshold: float = 0.8) -> list[Overlap]:
    """
    Every train example that is an exact or near-duplicate of an evaluation ask.

    Near-duplication is token Jaccard, which is blunt but has the property that
    matters here: it cannot be satisfied by two sentences that merely share a
    topic. Two asks scoring 0.8 share four fifths of their vocabulary, and that
    is a copy with the names changed, not a coincidence.
    """
    other_tokens = [(_tokens(a), a, (other.ids[i] if other.ids else None)) for i, a in enumerate(other.asks)]
    other_exact = {_normalise(a).strip(): (a, (other.ids[i] if other.ids else None)) for i, a in enumerate(other.asks)}

    found: list[Overlap] = []
    for i, ask in enumerate(train.asks):
        norm = _normalise(ask).strip()
        if norm in other_exact:
            hit_ask, hit_id = other_exact[norm]
            found.append(Overlap(i, ask, hit_id, hit_ask, 1.0))
            continue
        toks = _tokens(ask)
        if not toks:
            continue
        for o_toks, o_ask, o_id in other_tokens:
            if not o_toks:
                continue
            sim = len(toks & o_toks) / len(toks | o_toks)
            if sim >= threshold:
                found.append(Overlap(i, ask, o_id, o_ask, round(sim, 3)))
                break
    return found


def leakage_report(threshold: float = 0.8) -> dict:
    train, validation, test = load_train(), load_validation(), load_test()
    v = find_overlaps(train, validation, threshold)
    t = find_overlaps(train, test, threshold)
    return {
        "threshold": threshold,
        "train_size": len(train),
        "validation_size": len(validation),
        "test_size": len(test),
        "train_vs_validation_overlaps": [o.__dict__ for o in v],
        "train_vs_test_overlaps": [o.__dict__ for o in t],
        "clean": not v and not t,
    }


if __name__ == "__main__":
    report = leakage_report()
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("overlaps")}, indent=2))
    for key in ("train_vs_validation_overlaps", "train_vs_test_overlaps"):
        rows = report[key]
        print(f"\n{key}: {len(rows)}")
        for r in rows[:10]:
            print(f"  sim={r['similarity']}  train: {r['train_ask'][:70]!r}")
            print(f"                  eval : {r['other_ask'][:70]!r}  ({r['other_id']})")
