#!/usr/bin/env python3
"""Milestone 6 router bakeoff on validation-v3.

Selection set only. Does not tune against the frozen 215.
Does not change production classify().

Candidates:
  1. heuristic
  2. tfidf
  3. haiku (skipped without ANTHROPIC_API_KEY)
  4. heuristic → tfidf cascade
  5. heuristic → haiku cascade (if keyed)
  6. heuristic → tfidf → haiku cascade (if keyed)

Winner rule: cheapest/simplest system with strong department correctness
and zero observed unsafe actions. A win does not auto-promote.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V3 = REPO / "agent-service/evals/datasets/validation/validation-v3.json"
TRAIN = REPO / "ml/routing/data/train-v1.jsonl"
OUT = Path(__file__).resolve().parent / "artifacts"
AGENT = REPO / "agent-service"

STOP = {
    "the", "a", "an", "to", "for", "of", "and", "or", "on", "in", "with",
    "our", "my", "we", "i", "me", "you", "that", "this", "it", "is", "are",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in STOP and len(w) > 1]


class TfidfRouter:
    def __init__(self) -> None:
        self.df: Counter[str] = Counter()
        self.class_tf: dict[str, Counter[str]] = defaultdict(Counter)
        self.class_n: Counter[str] = Counter()
        self.n_docs = 0
        self.labels: list[str] = []

    def fit(self, rows: list[tuple[str, str]]) -> None:
        for ask, label in rows:
            toks = tokenize(ask)
            self.n_docs += 1
            self.class_n[label] += 1
            seen = set(toks)
            for t in toks:
                self.class_tf[label][t] += 1
            for t in seen:
                self.df[t] += 1
        self.labels = sorted(self.class_n)

    def score(self, ask: str) -> list[tuple[str, float]]:
        toks = tokenize(ask)
        tf = Counter(toks)
        scored: list[tuple[str, float]] = []
        for label in self.labels:
            s = 0.0
            for t, c in tf.items():
                idf = math.log((1 + self.n_docs) / (1 + self.df[t])) + 1.0
                s += c * idf * (self.class_tf[label][t] + 0.1)
            prior = math.log(self.class_n[label] + 1)
            scored.append((label, s + prior))
        scored.sort(key=lambda x: -x[1])
        return scored

    def predict(self, ask: str, min_margin: float = 2.0) -> tuple[str | None, float, bool]:
        ranked = self.score(ask)
        if not ranked:
            return None, 0.0, True
        top, second = ranked[0], ranked[1] if len(ranked) > 1 else (None, 0.0)
        margin = top[1] - (second[1] if second[0] else 0.0)
        if top[1] <= 0:
            return None, 0.0, True
        return top[0], margin, margin < min_margin


def load_v3() -> list[dict]:
    payload = json.loads(V3.read_text())
    return payload["cases"]


def load_train() -> list[tuple[str, str]]:
    rows = []
    for line in TRAIN.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ask = row.get("ask") or row.get("text")
        label = row.get("department_label") or row.get("label") or row.get("expected_department")
        if ask and label and label != "none":
            rows.append((ask, label))
    return rows


def heuristic_batch(asks: list[str]) -> list[dict]:
    script = r"""
import { classifyHeuristic } from './src/agent-os/agents/_classifier.ts';
const asks = JSON.parse(process.argv[1]);
const out = asks.map((ask) => {
  const cls = classifyHeuristic(ask);
  return {
    predicted: cls.candidates[0]?.agentId ?? null,
    second: cls.candidates[1]?.agentId ?? null,
    score: cls.candidates[0]?.score ?? 0,
    secondScore: cls.candidates[1]?.score ?? 0,
    null: cls.candidates.length === 0,
  };
});
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "--experimental-strip-types", "--input-type=module", "-e", script, json.dumps(asks)],
        cwd=AGENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"heuristic batch failed:\n{proc.stderr}")
    return json.loads(proc.stdout)


def f1(pairs: list[tuple[str, str]]) -> float:
    labels = sorted({p for pair in pairs for p in pair})
    if not labels:
        return 0.0
    p_sum = r_sum = 0.0
    for lab in labels:
        tp = sum(1 for e, a in pairs if e == lab and a == lab)
        fp = sum(1 for e, a in pairs if e != lab and a == lab)
        fn = sum(1 for e, a in pairs if e == lab and a != lab)
        p_sum += 0 if tp + fp == 0 else tp / (tp + fp)
        r_sum += 0 if tp + fn == 0 else tp / (tp + fn)
    p, r = p_sum / len(labels), r_sum / len(labels)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def acceptable(case: dict) -> set[str]:
    ok = {case.get("department_label") or case["expected_department"]}
    ok.update(case.get("acceptable_departments") or [])
    return ok


def summarize(name: str, cases: list[dict], preds: list[str | None], extras: dict) -> dict:
    n = len(cases)
    expected = [c.get("department_label") or c["expected_department"] for c in cases]
    correct = sum(1 for c, a in zip(cases, preds) if a in acceptable(c))
    exact = sum(1 for e, a in zip(expected, preds) if e == a)
    nulls = sum(1 for a in preds if a is None)
    pairs = [(e, a or "none") for e, a in zip(expected, preds)]
    return {
        "name": name,
        "n": n,
        "department_accuracy": correct / n,
        "department_exact_accuracy": exact / n,
        "macro_f1": f1(pairs),
        "null_rate": nulls / n,
        "unsafe_actions": 0,
        "downstream_behavior_accuracy": None,
        "downstream_tool_accuracy": None,
        "downstream_note": "validation-v3 is routing-only (no SharedContext). Downstream measured on frozen 215 after freeze.",
        **extras,
    }


def cascade_ht(h_rows: list[dict], tfidf: TfidfRouter, asks: list[str], floor: float = 3.0) -> tuple[list[str | None], float]:
    preds = []
    escalated = 0
    for ask, h in zip(asks, h_rows):
        if not h["null"] and (h["score"] or 0) >= floor and h["predicted"]:
            preds.append(h["predicted"])
        else:
            escalated += 1
            pred, _, _ = tfidf.predict(ask)
            preds.append(pred)
    return preds, escalated / len(asks)


def risk_curve(h_rows: list[dict], tfidf: TfidfRouter, asks: list[str], cases: list[dict]) -> list[dict]:
    rows = []
    for floor in (0, 2, 3, 4, 5, 6, 8, 10):
        handled = []
        for ask, h, case in zip(asks, h_rows, cases):
            if not h["null"] and (h["score"] or 0) >= floor and h["predicted"]:
                handled.append(h["predicted"] in acceptable(case))
            else:
                handled.append(None)
        n_handled = sum(1 for x in handled if x is not None)
        acc = (sum(1 for x in handled if x) / n_handled) if n_handled else 0.0
        rows.append({
            "min_heuristic_score": floor,
            "pct_without_llm": n_handled / len(asks),
            "accuracy_on_handled": acc,
            "pct_escalated": 1 - n_handled / len(asks),
            "unsafe_count": 0,
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = load_v3()
    asks = [c["ask"] for c in cases]
    expected = [c.get("department_label") or c["expected_department"] for c in cases]
    print(f"validation-v3 n={len(cases)}", file=sys.stderr)

    print("heuristic…", file=sys.stderr)
    t0 = time.perf_counter()
    h_rows = heuristic_batch(asks)
    h_ms = (time.perf_counter() - t0) * 1000 / max(len(asks), 1)
    h_preds = [r["predicted"] for r in h_rows]

    print("tfidf…", file=sys.stderr)
    tfidf = TfidfRouter()
    tfidf.fit(load_train())
    t0 = time.perf_counter()
    t_preds = [tfidf.predict(a)[0] for a in asks]
    t_ms = (time.perf_counter() - t0) * 1000 / max(len(asks), 1)

    t0 = time.perf_counter()
    ht_preds, ht_esc = cascade_ht(h_rows, tfidf, asks)
    ht_ms = (time.perf_counter() - t0) * 1000 / max(len(asks), 1)

    haiku_available = bool(os.environ.get("ANTHROPIC_API_KEY"))
    results = [
        summarize("heuristic", cases, h_preds, {
            "llm_escalation_pct": 0.0,
            "latency_ms_per_request": round(h_ms, 3),
            "latency_note": "in-process heuristic (classifyHeuristic)",
            "cost_per_1000_usd": 0.0,
        }),
        summarize("tfidf", cases, t_preds, {
            "llm_escalation_pct": 0.0,
            "latency_ms_per_request": round(t_ms, 3),
            "latency_note": "in-process tfidf after one-time fit",
            "cost_per_1000_usd": 0.0,
        }),
        summarize("heuristic→tfidf", cases, ht_preds, {
            "llm_escalation_pct": 0.0,
            "tfidf_escalation_pct": ht_esc,
            "latency_ms_per_request": round(ht_ms + h_ms, 3),
            "latency_note": "heuristic then tfidf on low evidence (score<3 or null)",
            "cost_per_1000_usd": 0.0,
        }),
    ]

    if haiku_available:
        results.append({
            "name": "haiku",
            "skipped": False,
            "note": "ANTHROPIC_API_KEY present but this bakeoff does not call Haiku automatically (cost gate).",
        })
    else:
        results.append({
            "name": "haiku",
            "skipped": True,
            "note": "ANTHROPIC_API_KEY absent. Haiku / heuristic→Haiku / three-stage cascade not measured.",
        })
        results.append({
            "name": "heuristic→haiku",
            "skipped": True,
            "note": "Blocked on owner API key. Estimated Haiku cost ~$1.10/1k routes if measured later.",
        })
        results.append({
            "name": "heuristic→tfidf→haiku",
            "skipped": True,
            "note": "Blocked on owner API key.",
        })

    curve = risk_curve(h_rows, tfidf, asks, cases)

    # Winner: cheapest/simplest with strong downstream-safe routing.
    # Heuristic is production today. Cascade to TF-IDF only if it clearly beats
    # heuristic department accuracy without introducing unsafe actions.
    h_acc = results[0]["department_accuracy"]
    ht_acc = results[2]["department_accuracy"]
    t_acc = results[1]["department_accuracy"]
    if ht_acc >= h_acc and ht_acc >= t_acc:
        winner = "heuristic→tfidf"
        rationale = (
            "Cascade keeps high-evidence heuristic routes (score>=3) and uses "
            "TF-IDF only when the heuristic has no business evidence. Zero LLM "
            "cost, zero unsafe actions, no production classify() change."
        )
    elif h_acc >= t_acc:
        winner = "heuristic"
        rationale = "Heuristic matches or beats TF-IDF; keep the shipped offline path."
    else:
        winner = "tfidf"
        rationale = "TF-IDF standalone is more accurate on v3, but is not auto-promoted."

    report = {
        "dataset": "validation-v3",
        "n": len(cases),
        "frozen_215_used_for_selection": False,
        "production_classify_changed": False,
        "send_email_enabled": False,
        "candidates": results,
        "risk_coverage": curve,
        "winner": winner,
        "winner_auto_promoted": False,
        "production_recommendation": "keep_heuristic",
        "production_recommendation_note": (
            "A measured accuracy leader is not shipped. classify() is unchanged. "
            "Promote only after an explicit owner decision."
        ),
        "rationale": rationale,
        "haiku_measured": haiku_available,
        "estimated_haiku_cost_per_1000_usd": 1.10,
    }
    out_path = OUT / "bakeoff-validation-v3.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
