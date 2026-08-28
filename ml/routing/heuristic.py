"""
Model A — the production heuristic router, as a Python-callable baseline.

Shells out to the real `classifyHeuristic` in the TypeScript engine rather than
reimplementing its scoring here. A baseline you reimplemented is a baseline you
can get subtly wrong in your own favour, and the whole experiment rests on this
number being the thing production actually does.

Latency is measured on the TS side per ask (`latency_ms` in the exporter),
excluding Node startup, so it is comparable with the in-process Python models.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Sequence

from evaluate import Prediction

REPO = Path(__file__).resolve().parents[2]
AGENT_SERVICE = REPO / "agent-service"
EXPORTER = AGENT_SERVICE / "evals" / "export-heuristic-predictions.ts"


def predict(asks: Sequence[str]) -> list[Prediction]:
    payload = "\n".join(json.dumps({"ask": a}) for a in asks) + "\n"
    proc = subprocess.run(
        ["node", "--experimental-strip-types", str(EXPORTER)],
        input=payload, capture_output=True, text=True, cwd=AGENT_SERVICE, check=True,
    )
    out: list[Prediction] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.append(Prediction(
            predicted=row["predicted"],
            confidence=float(row["confidence"]),
            ranked=[c["agentId"] for c in row["ranked"]],
            latency_ms=float(row["latency_ms"]),
            # Raw evidence, kept because the orchestrator's own routing decision
            # is made on it (`MIN_BUSINESS_EVIDENCE`), not on the saturated
            # confidence. A hybrid that triggers on anything else would be
            # covering a different set of cases than production actually drops.
            proba={"_score": float(row["score"])},
        ))
    assert len(out) == len(asks), f"exporter returned {len(out)} rows for {len(asks)} asks"
    return out
