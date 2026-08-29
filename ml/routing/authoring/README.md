# Routing validation-v3 (Milestone 6, workstream A)

Independent held-out **routing label** set. It is not a model-selection split.

## What this workstream added

| File | Role |
|---|---|
| `build_validation_v3.py` | Authors the cases. Each row is a `case(...)` call with the argument that labels it. |
| `../evals` path: `agent-service/evals/datasets/validation/validation-v3.json` | The generated split. |
| `leakage_v3.py` / `check_validation_v3_leakage.py` | Exact + Jaccard ≥ 0.8 + `template_id` / `pair_id` collision check. |
| `baselines/reference-asks-v3-leakage.json` | Read-only ask fingerprints of train / frozen / v1 / v2 so the check runs on main. **Not** the frozen eval file. |
| `../tests/test_validation_v3_leakage.py` | QA re-run of the leakage gate. |

## Hard constraints (honored)

- **Frozen 215 untouched.** `agent-service/evals/datasets/action-eval-v1.json` was not copied, edited, or extended. Frozen result JSON under `ml/routing/artifacts/` was not touched.
- **Production routing unchanged.** No edits to `classify()`, `classifyWithHaiku`, `classifyHeuristic`, `_classifier.ts`, or `setRoutingProvider` defaults.
- **No action-layer / email work.** No `send_email`, Gmail, `communication_actions`, executor, or policy changes.
- **No router winner.** This set is not for model selection yet. Do not report a champion from it.
- **Not a reuse of v1 or v2.** v2 was authored after frozen results and is not independent; v3 does not lift those asks.

## Labels

Eight ML-router departments only: `sales`, `marketing`, `customer_service`, `operations`, `invoicing`, `accounting`, `admin_records`, `people`. No `none`. Hard-negative pairs have both halves in this file.

`rationale` is human documentation. It is never a model feature. A router receives only `ask`.

## Leakage

```bash
python ml/routing/authoring/build_validation_v3.py
python ml/routing/authoring/check_validation_v3_leakage.py
python -m pytest ml/routing/tests/test_validation_v3_leakage.py -q
```

Drop rules: exact / normalised match, token Jaccard ≥ 0.8, `template_id` collision, `pair_id` collision. A colliding **template** is closed as a class. A pair is never split across this set and another split.

If live copies of train / frozen / v1 / v2 exist on the branch, the checker uses those bytes. Otherwise it uses the vendored fingerprints.

## What this is not

A measurement. A calibration set. A reason to change production routing. A replacement for the frozen 215.
