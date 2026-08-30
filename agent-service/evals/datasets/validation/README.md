# Validation splits

## validation-v3 (2026-08-29)

`validation-v3.json` — 208 department-labelled cases. **Independent held-out
routing labels, frozen for Milestone 6 model selection on 2026-08-30.**

- Same 8 ML-router departments. No `none`.
- Hard-negative pairs are complete inside this file (`v3_pair_*`).
- Leakage-checked against train-v1, frozen action-eval-v1 (215),
  validation-v1, and validation-v2. Drop rules: exact / normalised match,
  Jaccard ≥ 0.8, `template_id` collision, `pair_id` collision.
- Authored by `ml/routing/authoring/build_validation_v3.py`.
- QA: `python ml/routing/authoring/check_validation_v3_leakage.py`

**Frozen `action-eval-v1.json` (215) was not modified.** Production routing
(`classify` / Haiku / heuristic) remains unchanged until the bakeoff decision is
documented separately. Do not edit validation-v3 asks or labels after this
freeze.

v1 and v2, if present on another branch, stay as they are. This file does not
reuse them.
