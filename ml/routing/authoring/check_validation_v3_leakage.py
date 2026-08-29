"""
Re-run the validation-v3 leakage check so QA can verify independence.

    python ml/routing/authoring/check_validation_v3_leakage.py
    python ml/routing/authoring/check_validation_v3_leakage.py --json

Compares `validation-v3.json` against train-v1, frozen action-eval-v1,
validation-v1, and validation-v2 (live files if present, otherwise the
vendored ask fingerprints). Drop-rule hits fail the process.

This script does not score routers and does not select a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from leakage_v3 import (  # noqa: E402
    DROP_DETECTORS,
    JACCARD_THRESHOLD,
    find_id_hits,
    find_text_hits,
    leftover_jaccard_below_threshold,
    load_reference_splits,
)

REPO = Path(__file__).resolve().parents[3]
V3 = REPO / "agent-service/evals/datasets/validation/validation-v3.json"
DEPARTMENTS = {
    "accounting",
    "admin_records",
    "customer_service",
    "invoicing",
    "marketing",
    "operations",
    "people",
    "sales",
}


def load_v3() -> list[dict]:
    payload = json.loads(V3.read_text())
    return list(payload["cases"])


def check(cases: list[dict]) -> dict:
    refs = load_reference_splits()
    text_hits = find_text_hits(cases, refs)
    id_hits = find_id_hits(cases, refs)
    drop_hits = [h for h in (text_hits + id_hits) if h.detector in DROP_DETECTORS]
    leftover_ngram = [h for h in text_hits if h.detector == "NGRAM"]
    leftover_j = leftover_jaccard_below_threshold(cases, refs)

    depts = Counter(c["department_label"] for c in cases)
    pairs: dict[str, list[str]] = {}
    for c in cases:
        if c.get("pair_id"):
            pairs.setdefault(c["pair_id"], []).append(c["id"])

    pair_size_histogram = dict(Counter(len(ids) for ids in pairs.values()))
    split_pairs = {pid: ids for pid, ids in pairs.items() if len(ids) != 2}
    none_labels = [c["id"] for c in cases if c.get("department_label") == "none" or c.get("expected_department") == "none"]

    report = {
        "n_kept": len(cases),
        "n_dropped_on_this_pass": len(drop_hits),
        "drop_hits_by_detector": dict(Counter(h.detector for h in drop_hits)),
        "drop_hits_by_ref_split": dict(Counter(h.ref_split for h in drop_hits)),
        "leftover_ngram_hits": len(leftover_ngram),
        "leftover_near_duplicates_jaccard_0_55_0_80": leftover_j,
        "department_counts": dict(depts),
        "pair_count": len(pairs),
        "pair_size_histogram": pair_size_histogram,
        "split_pairs": split_pairs,
        "none_labels": none_labels,
        "thresholds": {"jaccard": JACCARD_THRESHOLD},
        "clean": not drop_hits and not split_pairs and not none_labels,
        "drop_examples": [
            {
                "detector": h.detector,
                "similarity": h.similarity,
                "v3_id": h.v3_id,
                "v3_ask": h.v3_ask,
                "ref_split": h.ref_split,
                "ref_id": h.ref_id,
                "ref_ask": h.ref_ask,
            }
            for h in drop_hits[:20]
        ],
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not V3.exists():
        print(f"missing {V3}", file=sys.stderr)
        return 2
    report = check(load_v3())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("validation-v3 leakage check")
        print(f"  n kept: {report['n_kept']}")
        print(f"  drop-rule hits on this pass: {report['n_dropped_on_this_pass']}")
        print(f"  leftover n-gram hits (reported, not dropped): {report['leftover_ngram_hits']}")
        print(f"  leftover Jaccard 0.55–0.80: {len(report['leftover_near_duplicates_jaccard_0_55_0_80'])}")
        print("  department counts:")
        for dept, n in sorted(report["department_counts"].items()):
            print(f"    {dept:<16}{n}")
        print(f"  complete pairs: {report['pair_count']}")
        print(f"  pair_id size histogram: {report['pair_size_histogram']}")
        print(f"  clean: {report['clean']}")
        if report["drop_examples"]:
            print("\n  drop examples:")
            for ex in report["drop_examples"]:
                print(f"    [{ex['detector']}] {ex['v3_id']} vs {ex['ref_split']}:{ex['ref_id']}")
                print(f"      v3 : {ex['v3_ask'][:90]!r}")
                print(f"      ref: {ex['ref_ask'][:90]!r}")
    return 0 if report["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
