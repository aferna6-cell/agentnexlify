# Improvement Backlog — Run 2026-06-11-pm (Run 56)

## Winner (AUTONOMOUS-EXECUTABLE)

### Fix 10 em-dash violations → Check 10 auto-wires tonight
- **Status:** pending_autonomous
- **Effort:** S (~2 min)
- **Execution:** Nightly 2:37 AM. SKILL.md Item A inline patch.
- **Unblocks:** Check 10 — 55-day pending pre-commit wire.
- **Files:** main.jsx:152, CookieConsent.jsx:5+31, MarketingUpsell.jsx:3, App.jsx:325, Sidebar.test.jsx:27+49, Sidebar.jsx:386, ReferralCard.jsx:24+45

---

## Parking Lot

### Add tenant isolation tests for os_graph_memory.py (AUTONOMOUS-EXECUTABLE)
- **Run:** 56 (Idea 2, SURVIVES WEAKENED)
- **ROI:** 2.1
- **Effort:** S
- **Evidence:** c8a0460 added os_graph_memory.py (397L) without cross-tenant isolation tests. 3rd _TENANT_COLUMN_OVERRIDES miss (os_graph_nodes + os_graph_edges) caught by c6805a5 — pattern is reliable.
- **Action:** Create `backend/tests/test_os_graph_isolation.py` — 2 mock-based tests: `accumulate_from_turn(client_id=A)` then `graph_kb_entries(client_id=B)` → empty; verify no cross-tenant node/edge leakage.
- **Deferred because:** Valid and AUTONOMOUS-EXECUTABLE, but lower leverage than winner. Does not unblock any existing gate.
- **Next run:** Promote if Check 10 wires tonight (moratorium pressure steady).

### AI-to-Human Handoff v1 implementation
- **Run:** 56 (Idea 4, WEAKENED)
- **ROI:** Highest customer value (60+ days, all 7 industries, #1 customer gap)
- **Effort:** M (~1 day)
- **Evidence:** bc8d0da (voice recovery) established detect→dispatch→outbound pattern. GoHighLevel has this at $97-497/mo.
- **Action:** trigger detection in widget_chat.py → `handoff_requests` table → `os_outbound_mirror.send_sms()` to tenant owner.
- **Deferred because:** M-effort during moratorium. Moratorium constraint is binding. No defense survives.
- **Promote when:** Check 10 wires (moratorium can exit) + billing.py PR #183 merged.

### Home.jsx god-class split (1171L)
- **Run:** 56 (Idea 3, not debated)
- **Effort:** M
- **Evidence:** Home.jsx at 1171L, nearly 2x god-class threshold (600L). High-velocity sprint adding features.
- **Action:** `/god-class-splitter` on `frontend/src/pages/Home.jsx`
- **Deferred because:** M-effort, moratorium active. email_sequences.py (1255L, run 41) has moratorium seniority.
- **Sequencing rule:** invoke /god-class-splitter on email_sequences.py FIRST, then Home.jsx.

### Fix kb-autopopulate.sh (agent-browser CLI not installed)
- **Run:** 56 (Idea 5, not debated)
- **ROI:** 1.8
- **Effort:** S
- **Evidence:** Broken 35+ days. KB stale.
- **Action:** Replace agent-browser invocations with native WebFetch/curl or graceful fallback.
- **Deferred because:** Operational, low urgency vs code health + customer value items.

---

## Standing Actions (human-required, not subconscious winners)

### Merge PR #183 — billing.py AMOUNT_TO_PLAN fix
- GH #181 open. 15000→autopilot + 25000→professional entries missing. ~10 min review + merge.
- Critical for correct billing on autopilot + professional plan signups.

### email_sequences.py god-class split (1255L, run 41)
- `/god-class-splitter` on `backend/services/email_sequences.py`. M-effort.
- Pre-requisites: PR #183 merged + moratorium exits.

---

## Moratorium Exit Path
1. **Tonight (autonomous):** Fix 10 em-dashes → Check 10 wires
2. **Human (~10 min):** Merge PR #183
3. **Result:** pending_approval count drops; moratorium can exit
4. **Post-moratorium:** AI-to-Human Handoff v1, email_sequences.py split, Home.jsx split

---

## Key metrics this run
- `check_project_invariants.py`: exits 1 (10 violations)
- `from __future__ import annotations` in channels_instagram.py: FIXED
- Check 10 in pre-commit: NOT WIRED (55+ days)
- check-widget-sync.sh: MISSING (50+ days)
- Moratorium: ACTIVE (day 41+)
- High-velocity sprint: 4 large PRs today (auth split, voice recovery, 8-next-steps, admin sidebar)
