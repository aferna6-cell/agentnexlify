"""Leakage check: independent holdout vs validation (+ optional locked snapshot).

Checks:
  * exact normalized ask match
  * token Jaccard >= 0.80
  * template_family overlap when metadata exists
  * deliberately authored hard-pair markers must stay holdout-only

Exit nonzero on any exact/Jaccard/template hit.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VALIDATION = REPO / "agent-service/evals/datasets/rag/rag-eval-validation-v1.json"
HOLDOUT = REPO / "agent-service/evals/datasets/rag/rag-eval-holdout-v1.json"
REPORT = REPO / "ml/rag/artifacts/rag-holdout-leakage-v1.json"

JACCARD_THRESHOLD = 0.80

_QUOTES = {ord(c): "'" for c in "‘’ʼ`´"}
_QUOTES.update({ord(c): '"' for c in "“”"})
_DASHES = {ord(c): "-" for c in "‐‑‒–—―"}


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def tokens(text: str) -> frozenset[str]:
    return frozenset(normalise(text).split())


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text())["cases"]


def check() -> dict:
    val = load_cases(VALIDATION)
    hold = load_cases(HOLDOUT)
    val_norm = {normalise(c["ask"]): c["id"] for c in val}
    val_tok = [(c["id"], c["ask"], tokens(c["ask"])) for c in val]
    val_families = {
        c.get("template_family")
        for c in val
        if c.get("template_family")
    }

    exact = []
    jac = []
    family = []
    for c in hold:
        n = normalise(c["ask"])
        if n in val_norm:
            exact.append(
                {
                    "holdout_id": c["id"],
                    "validation_id": val_norm[n],
                    "ask": c["ask"],
                }
            )
        ht = tokens(c["ask"])
        best = (0.0, None, None)
        for vid, vask, vt in val_tok:
            score = jaccard(ht, vt)
            if score > best[0]:
                best = (score, vid, vask)
        if best[0] >= JACCARD_THRESHOLD:
            jac.append(
                {
                    "holdout_id": c["id"],
                    "validation_id": best[1],
                    "jaccard": round(best[0], 4),
                    "holdout_ask": c["ask"],
                    "validation_ask": best[2],
                }
            )
        fam = c.get("template_family")
        if fam and fam in val_families:
            family.append({"holdout_id": c["id"], "template_family": fam})

    hard_pairs = [c["id"] for c in hold if "hard_pair" in (c.get("tags") or [])]
    # Hard pairs must not also appear as exact matches in validation.
    hard_leaks = [h for h in exact if h["holdout_id"] in hard_pairs]

    report = {
        "validation_cases": len(val),
        "holdout_cases": len(hold),
        "thresholds": {"jaccard": JACCARD_THRESHOLD},
        "exact_normalized_matches": exact,
        "jaccard_hits": jac,
        "template_family_overlap": family,
        "hard_pair_ids": hard_pairs,
        "hard_pair_leaks": hard_leaks,
        "pass": not exact and not jac and not family and not hard_leaks,
    }
    return report


def main() -> None:
    report = check()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "pass": report["pass"],
        "exact": len(report["exact_normalized_matches"]),
        "jaccard": len(report["jaccard_hits"]),
        "template_family": len(report["template_family_overlap"]),
        "hard_pair_leaks": len(report["hard_pair_leaks"]),
        "holdout_cases": report["holdout_cases"],
    }, indent=2))
    if not report["pass"]:
        print(json.dumps(report["exact_normalized_matches"][:5], indent=2))
        print(json.dumps(report["jaccard_hits"][:5], indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
