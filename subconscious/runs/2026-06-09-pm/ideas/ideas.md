# Ideas — 2026-06-09-pm (Run 53)

## Evidence Digest

Run 52 winner (Check 12 — agent-service timing-safe guard) IMPLEMENTED by nightly 2026-06-09 (ca3ce68). Agent OS Phase 4 shipped (369b3c8): 24 files, 2043 lines deleted, 854 added. New `os_action_dispatch.py` (85L) confirmed ZERO test coverage (`NO_TEST_FILE`). It guards idempotency for all approved agent actions from both human and auto-approval paths — the busiest correctness surface in Agent OS. PRs #211+#212 adding features on top of this unverified layer. `kb-autopopulate` broken since 2026-05-05 (35 days): `knowledge-base/log.md` last entry "network sandbox denies outbound + agent-browser not installed." Migration 133 RLS clean (deny_public on both tables — no issue). 5 new product roadmap issues (#213–217) filed 2026-06-08. PR #183 (billing) unmerged at 16 days; PR #200 (widget guard enabler) unmerged at 6 days; moratorium day 39+.

---

### Idea 1: Write test coverage for os_action_dispatch.py (AUTONOMOUS-EXECUTABLE)
**Evidence:** 369b3c8 Phase 4 added `os_action_dispatch.py` (85L) — zero dedicated test file confirmed (`NO_TEST_FILE`). Guards idempotency for ALL approved agent actions. Two callers (os_deliverables.py + agent_os_bridge.py). PRs #211+#212 are currently in review adding more features on top.
**Action:** Create `backend/tests/test_os_action_dispatch.py` — 5 test cases covering `queue_action_for_run()`: (1) no action_type returns None, (2) unknown action_type returns None, (3) idempotency on existing succeeded row, (4) background task queued when BackgroundTasks provided, (5) inline run when background=None. All mockable with unittest.mock.
**Impact:** Catches regressions in the idempotency guard before they reach production; provides safety net as Agent OS scales to 30+ agents. Autonomous channel confirmed (nightly creates test files in backend/tests/ scope).
**Category:** code_health

---

### Idea 2: Fix kb-autopopulate agent-browser dependency (35-day stale KB)
**Evidence:** `knowledge-base/log.md` last entry 2026-05-05 (35 days ago). Two consecutive blocking messages: "network sandbox denies outbound + agent-browser not installed" (2026-05-01) and "cron-gap | Supabase MCP unauthorized" (2026-05-05). CLAUDE.md: kb-autopopulate runs 6am+6pm daily. `fill-instructions-before-guessing.md` Rule 1: "A hook/command references a tool that isn't installed. Fix the hook before routing work around it." This is the exact documented pattern.
**Action:** Read `scripts/daily/kb-autopopulate.sh`; identify agent-browser CLI call; replace with native WebFetch/WebSearch fallback (or skip gracefully when agent-browser absent). Fix SUPABASE_ACCESS_TOKEN wiring. Re-run to verify.
**Impact:** Restores 35 days of missing competitive intel (GoHighLevel, Drillbit, Birdeye updates). KB is the "moat" per CLAUDE.md; stale = moat degrades.
**Category:** operational

---

### Idea 3: Write spec for WordPress plugin one-click embed (GH #214)
**Evidence:** GH #214 filed 2026-06-08: "WordPress plugin for one-click widget install (no-code embed)." 43% of websites run WordPress. GoHighLevel has WordPress integration. Current widget requires manual HTML snippet embed — activation friction gap.
**Action:** Write `specs/wordpress-plugin_spec.md` — plugin settings page (API key + business_id), `[agentnexlify-widget]` shortcode, admin health check banner.
**Impact:** Unlocks SMB distribution via largest CMS market; reduces widget activation drop-off.
**Category:** customer_value

---

### Idea 4: Integration health probe backend endpoint (GH #215)
**Evidence:** GH #215 filed 2026-06-08: "Integration health dashboard + is my widget live? probe." No current visibility into whether tenants have the widget working after embed. Early churn tied to silent widget configuration failures.
**Action:** Add `GET /api/widget/{client_id}/health` → returns `{widget_enabled, last_message_at, widget_script_version, status: "live"|"silent"|"disabled"}`. Wire status indicator into onboarding wizard.
**Impact:** Surfaces silent widget failures before customer churn; reduces support tickets.
**Category:** customer_value

---

### Idea 5: Activity log emission for all 4 automations (GH #213)
**Evidence:** GH #213 filed 2026-06-08: "Emit activity_log rows for all 4 automations (dashboard parity)." Automation dashboard shows no activity history. Customers cannot see what the AI is doing — reduces trust + increases support load.
**Action:** Audit which automations (booking, email_sequences, sms, lead_nurture) currently write `activity_log` entries; add missing `INSERT` calls with standardized `action_type` + `summary` fields.
**Impact:** Closes customer visibility gap; direct trust signal for tenants evaluating ROI.
**Category:** customer_value
