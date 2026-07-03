# Run 78 Ideas — 2026-07-03

Generated from evidence: run 78 mandate fires (ops/monitoring/healthz-alert.sh missing), 3+ days zero production commits, healthz timeout incident persists undetected, Dependabot PRs #381-383 open, /healthz handler root cause unknown, P-001 parking lot XS item.

---

### Idea 1: Add Step 9B to nightly SKILL.md — Healthz Monitor Maintenance
**Evidence:** Run 78 mandate fires. `ops/monitoring/healthz-alert.sh` missing from `ops/monitoring/` (only `uptime-checks.json` present). `/api/v1/healthz` timed out 10:27 UTC 2026-07-02. `SLACK_ALERT_WEBHOOK_URL` still not set. Run 77 winner was AUTONOMOUS-EXECUTABLE via nightly but nightly did not act on it. Run 77 winning-concept.md exists and prescribes exactly this action.
**Action:** Add Step 9B to nightly-commit-review SKILL.md Scheduled Task Prompt: check for `ops/monitoring/healthz-alert.sh`, write it from embedded content in winning-concept.md if missing. Include full script content in the winning concept so nightly can copy verbatim.
**Impact:** Closes the 3-day-old monitoring gap on next nightly run. Durable — nightly maintains it going forward. Human notified via GH issue + PushNotification to complete SLACK_ALERT_WEBHOOK_URL.
**Category:** operational

---

### Idea 2: Diagnose /healthz Handler Root Cause + Update bug-patterns.md
**Evidence:** P-004 parking lot item from run 77. `/api/v1/healthz` timed out at 10:27 UTC 2026-07-02 while `/version` returned 200 — partial failure, not crash. Root cause unknown. `docs/dev-knowledge/bug-patterns.md` has no entry for this. `grep -n "healthz" backend/main.py backend/routers/*.py` proposed as bonus action in run 77 but not executed.
**Action:** Read `/healthz` handler implementation. Identify what could hang (external calls, DB connection pool exhaustion, sync I/O in async path, missing timeout). Write finding to `docs/dev-knowledge/bug-patterns.md` under a new "Endpoint Timeout Patterns" section. File GH issue if a fixable cause is found.
**Impact:** Transforms a detection-only posture (monitoring alert) into a root-cause-known posture. Prevents recurrence. Estimated 20 min read + write.
**Category:** code_health

---

### Idea 3: Merge Dependabot PRs #381–383 — Patch Bump Hygiene
**Evidence:** Run 77 bonus action: "Merge Dependabot PRs #381-383 (patch bumps, `npm audit fix` safe)". Referenced in winning-concept.md. These PRs have been open since at least 2026-07-02. Outdated deps accumulate CVE surface.
**Action:** Verify PRs #381-383 are patch-only bumps (semver minor/patch, no breaking). Run `npm audit` before + after to confirm no regression. Merge via GH MCP. Recommendation only — human or autonomous merge.
**Impact:** Closes 3 open Dependabot PRs. Reduces CVE surface. Zero breaking risk for patch bumps.
**Category:** operational

---

### Idea 4: Plan-Name Guard Check 7 — Pre-Commit Validation
**Evidence:** P-001 parking lot from runs 73+. `scripts/check_project_invariants.py` Check 5 guards plan names at runtime. No pre-commit guard catches retired plan names (`foundation`, `operations`) before they reach the repo. XS effort, marked AUTONOMOUS-EXECUTABLE in parking lot.
**Action:** Add Check 7 to `scripts/check_project_invariants.py`: grep Python/SQL files for retired plan names and fail with clear message. Wire via pre-commit hook after `check_project_invariants.py` exit-1 from widget drift is resolved.
**Impact:** Prevents plan-name bugs before they hit production. Zero urgency (no current incident) but XS effort.
**Category:** code_health

---

### Idea 5: File GH Issue for SMS Compliance Dashboard Acceleration
**Evidence:** B-002 (SMS Compliance Dashboard) active since runs 73+74. GH #385 open, issue-to-pr-loop active. Backend + migration 160 shipped. Endpoint + dashboard page outstanding. 14+ days since issue filed. No PR opened yet by the loop.
**Action:** Add a comment to GH #385 with paste-ready endpoint + page code (from run 74 sketch). Accelerate issue-to-pr-loop by providing concrete implementation detail instead of waiting for the loop to derive it independently.
**Impact:** Unblocks B-002 from stall. Delivers SMS Dashboard page faster. No new code here — just context injection into existing issue.
**Category:** customer_value
