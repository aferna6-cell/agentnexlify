# RAG eval splits

| File | Role |
|------|------|
| `rag-eval-validation-v1.json` | Model / threshold / abstention selection. Editable until freeze. |
| `rag-eval-holdout-v1.json` | **Independent** frozen holdout. Authored separately. Not used for selection. |
| `rag-eval-v1.json` | Public frozen alias of the independent holdout (`independent: true`). |

Do **not** treat a locked copy of the validation set as an independent benchmark.

`rationale` is never model input. `accountId` is the only tenant scope.

Leakage gate: `python3 ml/rag/authoring/check_rag_holdout_leakage.py`
