# Ideas — Run 80 (2026-07-06)

## Evidence Summary

Brain connectors failing 6 consecutive days (Jul 1–6). GitHub 403 + Supabase token missing. All autonomous agents operating on stale brain data — last successful sync was 2026-06-22. Run 79 winner (fix credentials) pending human action, unfixed. Run 80 mandate fires: add Step 9C to nightly SKILL.md. check_project_invariants.py still exits 1 (widget drift — topic retired). SMS Compliance Dashboard (12/12 council score) still not shipped: backend router missing, frontend page missing. Moratorium active (max_pending_approvals: 2). No production feature commits in 4+ days.

---

### Idea 1: Add Step 9C to nightly SKILL.md — Brain Connector Health Check
**Evidence:** brain/INGESTION-LOG.md shows GitHub 403 + SUPABASE_ACCESS_TOKEN missing for 6 consecutive days (Jul 1–6). Run 79 mandate fires explicitly: "If brain connectors still failing after next run: add Step 9C to nightly SKILL.md." The failure went undetected 4 days before subconscious caught it. GH #394 filed for the human credential fix. Step 9C closes the detection blind spot for future expirations.
**Action:** Add Step 9C block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9B: read brain/INGESTION-LOG.md last 20 lines, count consecutive failures, if 3+ and no open GH issue labeled `brain-connector-failure` → create GH issue with human-action-required + critical labels.
**Impact:** Future credential expirations detected and escalated within 24h instead of 4+ days. AUTONOMOUS-EXECUTABLE (same class as Step 9B added by run 79).
**Category:** operational

---

### Idea 2: SMS Compliance Dashboard — File GH Issue for Issue-to-PR Loop
**Evidence:** SMS Compliance Dashboard has 12/12 council score (run 70). backend/routers/sms_compliance.py = MISSING. frontend/src/pages/SmsCompliance.jsx = MISSING. Run 74 delivered paste-ready code blocks. Run 75 mandate: "de-scope to backend endpoint only." Run 76 mandate: "file GH issue for issue-to-pr-loop." Both mandates fired. 6+ days with no implementation.
**Action:** Create GH issue with `ai-ready` label + full implementation sketch (file list: sms_compliance.py router, main.py registration, SmsCompliance.jsx, App.jsx route, Sidebar.jsx entry). Reference run 74 winning-concept.md for paste-ready code. Include invariants: client_id not tenant_id, no __future__ annotations.
**Impact:** Routes highest-scored pending customer value item through autonomous execution channel, bypassing human activation bottleneck.
**Category:** customer_value

---

### Idea 3: Add brain/INGESTION-LOG.md to Subconscious Phase 2 Evidence Sources
**Evidence:** Runs 77 and 78 did not check INGESTION-LOG.md. The brain data staleness was invisible to ideation for 2 runs. Subconscious SKILL.md Phase 2 lists specific files to read but INGESTION-LOG.md is not among them.
**Action:** Add `brain/INGESTION-LOG.md` (last 10 lines) to Phase 2 evidence gathering in `.claude/skills/subconscious/SKILL.md`. If last entry shows failure: surface as evidence item "BRAIN DATA STALE — N days". Update evidence summary to include brain data freshness status.
**Impact:** Future subconscious runs explicitly surface data quality issues. Prevents ideating on stale brain context without knowing it.
**Category:** workflow

---

### Idea 4: Morning Digest — Add Brain Connector Freshness Check
**Evidence:** Morning digest was running (ops/routines/logs/morning-digest-2026-07-03.md exists) but did not flag the brain connector failures. ops/monitoring/ has uptime-checks.json but no brain-monitoring.
**Action:** Add brain connector check to morning digest routine: read brain/INGESTION-LOG.md, if last entry is failure → include "⚠ Brain connectors FAILING" as P0 item in digest output.
**Impact:** Human sees brain connector failure at morning review, not just when subconscious runs. Faster path to credential fix.
**Category:** operational

---

### Idea 5: check_project_invariants.py — Add Brain Connector Freshness as Invariant
**Evidence:** check_project_invariants.py guards 6 structural invariants at pre-commit time. Brain data freshness is not a code invariant — it's an operational concern. However, adding it would make the staleness visible on every commit attempt.
**Action:** Add a 7th check to scripts/check_project_invariants.py: read brain/INGESTION-LOG.md, if last entry date is > 7 days ago → WARNING (not FAIL). Non-blocking pre-commit warning.
**Impact:** Developers see brain staleness during commit workflow. Low-friction visibility.
**Category:** code_health
