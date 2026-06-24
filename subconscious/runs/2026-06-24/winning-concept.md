# Winning Concept — Run 65 (2026-06-24)

## Title
Add localStorage detection to post-edit hook (invariant #6 gap closure)

## One-line summary
Extend `scripts/claude-hooks/post-edit-check.sh` to warn when `localStorage` is used in React files — closing the last unautomated CLAUDE.md critical invariant.

## Evidence base
- 3eaf702 (2026-06-23): added 4 CLAUDE.md invariant checks to post-edit hook (lead_stage, service_interest, widget sync, model IDs)
- c8f1bde: fixed em-dash HTML entity false positives
- Invariant coverage after 3eaf702: #1 (client_id) ✅ · #2 (lead_stage) ✅ · #3 (areas_of_interest) ✅ · #4 (widget sync) ✅ · #5 (from __future__) ✅ pre-commit · **#6 (localStorage) ❌ uncovered**
- CLAUDE.md invariant #6: "No `localStorage` in React artifacts — storage isn't available in claude.ai artifact sandbox"
- localStorage violations are a documented past failure mode, not theoretical

## Governance note
**Moratorium exits this run.** Both override items verified implemented:
- GH #308 (webhook idempotency): `delete_key` confirmed in `backend/services/idempotency.py:96` + called in `stripe_webhooks.py:110` ✅
- GH #292/#293 (plan-name dicts): `plan_catalog.py` PREMIUM_PLANS correct; `api_key_auth.py` intentionally excludes chatbot from API keys (product decision, not bug); migration 158 landed ✅
- `pending_approvals` for the two override items → both IMPLEMENTED; moratorium condition no longer holds

This is the first free-cycling recommendation since the moratorium began.

## Implementation sketch

**File:** `scripts/claude-hooks/post-edit-check.sh`

Add after the existing invariant checks:

```bash
# Invariant #6: no localStorage in React files (claude.ai artifact sandbox)
if [[ "$EDITED_FILE" == frontend/*.jsx || "$EDITED_FILE" == frontend/*.js || \
      "$EDITED_FILE" == frontend/**/*.jsx || "$EDITED_FILE" == frontend/**/*.js ]]; then
  if grep -qn "localStorage" "$EDITED_FILE" 2>/dev/null; then
    echo "WARN [invariant-6]: localStorage found in React file '$EDITED_FILE'" >&2
    echo "  → localStorage unavailable in claude.ai artifact sandbox (CLAUDE.md #6)" >&2
  fi
fi
```

- Warn-only (consistent with hook style — no blocking on warn)
- Scoped to `frontend/**/*.{jsx,js}` only (widget has separate byte-identical check)
- No new dependencies

## Acceptance criteria
1. Adding `localStorage.getItem(...)` to any `frontend/**/*.jsx` file triggers the WARN message on post-edit
2. Files in `backend/`, `widget/`, `migrations/` are NOT flagged
3. Existing test in `backend/tests/` (if any) for the hook still passes
4. No false positives on variable names like `localStorageKey` (use word-boundary or exact `localStorage.` match)

**Refinement**: use `localStorage\.` (with dot) to match only API calls, not variable names containing "localStorage":

```bash
grep -qn "localStorage\." "$EDITED_FILE"
```

## Risk
LOW. Warn-only. No blocking behavior. Reversible by removing the block.

## Effort
~8-10 lines in `scripts/claude-hooks/post-edit-check.sh`. 10-minute implementation.

## Category
Code quality / automation / invariant protection

---

## RUN 66 MANDATE
Moratorium exited. Next recommended direction: **Write AI-to-human handoff PRD** (`specs/ai-human-handoff_spec.md`). Brain backlog exhausted; this is the highest-priority product gap across all 13 verticals. Use `/write-prd` + `/grill-me` in an interactive session. Run 66 winner should be this spec unless a more urgent regression surfaces.
