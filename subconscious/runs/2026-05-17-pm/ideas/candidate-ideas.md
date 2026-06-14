# Candidate Ideas — 2026-05-17-pm (Run 22)

## Evidence Digest

Zero production commits for 12 days (since 72f8204 May 5). Run 21 winner (AI-to-Human Handoff GH issue) NOT implemented — no GH issue found in filesystem or nightly review. Pending = 7 (runs 4, 7, 8, 14, 19, 20, 21). check-widget-sync.sh MISSING. lead-qualifier-eval.yml MISSING. check_project_invariants.py NOT in pre-commit. SKILL.md Moratorium Escalation Protocol section missing. autopilot-issue-loop dormant (zero production commits). conversations.py has 3 endpoints — no handoff route. Nightly review May 17 confirms GH #169 open, no new action posted. Human is PRESENT in session (ran subconscious right now).

---

### Idea 1: Restart autopilot-issue-loop + Tag S-effort items as ai-ready
**Evidence:** Run 21 backlog explicitly mandates this if run 21 not implemented. 4 S-effort items (runs 7+8+14+19, ~50 min total). Loop dormant confirmed (zero production commits 12 days). If loop is configured and running, auto-implements S-effort items without manual effort.
**Action:** Verify .github/workflows/issue-to-pr.yml is configured and enabled. Add ai-ready label to GH issues for runs 7+8+14+19. Loop picks them up in next 15-min poll.
**Impact:** Could drop pending 7→3 (moratorium exits) without further human action beyond enabling the loop.
**Category:** workflow

---

### Idea 2: Wire check_project_invariants.py into pre-commit hook
**Evidence:** Run 8 winner (2026-04-25, 22 days pending). 037865f added scripts/check_project_invariants.py — stdlib-only, passes all 6 checks today (confirmed). Pre-commit has 9 checks; this becomes Check 10. Em-dash blocker cleared by 8f680e8. S-effort: 2-3 lines. No external dependencies. Human is present in this session — lowest-friction action to implement RIGHT NOW.
**Action:** Add `python3 scripts/check_project_invariants.py || exit 1` call to scripts/hooks/pre-commit after existing Check 9.
**Impact:** Blocks client_id/status/areas_of_interest violations at commit time. Drops pending 7→6. Moratorium progress.
**Category:** code_health

---

### Idea 3: Create AI-to-Human Handoff GH issue (escalate run 21's unfulfilled recommendation)
**Evidence:** Run 21 winner NOT implemented (no GH issue created in the ~12 hours since run 21). 32 days pending (run 4). CRITICAL gap all 7 industries in customer-gaps.md. conversations.py confirmed: no handoff endpoint. Infrastructure exists: Twilio wired, Resend wired, conversations table has session_id, status (verify). Run 21 backlog authorizes parallel track.
**Action:** Create GH issue "[P0] AI-to-Human Handoff v1 — Explicit Trigger" using implementation sketch from subconscious/runs/2026-05-17/winning-concept.md §Step 1.
**Impact:** Creates sprint anchor for highest-ROI feature. ~1.5-2 day implementation unlocks conversion uplift across all 7 industries.
**Category:** customer_value

---

### Idea 4: Widget 3-Copy Sync Guard (run 7 — 7th escalation)
**Evidence:** Run 7 winner (2026-04-24, 23 days pending). check-widget-sync.sh MISSING. Widget copies confirmed IN SYNC (May 15). CLAUDE.md Invariant #4 still says "2 copies" (should be 3). S-effort ~15 min. Was demoted to Bonus A in run 18 governance mandate.
**Action:** Create scripts/check-widget-sync.sh, wire into scripts/hooks/pre-push, fix CLAUDE.md Invariant #4.
**Impact:** Prevents future widget divergence. Drops pending 7→6.
**Category:** code_health
**Note:** Seventh consecutive moratorium escalation with no new evidence since run 17 confirmed sync. Excluded from debate.

---

### Idea 5: Zapier API key plan_status enforcement (GH #107, security)
**Evidence:** bug-patterns.md entry: backend/services/zapier_auth.py::_get_api_key_client resolves keys without plan_status check. GH #107 open 17+ days. ROI 2.5. HIGH security — cancelled tenants bypass tier gate.
**Action:** Add plan_status IN ('active','trialing') filter to _get_api_key_client + regression test seeding cancelled tenant with valid key asserting 403.
**Impact:** Closes tier-gate bypass. First real security fix since moratorium started.
**Category:** code_health / security
**Note:** Parking lot per moratorium protocol. Valid fix but requires code review beyond S-effort. Excluded from debate pending moratorium exit.
