# Ideas — 2026-08-01-pm (Run 101)

## Evidence Digest

18 commits landed in the last 3 days. PR #619 (b67710c) is the dominant event: 5 new major services totalling ~2,272 LOC — inbox monitoring, SMS agent, social publishing, prospecting, connector registry. PR #622 (c5a5a62) ships PWA installability + push escalation. Agent graph + autonomous engineering loop landed (d7259d4, 2026-07-26). KB last compile: 2026-07-23 (9 days ago, >7-day threshold). Step 9G (run 100 winner) is ABSENT from nightly SKILL.md. Issue-to-PR loop (GH #399) stalled 18+ days as of 2026-07-22. Moratorium inactive.

---

### Idea 1: Step 9G — KB Self-Healing Trigger (run 100 mandate carry-forward)
**Evidence:** KB 9 days stale (last compile 2026-07-23). Step 9F fired on nightly-2026-07-22: "Step 9F: KB STALE (9 days) — comment added to GH #403." Alert works; repair doesn't exist. Run 100 winner was identical: add `gh workflow run kb-autopopulate.yml` to nightly SKILL.md when >7-day stale. Step 9G absent in SKILL.md (grep returned nothing). Steps 9B/9C/9D/9E/9F all shipped in 1 nightly cycle each via same channel.
**Action:** Add Step 9G bash block after Step 9F in `.claude/skills/nightly-commit-review/SKILL.md`. Block: trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`, sleep 30s, check conclusion, comment on GH #403 with specific diagnostic if failed (e.g. empty secrets). ~30 lines bash.
**Impact:** KB freshness restored autonomously within 24h of stale threshold breach. Tenant AI chat quality maintained without human intervention.
**Category:** operational

---

### Idea 2: prospecting.py God-Class Split (PR #619 debt)
**Evidence:** PR #619 (b67710c, 2026-07-31) ships `backend/services/prospecting.py` at 536 lines — approaching the 600L god-class threshold. Contains 3 distinct concerns: lead discovery (URL scraping + GBP lookup), sequence management (schedule + retry logic), rate limiting (per-tenant caps). CLAUDE.md Rule 9: factor at 600L. /god-class-splitter skill available (e848b87, live).
**Action:** Invoke `/god-class-splitter` on `backend/services/prospecting.py` — split into `prospecting_discovery.py` + `prospecting_sequences.py` + `prospecting_rate_limiter.py`. Run post-split-test-repair checklist for `test_prospecting.py` (1368L, high mock density).
**Impact:** Prevents future god-class bloat. Makes prospecting subsystem testable in isolation. Keeps blast radius small when rate-limit logic changes.
**Category:** code_health

---

### Idea 3: GH #399 Specific Rotation Steps Comment
**Evidence:** autopilot-issue-loop.yml stalled 18+ days as of 2026-07-22 (latest data). AUTOPILOT_GH_TOKEN expired 2026-07-04. Nightly Step 9D confirms: "STALLED — loop last ran 2026-07-22T04:27:29Z." Multiple escalation comments posted but none included step-by-step Railway rotation instructions. 3 ai-ready issues open (#69, #70, #114). GH #399 open.
**Action:** Post comment on GH #399 with exact rotation steps: "1. Go to github.com/settings/tokens → Generate new token (repo + workflow scopes, 90-day expiry) → Copy. 2. Railway → agentnexlify project → Variables → AUTOPILOT_GH_TOKEN → paste new token → Deploy. 3. Confirm: autopilot-issue-loop.yml next scheduled run succeeds."
**Impact:** Reduces human activation friction from "investigate and figure it out" to "copy-paste 3 steps." Loop restart unlocks 3+ ai-ready issues.
**Category:** operational

---

### Idea 4: connector_registry.py Interface Contract ADR
**Evidence:** PR #619 ships `connector_registry.py` (314L) as the central hub for Gmail, social, prospecting, and SMS connectors. As more connectors land, this file will grow into a god-class if there's no documented interface. `connector_registry.py` already has 4 connector types wired in 314 lines. Each new connector will add more methods.
**Action:** Write `planning/decisions/2026-08-01-connector-interface-contract.md` documenting: (1) required interface methods per connector type (connect, disconnect, health_check, sync), (2) registry pattern (plugin list vs. dict dispatch vs. class registry), (3) guideline: max 50L per connector in registry, full logic in service file. Prevents future sprawl.
**Impact:** Prevents connector_registry.py from becoming the next god-class as Facebook, MS365, HubSpot connectors land. Estimated: saves 2-3 extraction refactors.
**Category:** code_health

---

### Idea 5: PWA Push on appointment_completed for Owner Notification
**Evidence:** `c5a5a62` (today) ships `frontend/public/manifest.webmanifest` + PWA icons + `os_push_notify.py` escalation push. `appointment_jobs.py` (PR #475, 2026-07-18) fires `appointment_completed` rule event. `escalations.py` (415L, PR #619) already has `push_notify` dispatch. The loop is nearly closed: appointment completes → owner gets push to follow up. Missing: one-line rule wiring `appointment_completed` → escalation push.
**Action:** Add `appointment_completed` to `escalations.py` rule handler: when appointment status transitions to `completed`, call `os_push_notify.send_push(tenant_id, "Appointment completed — time to request a review!")`. Add 1 test in `test_escalations.py`. ~15 lines total.
**Impact:** Owners notified in real-time to request reviews post-appointment. Closes the booking → review feedback loop. High LTV impact per tenant.
**Category:** customer_value
