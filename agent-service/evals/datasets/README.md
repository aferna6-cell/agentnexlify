# Action evaluation datasets

| File | Role |
|---|---|
| `action-eval-v1.json` | **Frozen 215.** Labels are immutable. Blob SHA pinned in `FROZEN.json`. |
| `validation/validation-v3.json` | Independent routing-only split (n=208). Used for model/cascade **selection**. Not a replacement for the frozen 215. |
| `FROZEN.json` | Pin of the frozen blob SHA / byte count / case count. |

`rationale` is human documentation. It is never a model feature.

Do not re-serialize `action-eval-v1.json`. Copy with `git show` / `git hash-object` only.

validation-v1 and validation-v2 stay on research branches. They are not imported here.
