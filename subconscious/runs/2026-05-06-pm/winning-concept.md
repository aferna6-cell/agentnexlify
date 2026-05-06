# Winning Concept — 2026-05-06-pm (Run 15)

## Recommendation
Wire `check_project_invariants.py` into the pre-commit hook as Check 10, closing run 8 (11 days pending), dropping the pending queue from 4→3, and permanently guarding against the #1 production bug class in this codebase.

## Why This, Why Now

**Moratorium re-triggered.** Run 14 lifted the moratorium on 2026-05-05 but immediately added a new pending item (eval harness CI), bringing the queue back to 4 — above the threshold of 3. Moratorium mode mandates: close queue items, don't add new ones. Run 8 (check_project_invariants pre-commit) is the S-effort closer that gets us back to 3 pending.

**Zero-risk implementation.** `python3 scripts/check_project_invariants.py` was confirmed to PASS all 6 checks today: no `__future__` annotations, no retired schema fields, no retired plan names, widget assets byte-identical, no em-dashes in source, SDK calls behind runtime wrapper. The guard is ready. The only missing piece is the 10-line bash block wiring it to pre-commit.

**Was run 14's bonus step.** It was already specified in run 14's winning-concept.md — but bonus steps get buried behind the primary winner. Making it the primary winner gives it full attention. S-effort = 5 minutes. Implementation spec is already written.

**Guards the #1 production bug class.** client_id vs. tenant_id, status vs. lead_stage, areas_of_interest vs. service_interest — naming violations have caused 3+ production bugs (cited in CLAUDE.md). This is the permanent automated guard.

## Implementation Sketch

**Step 1:** Open `scripts/hooks/pre-commit`. Locate the Check 9 block (~line 225). Insert after it:

```bash
# Check 10: Project invariants (client_id, status, areas_of_interest, widget sync, em-dash, SDK wrapper)
echo -n "Check 10: Project invariants... "
if python3 scripts/check_project_invariants.py > /dev/null 2>&1; then
  echo -e "${GREEN}OK${NC}"
else
  echo -e "${RED}BLOCKED${NC}"
  python3 scripts/check_project_invariants.py
  ERRORS=$((ERRORS + 1))
fi
```

**Step 2:** Test the hook locally:
```bash
cd /home/user/agentnexlify
git commit --allow-empty -m "test: verify Check 10 fires"
# Should see: Check 10: Project invariants... OK
```

**Step 3:** Verify Check 10 appears in hook output and passes green.

**Step 4:** Commit with message:
```
chore(pre-commit): add Check 10 — project invariants guard, closes run 8
```

**Step 5:** Update `subconscious/state/governance.json` — change run 8 active_direction status from `pending_approval` → `implemented`. Pending drops 4→3.

## Security Escalation (Separate from Approval Queue)

**Zapier plan_status auth bypass (Issue #107)** is an urgent security bug — NOT a subconscious approval item. Steps to handle separately:

1. Grep codebase for `_get_api_key_client` to confirm actual file location (bug-patterns.md path `backend/services/zapier_auth.py` not found — path may be stale)
2. Once located: add `.in_("plan_status", ["active", "trialing"])` filter to the API key lookup query
3. Add regression test: seed cancelled tenant + valid API key, assert 402/403
4. Close Issue #107

This should go through the normal bug fix channel (backend-dev agent), not through the subconscious approval queue.

## Moratorium Warning

**Run 4 (AI-to-Human Handoff v1)** is now 20+ days pending — exceeds max_pending_age_days of 14. If it reaches 30 days unimplemented at run 16, trigger a dedicated implementation session recommendation rather than continuing to note it as "aging." The moratorium governance config mandates escalation at this stage.

## What This Replaces
Previous active direction was "Wire golden eval harness to CI" (run 14). Run 14's winner is still pending — this recommendation does not replace it. Run 8 and run 14 can both be implemented in the same session since they are independent tasks.

## Pending Queue After Implementation
- Before: 4 pending (runs 4, 7, 8, 14)
- After run 8 close: 3 pending (runs 4, 7, 14)
- Moratorium threshold: 3
- Status: exactly at threshold — any new addition re-triggers

## Next Run Candidates (Run 16)
1. **Widget 3-Copy Sync Guard (run 7)** — S-effort, 12+ days pending. If queue drops to 3, this closes it to 2.
2. **Wire eval harness to CI (run 14)** — S-effort, still unimplemented 2+ days after recommendation.
3. **AI-to-Human Handoff v1 (run 4)** — if still pending at 30+ days, mandate a dedicated implementation recommendation.
4. **Fix N+1 in leads.py:714,866** — architecture audit finding, M-effort, promote if sprint starts.

## Confidence
**HIGH** — Evidence: (1) check_project_invariants.py confirmed PASS all 6 checks on 2026-05-06; (2) moratorium governance requires queue closure; (3) full 10-line implementation spec from run 14 bonus step; (4) pre-commit slot is clean (Check 9 is last); (5) no blocking dependencies; (6) closes an 11-day-old pending item.
