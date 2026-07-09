# Winning Concept — Run 2026-07-01-pm (Run 76)

## Winner: Zapier plan_status Enforcement — De-scoped (Run 76 Mandate)

**Category:** code_health / security  
**Effort:** XS (de-scoped)  
**Type:** AUTONOMOUS-EXECUTABLE  
**Moratorium override:** YES (security + revenue access control gap)  
**Mandate:** Run 75 — fires unconditionally this run

---

## Context

Run 75 winner was Zapier plan_status enforcement with full test file. Implementation deadline: before run 76 check.

Run 76 check result: **NOT IMPLEMENTED**.

Per run 75 winning-concept.md mandate:
> "If Zapier fix not implemented after run 76: de-scope to API key resolver check only (skip test file). One-line guard is sufficient to close the access control gap."

---

## Critical Finding (New, Run 76)

`backend/services/zapier_auth.py` does **not exist** at the expected path.

Before implementing, locate the correct file:
```bash
grep -r "_get_api_key_client" /home/user/agentnexlify/backend/ --include="*.py" -l
```

Possible locations:
- `backend/routers/zapier.py`
- `backend/services/api_keys.py`
- `backend/services/integrations/zapier.py`

If function not found: the Zapier auth flow may use a different function name. Fallback search:
```bash
grep -r "zapier" /home/user/agentnexlify/backend/ --include="*.py" -l | head -10
```

---

## Implementation (De-scoped — No Test File)

**Step 1:** Locate the file (grep above).

**Step 2:** Find the point where the API key resolves to `client_id`. After that resolution, add:

```python
# Enforce plan_status — prevent cancelled/past-due tenants from using Zapier
from backend.dependencies import get_supabase_client  # adjust import path

supabase = get_supabase_client()
tenant_result = (
    supabase.table("tenants")
    .select("plan_status")
    .eq("id", client_id)
    .single()
    .execute()
)
if tenant_result.data["plan_status"] not in ("active", "trialing"):
    raise HTTPException(
        status_code=402,
        detail="Active subscription required for Zapier integration"
    )
```

**Step 3:** Verify no existing import of `HTTPException` would conflict.

**Step 4:** Run `python -c "from backend.services.<found_module> import _get_api_key_client"` to confirm no import errors.

**No test file.** Test debt is accepted per de-scope mandate.

---

## Success Criteria

- `_get_api_key_client` (or equivalent Zapier auth function) returns 402 when tenant `plan_status` is `cancelled` or `past_due`
- Active / trialing tenants pass through unchanged
- No existing tests broken (none exist for this function)
- Import check passes

---

## Run 77 Mandate

If this fix is NOT implemented by run 77 check:
- Escalate to `severity: CRITICAL` in governance.json
- File GH issue directly (do not just recommend)
- Mark as `human_blocked` with note: "62+ days open, 3 recommendation cycles, zero implementation — requires human intervention"
- Add `ai_human_handoff` to `frozen_ideas` in governance.json (7 consecutive kills = not subconscious cycle material)

---

## Parking Lot (Run 76)

Items surviving debate but not selected:

1. **Plan-name guard pre-commit hook** — XS effort, AUTONOMOUS-EXECUTABLE. No urgency. Implement opportunistically when touching scripts/hooks/.
2. **email_sequences.py god-class split** — M effort. Implement when: (a) moratorium lifts, (b) new code is about to be added to the file.
