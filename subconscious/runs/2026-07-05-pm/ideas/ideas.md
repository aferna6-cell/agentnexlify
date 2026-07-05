# Ideas — Run 80 (2026-07-05-pm)

## Evidence Digest

**brain/INGESTION-LOG.md:** GitHub 403 + SUPABASE_ACCESS_TOKEN missing — 5 consecutive days (2026-07-01 through 2026-07-05T09:47Z). Run 80 mandate fires from run 79 winning-concept.md §Run 80 Mandate. All autonomous agents (subconscious, nightly, issue-to-pr-loop) running on stale context since July 1.

**check_project_invariants.py:** Still exits 1 on widget drift (retired topic — permanent). All other checks PASS.

**ops/monitoring/:** Only `uptime-checks.json`. `healthz-alert.sh` still absent. Step 9B was added to nightly SKILL.md by run 79 — nightly will write the script tonight.

**SMS Compliance Dashboard:** No `SmsCompliance.jsx` in frontend, no `sms_compliance.py` router. Paste-ready code in `subconscious/runs/2026-06-30-pm/winning-concept.md`. Unimplemented 5+ days (runs 73-74). Run 74 mandate: file GH issue for issue-to-pr-loop if still not shipped.

**Production commits:** 0 in last 3 days (only subconscious/brain/ops automation).

---

## Candidate Ideas

### Idea 1: Add Step 9C to nightly SKILL.md — Brain Connector Health Check
**Evidence:** `brain/INGESTION-LOG.md` shows 5 consecutive connector failures (2026-07-01 to 2026-07-05). Run 80 mandate fires explicitly from run 79 `winning-concept.md §Run 80 Mandate`. No automated detection pathway existed — failure was silent for 4 days before first detection.
**Action:** Append Step 9C block to `.claude/skills/nightly-commit-review/SKILL.md`. Step reads `brain/INGESTION-LOG.md`, detects 3+ consecutive `error` or `skipped` lines in the last 3 entries, creates a GH issue with `human-action-required` label if detected. Consistent with precedent: Step 9A (Moratorium Escalation Protocol, run 19, delivered in 1 cycle), Step 9B (healthz maintenance, run 78, delivered this session by run 79).
**Impact:** Closes silent degradation gap. Brain connector failures currently go undetected until subconscious runs (every 2 days). Step 9C fires nightly, alerting within 1 cycle of a 3-day failure pattern. All autonomous agents benefit from timely brain refresh.
**Category:** operational

---

### Idea 2: File GH Issue for SMS Compliance Dashboard via issue-to-pr-loop
**Evidence:** SMS Compliance Dashboard paste-ready code in `subconscious/runs/2026-06-30-pm/winning-concept.md`. Council score 12/12 (run 70). Unimplemented 5+ days. No `SmsCompliance.jsx` or `sms_compliance.py` router confirmed today. Run 74 active_directions note: "Run 76 mandate: file GH issue for issue-to-pr-loop." That mandate was absorbed by Zapier runs — SMS GH issue never filed.
**Action:** Create GH issue with `ai-ready` + `customer-value` + `frontend` + `backend` labels. Body: paste-ready code from run 74 winning-concept.md (backend router + React page + exact edit instructions for `main.py`, `App.jsx`, `Sidebar.jsx`). Issue-to-pr-loop picks up and implements autonomously.
**Impact:** Converts human-required activation energy (~30 min) to autonomous execution. TCPA compliance visibility for tenants. AUTONOMOUS-EXECUTABLE via issue-to-pr-loop if loop is running.
**Category:** customer_value

---

### Idea 3: Plan-Name Guard Pre-commit Check 7
**Evidence:** Parked since run 76. Retired plan names (`foundation`, `operations`) could drift back into feature gates after future code edits. The repricing bug (runs 62/76) caused 100% of new paid tenants to be locked out of premium features.
**Action:** Append bash block to `scripts/hooks/pre-commit` after Check 13. Grep staged `backend/**/*.py` for retired plan names (`foundation`, `operations`) outside of known-grandfathered sections. FAIL if found. AUTONOMOUS-EXECUTABLE.
**Impact:** Prevents recurrence of the plan-gating half-migration bug class. Guards against a LOW-frequency but HIGH-severity bug.
**Category:** code_health

---

### Idea 4: Create ops/monitoring/SETUP.md — Document SLACK_ALERT_WEBHOOK_URL Setup
**Evidence:** `SLACK_ALERT_WEBHOOK_URL` not set (confirmed 3+ consecutive runs). Run 78 governance: "no further automated mandate." Once nightly Step 9B writes `healthz-alert.sh`, the script will silently fail without the webhook. No documentation exists.
**Action:** Create `ops/monitoring/SETUP.md` documenting: what `SLACK_ALERT_WEBHOOK_URL` is, how to create a Slack incoming webhook, where to set it in Railway Variables, how to verify. Pure markdown addition, AUTONOMOUS-EXECUTABLE.
**Impact:** Human can follow clear instructions to enable alerting. Converts undocumented gap to documented one. Unblocks the healthz-alert chain.
**Category:** operational

---

### Idea 5: email_sequences.py God-Class Split
**Evidence:** `email_sequences.py` confirmed 1255L (last checked run 41). Parked since run 35. god-class-splitter SKILL.md exists (e848b87). post-split-test-repair SKILL.md exists (d481799).
**Action:** Invoke `/god-class-splitter` on `email_sequences.py`. Split into `email_crud.py`, `email_enrollment.py`, `email_processor.py`.
**Impact:** Reduces blast radius of future email changes. Active moratorium (pending_human items) lowers priority.
**Category:** code_health
