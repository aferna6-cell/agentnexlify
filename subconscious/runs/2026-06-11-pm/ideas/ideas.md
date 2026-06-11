# Ideas — Run 2026-06-11-pm (Run 56)

## Context
Run 55 winner (channels_instagram.py `from __future__` + 10 em-dashes) was PARTIALLY implemented:
- `from __future__ import annotations`: **FIXED** (confirmed PASS in invariants; likely cleared in b736ca2/b8fdcd2)
- Em-dash violations: **STILL PRESENT** — 10 violations, slightly different set (Sidebar.jsx:386 NEW from high-velocity sprint; ComposerAttachments.jsx:1 GONE)
- Check 10: **NOT WIRED** (55+ day pending)
- check-widget-sync.sh: **STILL MISSING** (50+ day pending)

New evidence since run 55 (this morning): 4 large feature PRs (#237-239) in ~6 hours — auth split, voice recovery (133 tests), 8-next-steps consolidation (35 files). High-velocity sprint is introducing new em-dash violations in real-time (Sidebar.jsx:386 is proof).

---

### Idea 1: Fix 10 em-dash violations (AUTONOMOUS-EXECUTABLE, carry-forward run 55)
**Evidence:** `check_project_invariants.py` exits 1 on 10 violations confirmed live. Set slightly updated vs run 55: Sidebar.jsx:386 is NEW (introduced by recent high-velocity PRs), ComposerAttachments.jsx:1 GONE (fixed as side-effect). AUTONOMOUS-EXECUTABLE path proven: 8db33df fixed 5 em-dashes autonomously on 2026-06-05. Nightly SKILL.md Item A inline patch is written and ready. Governance.json Item A = pending_autonomous + autonomous_executable: true. The high-velocity sprint (4 PRs today) is actively introducing new violations — Sidebar.jsx:386 came from fc662b4/b736ca2/b8fdcd2. Check 10's absence is an active regression risk, not latent.
**Action:** Replace 10 em-dash chars with hyphens across 8 JSX files: main.jsx:152, CookieConsent.jsx:5+31, MarketingUpsell.jsx:3, App.jsx:325, Sidebar.test.jsx:27+49, Sidebar.jsx:386, ReferralCard.jsx:24+45. Nightly 2:37 AM auto-wires Check 10 once exits 0.
**Impact:** Unblocks 55-day Check 10 gate; self-healing loop blocks future violations at commit time. Stops the accumulation pattern visible in today's PRs.
**Category:** code_health

---

### Idea 2: Add tenant isolation tests for os_graph_memory.py (AUTONOMOUS-EXECUTABLE)
**Evidence:** c8a0460 added os_graph_memory.py (397L) without cross-tenant isolation tests. c6805a5 had to fix 3rd _TENANT_COLUMN_OVERRIDES miss on Agent OS tables (os_graph_nodes + os_graph_edges). Agent OS knowledge graph serves customer conversations — cross-tenant data leak is catastrophic for a multi-tenant SaaS. Run 54 parking lot ROI 2.1. test_os_action_dispatch.py (run 53) was AUTONOMOUS-EXECUTABLE and nightly created it via c6805a5 — same class.
**Action:** Create `backend/tests/test_os_graph_isolation.py` — 2 mock-based tests: `accumulate_from_turn(client_id=A)` then `graph_kb_entries(client_id=B)` → empty; verify no cross-tenant node/edge leakage. Label AUTONOMOUS-EXECUTABLE.
**Impact:** Prevents silent cross-tenant data leak in Agent OS knowledge graph. Catches the recurring _TENANT_COLUMN_OVERRIDES miss pattern before production.
**Category:** code_health

---

### Idea 3: Invoke /god-class-splitter on Home.jsx (1171L)
**Evidence:** Home.jsx confirmed at 1171L — nearly 2x god-class threshold (600L). Run 9 rule: don't extend god classes, factor them first. High-velocity sprint (4 PRs today) is adding more features. bc8d0da added MessagingSettingsCards voice settings. auth.py was just split (b8fdcd2) into 3 new files — precedent for god-class splitting in active sprint. email_sequences.py (1255L, run 41) still unexecuted but pre-requisites cleared.
**Action:** Invoke /god-class-splitter on `frontend/src/pages/Home.jsx` — identify clean concerns (hero section, features, pricing/CTA blocks, signup forms), extract to focused components.
**Impact:** Reduces merge conflict surface in high-velocity sprint, enables focused UI testing, prevents further coupling accumulation.
**Category:** code_health

---

### Idea 4: AI-to-Human Handoff v1 implementation
**Evidence:** customer-gaps.md Critical, all 7 industries, 60+ days pending (run 4, 2026-04-16). bc8d0da (voice recovery, shipped today) established the detection→Agent OS dispatch pattern: detect condition → `os_action_dispatch.queue_action_for_run()` → deliver via `os_outbound_mirror`. os_outbound_mirror.py (PR #188, 152 tests) handles SMS/email delivery. Run 38 scoped to ~1 day (down from 3 days pre-Agent-OS). GoHighLevel ($97-497/mo) has this; it's a competitive gap.
**Action:** Add explicit trigger detection in widget_chat.py → write `handoff_requests` table row → `os_outbound_mirror.send_sms()` to tenant owner. Same dispatch pattern as voice recovery.
**Impact:** Closes #1 customer gap. Reduces churn vs GoHighLevel.
**Category:** customer_value

---

### Idea 5: Fix kb-autopopulate.sh (agent-browser CLI not installed)
**Evidence:** scripts/daily/kb-autopopulate.sh broken 35+ days (parking lot, run 53). Agent-browser CLI not available in deployment environment. KB stale 35+ days. Run 53 explicitly flagged this. Knowledge base is how widget AI serves tenants well.
**Action:** Replace agent-browser invocations in kb-autopopulate.sh with native WebFetch/curl, or add graceful fallback that logs and exits cleanly when CLI missing.
**Impact:** Restores twice-daily KB auto-population, keeps tenant AI knowledge current.
**Category:** operational
