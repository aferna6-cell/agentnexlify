# RAG eval splits

| File | Role |
|------|------|
| `rag-eval-validation-v1.json` | Model/threshold selection. Editable until freeze. |
| `rag-eval-v1.json` | Frozen snapshot after selection (same labels, `frozen: true`). |

`rationale` is never model input. `accountId` is the only tenant scope.
