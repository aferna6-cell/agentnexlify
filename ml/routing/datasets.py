"""
Dataset loading and leakage control for the routing experiment.

Three splits, three different permissions:

  train       ml/routing/data/train-v1.jsonl        fit freely
  validation  agent-service/evals/datasets/validation/validation-v2.json
                                                    select models, tune, inspect
                                                    (v1 kept loadable as a regression check)
  test        agent-service/evals/datasets/action-eval-v1.json
                                                    measure once, at the end

The frozen test split is the same 215-case action benchmark the engine is
scored against. It is loaded here read-only and only for the final comparison.
Nothing in this module lets a fitting routine reach it: `load_test` is the one
function that touches it and every trainer takes its data from `load_train`.

Leakage is checked empirically rather than asserted. Writing "I did not look at
the test set" in a comment is not a control; a script that fails the build if an
ask overlaps is. Two detectors live here — exact match on normalised text, and
token Jaccard — and `ml/routing/leakage.py` adds three more (punctuation/case
normalisation, character n-gram cosine, and template-family widening). Both are
runnable: this pair is what the Milestone-5 numbers were produced under, so
keeping it reproduces that audit exactly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TRAIN_PATH = Path(__file__).resolve().parent / "data" / "train-v1.jsonl"
VALIDATION_PATHS = {
    "v1": REPO / "agent-service/evals/datasets/validation/validation-v1.json",
    "v2": REPO / "agent-service/evals/datasets/validation/validation-v2.json",
}
TEST_PATH = REPO / "agent-service/evals/datasets/action-eval-v1.json"

TRAIN_VERSION = "routing-train-v1"
VALIDATION_VERSIONS = {"v1": "action-eval-validation-v1", "v2": "action-eval-validation-v2"}
#: Milestone 6 selects models against v2. v1 is retained as a regression check:
#: it is the split Milestones 4 and 5 were developed against, and it had been
#: driven to ~97%, which is precisely why it can no longer discriminate.
DEFAULT_VALIDATION = "v2"
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
    #: Per-case routing-boundary label, present on validation v2. Lets accuracy
    #: be reported by difficulty instead of pooled into one number that hides
    #: where the failures concentrate.
    stress: list[str] | None = None

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
        stress=([c.get("stress") for c in cases] if any("stress" in c for c in cases) else None),
    )


def load_validation(version: str = DEFAULT_VALIDATION) -> Split:
    """The editable split. v2 by default; v1 remains loadable as a regression check."""
    if version not in VALIDATION_PATHS:
        raise ValueError(f"unknown validation version {version!r}; have {sorted(VALIDATION_PATHS)}")
    return _load_eval_split(VALIDATION_PATHS[version], f"validation-{version}", VALIDATION_VERSIONS[version])


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


def leakage_report(threshold: float = 0.8, validation_version: str = DEFAULT_VALIDATION) -> dict:
    """
    The Milestone-5 two-detector check, kept for continuity.

    `ml/routing/leakage.py` is the Milestone-6 report and adds three further
    detectors (normalised, character n-gram, template family). This one is not
    obsolete — it is the exact check the earlier results were produced under,
    and keeping it runnable is what makes those results still auditable.
    """
    train, validation, test = load_train(), load_validation(validation_version), load_test()
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
