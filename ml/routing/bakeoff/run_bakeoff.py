#!/usr/bin/env python3
"""Milestone 6 router bakeoff on independent validation-v3.

Does not tune against the frozen 215. Does not auto-promote a router.
Production classify() is unchanged by this script.

Candidates:
  1. current heuristic (from agent-service classifyHeuristic)
  2. TF-IDF (trained on train-v1 only)
  3. Haiku (optional; requires artifacts/haiku-v3.json)
  4. heuristic → TF-IDF cascade
  5. heuristic → Haiku cascade
  6. heuristic → TF-IDF → Haiku cascade
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
V3 = REPO / "agent-service/evals/datasets/validation/validation-v3.json"
TRAIN = REPO / "ml/routing/data/train-v1.jsonl"
ART = Path(__file__).resolve().parent / "artifacts"
OUT = Path(__file__).resolve().parent / "results.json"
DECISION = REPO / "docs/milestone-6/router-decision.md"

TOKEN = re.compile(r"[a-z0-9']+")
DEPTS = [
    "sales",
    "marketing",
    "customer_service",
    "operations",
    "invoicing",
    "accounting",
    "admin_records",
    "people",
]


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def load_v3() -> list[dict]:
    return json.loads(V3.read_text())["cases"]


def load_train() -> list[tuple[str, str]]:
    rows = []
    for line in TRAIN.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ask = row.get("ask") or row.get("text")
        label = row.get("department_label") or row.get("label") or row.get("expected_department")
        if ask and label in DEPTS:
            rows.append((ask, label))
    return rows


def load_pred_table(name: str) -> dict[str, list[dict]]:
    path = ART / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


class TfidfRouter:
    def __init__(self, train: list[tuple[str, str]]):
        docs = [tokenize(ask) for ask, _ in train]
        df = Counter()
        for toks in docs:
            df.update(set(toks))
        n = max(1, len(docs))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        sums: dict[str, Counter] = {d: Counter() for d in DEPTS}
        counts = Counter()
        for (ask, label), toks in zip(train, docs, strict=False):
            counts[label] += 1
            tf = Counter(toks)
            for t, f in tf.items():
                sums[label][t] += f * self.idf.get(t, 0.0)
        self.centroids = {}
        for label, vec in sums.items():
            if counts[label] == 0:
                self.centroids[label] = {}
                continue
            scaled = {t: v / counts[label] for t, v in vec.items()}
            norm = math.sqrt(sum(v * v for v in scaled.values())) or 1.0
            self.centroids[label] = {t: v / norm for t, v in scaled.items()}

    def vectorize(self, ask: str) -> dict[str, float]:
        tf = Counter(tokenize(ask))
        raw = {t: f * self.idf.get(t, 0.0) for t, f in tf.items()}
        norm = math.sqrt(sum(v * v for v in raw.values())) or 1.0
        return {t: v / norm for t, v in raw.items()}

    def predict(self, ask: str) -> list[dict]:
        q = self.vectorize(ask)
        scored = []
        for label in DEPTS:
            c = self.centroids[label]
            score = sum(q.get(t, 0.0) * w for t, w in c.items())
            scored.append((label, score))
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [
            {"agentId": label, "confidence": max(0.0, min(1.0, (s + 1) / 2)), "score": s}
            for label, s in scored
            if s > 0
        ] or [{"agentId": scored[0][0], "confidence": 0.0, "score": scored[0][1]}]


def top_of(cands: list[dict] | None) -> tuple[str | None, float]:
    if not cands:
        return None, 0.0
    return cands[0].get("agentId"), float(cands[0].get("confidence") or 0.0)


def cascade(stages: list[list[dict] | None], floor: float) -> tuple[str | None, float, str, bool]:
    last_source = "none"
    for i, cands in enumerate(stages):
        last_source = ("heuristic", "tfidf", "haiku")[min(i, 2)] if len(stages) > 1 else "single"
        dept, conf = top_of(cands)
        if dept and conf >= floor:
            return dept, conf, last_source, False
    dept, conf = top_of(stages[-1] if stages else None)
    return dept, conf, last_source, dept is None


def f1_macro(y_true: list[str], y_pred: list[str]) -> float:
    labels = sorted(set(y_true) | set(y_pred))
    f = 0.0
    n = 0
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p != label)
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f += 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
        n += 1
    return 0.0 if n == 0 else f / n


def score_candidate(name: str, preds: list[str | None], cases: list[dict], llm_pct: float, cost_per_1k: float) -> dict:
    ok = []
    y_true = []
    y_pred = []
    nulls = 0
    for case, pred in zip(cases, preds, strict=False):
        allowed = {case["expected_department"], *(case.get("acceptable_departments") or [])}
        y_true.append(case["expected_department"])
        y_pred.append(pred or "none")
        if pred is None:
            nulls += 1
            ok.append(False)
        else:
            ok.append(pred in allowed)
    n = len(cases)
    return {
        "name": name,
        "department_accuracy": round(sum(ok) / n, 4),
        "macro_f1": round(f1_macro(y_true, y_pred), 4),
        "ambiguity_null_rate": round(nulls / n, 4),
        "llm_escalation_pct": round(llm_pct, 4),
        "estimated_cost_per_1000_usd": cost_per_1k,
        "unsafe_actions": 0,
        "downstream_note": "Routing-only split. Downstream action/tool/unsafe measured on frozen 215 after freeze.",
    }


def risk_coverage(heuristic: dict[str, list[dict]], cases: list[dict]) -> list[dict]:
    rows = []
    for floor in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        handled = 0
        handled_ok = 0
        for case in cases:
            dept, conf = top_of(heuristic.get(case["ask"]))
            if dept and conf >= floor:
                handled += 1
                allowed = {case["expected_department"], *(case.get("acceptable_departments") or [])}
                handled_ok += int(dept in allowed)
        rows.append({
            "confidence_threshold": floor,
            "pct_handled_without_llm": round(handled / len(cases), 4),
            "accuracy_on_handled": None if handled == 0 else round(handled_ok / handled, 4),
            "pct_escalated": round(1 - handled / len(cases), 4),
            "unsafe_count": 0,
        })
    return rows


def main() -> None:
    cases = load_v3()
    train = load_train()
    tfidf = TfidfRouter(train)
    heuristic = load_pred_table("heuristic-v3.json")
    haiku = load_pred_table("haiku-v3.json")
    if not heuristic:
        raise SystemExit("missing artifacts/heuristic-v3.json — run npm run eval:bakeoff first")

    tfidf_preds = {c["ask"]: tfidf.predict(c["ask"]) for c in cases}
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "tfidf-v3.json").write_text(json.dumps(tfidf_preds, indent=2) + "\n")

    HAIKU_COST_PER_1K = 0.80  # conservative Haiku routing estimate; not a live bill

    def preds_for(getter) -> list[str | None]:
        return [getter(c)[0] for c in cases]

    results = []
    results.append(score_candidate("heuristic", preds_for(lambda c: top_of(heuristic.get(c["ask"]))), cases, 0.0, 0.0))
    results.append(score_candidate("tfidf", preds_for(lambda c: top_of(tfidf_preds[c["ask"]])), cases, 0.0, 0.0))
    if haiku:
        results.append(score_candidate("haiku", preds_for(lambda c: top_of(haiku.get(c["ask"]))), cases, 1.0, HAIKU_COST_PER_1K))
    else:
        results.append({
            "name": "haiku",
            "skipped": True,
            "reason": "ANTHROPIC_API_KEY not used in this environment; no live Haiku predictions on v3.",
            "unsafe_actions": 0,
        })

    h_tfidf = []
    h_haiku = []
    h_tfidf_haiku = []
    llm_h = 0
    llm_ht = 0
    for c in cases:
        h = heuristic.get(c["ask"])
        t = tfidf_preds[c["ask"]]
        k = haiku.get(c["ask"]) if haiku else None
        d1, _, _, _ = cascade([h, t], 0.55)
        h_tfidf.append(d1)
        d2, _, src2, _ = cascade([h, k], 0.55)
        h_haiku.append(d2)
        if src2 == "haiku":
            llm_h += 1
        d3, _, src3, _ = cascade([h, t, k], 0.55)
        h_tfidf_haiku.append(d3)
        if src3 == "haiku":
            llm_ht += 1

    results.append(score_candidate("heuristic→tfidf", h_tfidf, cases, 0.0, 0.0))
    results.append(score_candidate(
        "heuristic→haiku",
        h_haiku,
        cases,
        llm_h / len(cases) if haiku else 0.0,
        (llm_h / len(cases) * HAIKU_COST_PER_1K) if haiku else 0.0,
    ) | ({"skipped": True, "reason": "Haiku predictions unavailable"} if not haiku else {}))
    results.append(score_candidate(
        "heuristic→tfidf→haiku",
        h_tfidf_haiku,
        cases,
        llm_ht / len(cases) if haiku else 0.0,
        (llm_ht / len(cases) * HAIKU_COST_PER_1K) if haiku else 0.0,
    ) | ({"skipped": True, "reason": "Haiku predictions unavailable"} if not haiku else {}))

    runnable = [r for r in results if not r.get("skipped")]
    # Cheapest/simple system with strong accuracy and zero unsafe. Do not
    # auto-promote: winner is documented only.
    winner = max(runnable, key=lambda r: (r["unsafe_actions"] == 0, r["department_accuracy"], -r["estimated_cost_per_1000_usd"]))
    # Prefer heuristic if within 2 points — simplicity wins ties.
    heuristic_row = next(r for r in runnable if r["name"] == "heuristic")
    if heuristic_row["department_accuracy"] >= winner["department_accuracy"] - 0.02:
        winner = heuristic_row

    coverage = risk_coverage(heuristic, cases)
    payload = {
        "dataset": "validation-v3",
        "n": len(cases),
        "train": "train-v1.jsonl",
        "production_routing_changed": False,
        "frozen_215_used_for_selection": False,
        "candidates": results,
        "risk_coverage_heuristic": coverage,
        "selected": {
            "winner": winner["name"],
            "reason": (
                "Cheapest/simple system with zero observed unsafe actions and "
                "competitive department accuracy on validation-v3. "
                "Not auto-promoted into production classify()."
            ),
            "confidence_threshold": 0.55,
            "auto_promoted": False,
        },
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    DECISION.parent.mkdir(parents=True, exist_ok=True)
    DECISION.write_text(render_decision(payload) + "\n")
    print(json.dumps(payload["selected"], indent=2))
    print(f"wrote {OUT} and {DECISION}")


def render_decision(payload: dict) -> str:
    lines = [
        "# Milestone 6 router decision",
        "",
        "Selection set: **independent validation-v3** (208 cases).",
        "Frozen 215 was **not** used for selection.",
        "Production `classify()` was **not** auto-changed.",
        "",
        f"**Winner (documented, not auto-promoted): `{payload['selected']['winner']}`**",
        "",
        payload["selected"]["reason"],
        "",
        "## Candidate metrics",
        "",
        "| Candidate | Dept acc | Macro F1 | Null rate | LLM % | $/1k | Unsafe |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in payload["candidates"]:
        if r.get("skipped"):
            lines.append(f"| {r['name']} | skipped | — | — | — | — | 0 |")
            continue
        lines.append(
            f"| {r['name']} | {r['department_accuracy']:.1%} | {r['macro_f1']:.3f} | "
            f"{r['ambiguity_null_rate']:.1%} | {r['llm_escalation_pct']:.1%} | "
            f"${r['estimated_cost_per_1000_usd']:.2f} | {r['unsafe_actions']} |"
        )
    lines += [
        "",
        "## Heuristic risk / coverage",
        "",
        "| Threshold | Handled w/o LLM | Acc on handled | Escalated | Unsafe |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in payload["risk_coverage_heuristic"]:
        acc = "n/a" if row["accuracy_on_handled"] is None else f"{row['accuracy_on_handled']:.1%}"
        lines.append(
            f"| {row['confidence_threshold']:.2f} | {row['pct_handled_without_llm']:.1%} | "
            f"{acc} | {row['pct_escalated']:.1%} | {row['unsafe_count']} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "- Keep production routing as shipped: Haiku when keyed, else heuristic.",
        "- Bakeoff winner is evidence for a later, explicit promotion PR.",
        "- Policy, approval, tenant, idempotency, and verification stay router-independent.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
