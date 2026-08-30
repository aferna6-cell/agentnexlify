# Action evaluation datasets

## `action-eval-v1.json` — frozen 215

Production behavioral benchmark. **Frozen. Do not edit labels.**

Copied from the #693 research branch as-is. Used only after router
selection, and by the safety gate. The automated harness never sends mail.

## `validation/validation-v3.json` — independent selection set

208 department-labelled cases. Leakage-checked against train-v1, frozen
215, validation-v1, and validation-v2. Used for Milestone 6 router /
cascade selection. Not a replacement for the frozen 215.
