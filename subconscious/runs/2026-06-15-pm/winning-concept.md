# Winning Concept — 2026-06-15-pm

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Update Check 11 in `scripts/hooks/pre-commit` to reflect the two-plan repricing ({1999:chatbot,
9999:agent_os}), and wire `check_project_invariants.py` as Check 10 in the same commit.

## Why This, Why Now
PR #288 (9bed342) repriced AMOUNT_TO_PLAN from {9900/15000/25000/89900} to {1999/9999}. Check 11
(added by nightly 061582c) still checks the old amounts — it fires WARNING on every commit since
the repricing with "AMOUNT_TO_PLAN missing entries: 9900 15000 25000 89900." This is noise that
trains developers to ignore pre-commit warnings, undermining the entire guard system. Simultaneously,
`check_project_invariants.py` now exits 0 for the first time in ~45 days (PR #257 / 3234597 cleared
all three blockers: widget sync, em-dash, from __future__). Check 10 has been pending for 60+ days
with no remaining blocker. Both fixes touch the same file (scripts/hooks/pre-commit) and are
AUTONOMOUS-EXECUTABLE via the nightly review channel, keeping them off the moratorium pending_approval
count.

## Implementation Sketch

**Step 1 — Update Check 11 (lines ~248-269 in scripts/hooks/pre-commit):**
```bash
# Find:
    REQUIRED_AMOUNTS=(9900 15000 25000 89900)
# Replace with:
    REQUIRED_AMOUNTS=(1999 9999)
```
```bash
# Find:
    echo "  Expected: 9900 (growth), 15000 (autopilot), 25000 (professional), 89900 (enterprise)"
    echo "  Fix: backend/routers/billing.py — see GH #181"
# Replace with:
    echo "  Expected: 1999 (chatbot), 9999 (agent_os)"
    echo "  Fix: update AMOUNT_TO_PLAN in backend/routers/billing.py"
```

**Step 2 — Add Check 10 block before Check 11 (insert at ~line 248, before "# Check 11:"):**
```bash
# Check 10: project invariants
echo -n "Check 10: Project invariants... "
INV_OUT=$(python3 scripts/check_project_invariants.py 2>&1)
INV_EXIT=$?
if [ $INV_EXIT -eq 0 ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "$INV_OUT"
    ERRORS=$((ERRORS + 1))
fi
```

**Step 3 — Verify:**
```bash
bash scripts/hooks/pre-commit   # should show Check 10 OK, Check 11 OK
```

**Step 4 — Commit:**
```bash
git add scripts/hooks/pre-commit
git commit -m "fix(pre-commit): wire Check 10 (invariants) + update Check 11 for two-plan repricing"
```

## What This Replaces
- Run 22 / run 42 / run 43 active directions (all about wiring Check 10, now superseded by this)
- Check 11 false-positive warning loop (active since PR #288, 2026-06-13)
- Run 57 backlog question "Did nightly implement Check 13 (run 56)?" — Check 2 already covers
  from __future__ in routers; this run confirms Check 13 was subsumed

## Confidence
HIGH — evidence is concrete (live code inspection + direct script execution), implementation is
low-risk bash edits to a well-tested file, execution path (nightly autonomous channel) has
delivered 16+ successful implementations.
