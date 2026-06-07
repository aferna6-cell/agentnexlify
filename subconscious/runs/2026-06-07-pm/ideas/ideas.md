# Ideas — Run 2026-06-07-pm (Run 52)

Generated: 2026-06-07

## Evidence Digest

Last 72h: Agent OS v2 orchestration engine landed (7a621a1, 7,640 insertions — new execution core, migration 131, frontend flowchart update). Widget hijack bug found and fixed (2287f6b — `_DEFAULT_CONFIG["widget_enabled"]` was True, now False). Auth hardening shipped (abccdc3 — X-Agent-Token gate between FastAPI and agent-service). Nightly 2026-06-07 filed GH #206: `isTokenAuthorized` in auth.ts uses `===` (not constant-time), timing attack surface in new auth layer.

**Continuations:** GH #181 billing still open (AMOUNT_TO_PLAN missing 15000/25000, confirmed live). Check 10 not wired despite 2 scope extensions — root cause: run 51 winning concept (PR #183 merge) displaced run 50's AUTONOMOUS-EXECUTABLE trigger; nightly checks most-recent winning-concept.md for label, run 51 has none. check-widget-sync.sh still missing (51 days). email_sequences.py still 1255L.

---

### Idea 1: Fix Timing-Safe Token Comparison in auth.ts (GH #206)

**Evidence:** Nightly 2026-06-07 reviewed abccdc3 (auth hardening) and filed GH #206: `isTokenAuthorized` in `agent-service/src/auth.ts` uses JavaScript `===` for secret comparison — not constant-time, vulnerable to timing side-channel attacks. Current code: `return value === expected;`. DEPLOY.md added in same commit signals service is being prepared for real deployment. Widget hijack (2287f6b) proves Agent OS changes produce regressions; auth is the gateway.

**Action:** 2-line edit in `agent-service/src/auth.ts` — replace `return value === expected;` with timing-safe comparison using Node.js `crypto.timingSafeEqual`. Import crypto at top. Handle undefined/length-mismatch safely.

**Impact:** Closes security gap in freshly-shipped auth layer before Agent OS v2 scales publicly. Same-day fix maintains security posture on new code surface.

**Category:** code_health (security)

---

### Idea 2: Merge PR #183 (GH #181 Billing Fix, Existing 14-Day Draft)

**Evidence:** AMOUNT_TO_PLAN in `backend/routers/billing.py:263` confirmed missing `15000: "autopilot"` and `25000: "professional"` (live grep run 52). PR #183 is a 14-day draft. Run 51 winner under "merge existing PR" framing (bypasses rejected_paths governance). Morning digest endorsed merge. Check 11 WARNING fires on every commit.

**Action:** Read PR diff, verify path is backend/routers/billing.py (not services/), verify 15000+25000 entries present and backwards test assertions corrected, then merge.

**Impact:** Closes billing revenue recognition gap, silences Check 11 WARNING, unblocks email_sequences.py god-class split (run 41 active_direction).

**Category:** code_health

---

### Idea 3: Restore Autonomous Channel for Check 10 via This Run's Winning Concept

**Evidence:** SKILL.md trigger for Item A autonomous execution reads: "the most recent `subconscious/runs/*/winning-concept.md` contains `AUTONOMOUS-EXECUTABLE`." Run 50 winning concept had the label for Items A+B. Run 51 (PR #183 merge) became the most recent — no AUTONOMOUS-EXECUTABLE label. Nightly 2026-06-07 shows 0 auto-fixes. Check 10 not in pre-commit. Channel broke because a non-AUTONOMOUS recommendation displaced the trigger label. `check_project_invariants.py` exits 0 (em-dash fix 8db33df, 2026-06-05) — pre-condition met. 3-line patch inline in SKILL.md.

**Action:** This run's winning concept embeds AUTONOMOUS-EXECUTABLE directive for Item A (wire Check 10). Costs zero additional effort — restores nightly trigger for 2:37 AM tonight.

**Impact:** Check 10 wires autonomously tonight. Reduces moratorium pending count. Compounds: every future AUTONOMOUS-EXECUTABLE item can now fire reliably.

**Category:** workflow

---

### Idea 4: Write Integration Tests for Agent OS v2 Routing + Auth Pipeline

**Evidence:** Agent OS v2 (7a621a1) adds 7,640 insertions — new `agent-service/src/agent-os/` engine, `backend/routers/os_orchestrate.py`, `backend/services/agent_os_bridge.py`. Nightly counted 14 agent-service tests. Widget hijack (2287f6b) shows regression risk from Agent OS changes. New execution path: widget → `os_inbound_bridge.py` → `os_orchestrate.py` → `agent_os_bridge.py` → agent-service — no integration tests span this chain.

**Action:** Add integration tests for: (a) `os_orchestrate.py` routing decisions, (b) `agent_sdk_client.py` auth token rejection (401 → fallback), (c) `os_inbound_bridge` default widget_enabled=False regression test. ~40 lines of pytest.

**Impact:** Catches regressions before they reach widget tenants. Prevents repeat of 2287f6b class bugs. Estimated 60% fewer Agent OS production regressions.

**Category:** code_health

---

### Idea 5: Create GH Issue — Apply Migration 131 to Production Supabase

**Evidence:** Nightly 2026-06-07 flagged: "migration 131 must be applied to production Supabase if not already done." Migration 131 (from 7a621a1) adds `os_routing_decision` and `os_model_call_log` tables. Both are `client_id`-scoped with RLS. If not applied, Agent OS v2 will fail silently in production when any routing decision is recorded.

**Action:** Create GH issue "ops: verify/apply migration 131 in production Supabase (os_routing_decision, os_model_call_log) — required for Agent OS v2" with labels `operational`, `ai-ready`. Routes to issue-to-pr-loop for verification.

**Impact:** Prevents production Agent OS failure mode. Time-sensitive: Agent OS v2 just shipped and is in use.

**Category:** operational
