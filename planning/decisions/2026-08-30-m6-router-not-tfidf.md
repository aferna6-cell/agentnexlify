# Decision: Do not promote TF-IDF router to production (Milestone 6)

**Date:** 2026-08-30  
**Status:** Accepted (pending merge of `cursor/milestone6-completion-b6dd`)  
**War room visibility:** This record supersedes the hybrid recommendation in `docs/ml-router-benchmark.md`.

## Context

validation-v3 (208 cases, leakage-checked) showed TF-IDF routing accuracy 51.9% vs heuristic 36.5%. The earlier research write-up (`docs/ml-router-benchmark.md`) recommended a heuristic→TF-IDF hybrid cascade.

## Decision

**Keep production routing as heuristic (+ semantic intent/subject scoring) with Haiku when `ANTHROPIC_API_KEY` is present.** Do not deploy TF-IDF or cascades behind a flag until downstream action-eval shows improvement, not routing-only accuracy.

## Rationale

1. Frozen 215-case action benchmark: **0 unsafe actions** with shipped path; no evidence TF-IDF improves behavior/tool accuracy.
2. Heuristic→TF-IDF cascade (architecture C) scored **48.1%** on validation-v3 — worse than TF-IDF alone (51.9%).
3. Operational cost: artifact versioning, calibration drift, CI reproducibility — not justified without downstream gain.
4. Haiku already available in production when keyed (~$1.11/1k); offline heuristic remains CI default.

## Dissent / revisit triggers

- Re-evaluate if downstream action eval (frozen 215) improves ≥5 pp on behavior or tool accuracy with a substituted router file.
- Re-evaluate if Haiku cost/latency becomes unacceptable at scale and cascade F (heuristic→TF-IDF→Haiku) shows measured downstream gain.

## Evidence artifacts

- `ml/routing/artifacts/milestone6-validation-v3.json`
- `agent-service/evals/results/action-eval-action-eval-v1-2026-08-30.json`
- `docs/milestone-6-router-decision.md`
