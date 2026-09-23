# Ideas — Run 2026-09-23 (Run 127)

## Evidence Digest

**What changed:** Run 126 winner (Step 9G gh→MCP fix) IMPLEMENTED by today's nightly (2026-09-23). SKILL.md now uses `mcp__github__actions_run_trigger` instead of unavailable `gh` CLI in CCR.

**What's urgent:** AUTOPILOT_GH_TOKEN expires 2026-10-02 — 9 days away. GH #893 filed ad-hoc (P0 label). Step 9E at 76-day threshold does not escalate as deadline approaches; no P0 tier in SKILL.md.

**What's accumulating:** 45 unguarded AI call sites (GH #827, p1, billing). Step 9L detects but doesn't prevent new violations from entering. 6 fresh Dependabot PRs (#885–#891) 1d old. Step 9J still skipping 17/19 PRs per run due to token budget.

**What's healthy:** Step 9G fixed (run 126 win). Step 9K reports 1 subconscious PR open (0 stale). Step 9L fires nightly. Step 9I demo-role sweep active.

---

### Idea 1: Step 9E P0 Tier — 10-Day Credential Expiry Escalation

**Evidence:** AUTOPILOT_GH_TOKEN at 9 days (expires 2026-10-02). GH #893 filed ad-hoc 2026-09-22 with P0 label — proving the need. Current Step 9E only fires at 76-day threshold (approaching_expiry). No escalation as deadline approaches. Without a P0 tier, nightly has no structured action when <= 10 days remain. This is the 7th carry-forward; autonomous-executable since run 122.

**Action:** In `.claude/skills/nightly-commit-review/SKILL.md` Step 9E, add branch: if `days_remaining <= 10` for any credential in ops/credential-rotation-schedule.md — (1) file GH issue with `p0` + `human-action-required` labels (dedup check), (2) append P0 escalation line to nightly log. Log line: "Step 9E: P0 ALERT — {credential} expires in {N} days. GH #{issue_number} filed."

**Impact:** Systematic P0 alert fires for ALL future credential expirations, not just ad-hoc detection. Tonight's nightly would fire P0 tier for AUTOPILOT_GH_TOKEN. Prevents token expiry from silently stopping all automation.

**Category:** operational

---

### Idea 2: Pre-Commit Hook Blocking New Unguarded AI Call Sites

**Evidence:** GH #827 (p1, billing, risk:high) tracks 45 unguarded production AI call sites. check_ai_metering.py (commit 1c5b749) exists and detects violations. Step 9L fires nightly. But no enforcement at commit time — developers can add new unguarded calls without friction, growing the backlog beyond 45.

**Action:** Add entry to `.claude/settings.json` PreCommitHook (or scripts/hooks/pre-commit) running `python3 scripts/check_ai_metering.py --staged-only` — scans only staged backend/routers/ and backend/services/ files for new AI calls without metering guard. Blocks commit if new violations found. Provides actionable error: "New unguarded AI call at path:function — add ai_usage_guard dependency."

**Impact:** Stops the 45-site backlog from growing. Systemic prevention at commit time vs reactive nightly detection. Zero cost to pass if code is already guarded.

**Category:** code_health

---

### Idea 3: Step 9J Token Budget Fix — Process Dependabot PRs First

**Evidence:** run_116_mandate_executed: 17/19 Dependabot PRs skipped per nightly run due to token budget exhaustion. Morning digest 2026-09-22: 6 fresh Dependabot PRs (#885–#891) opened 1d ago (bcrypt, supabase, google-api, uvicorn, vitest, jsdom). At 2/19 processed per run, these 6 PRs would take 3+ nightly cycles to merge — accumulating CVE exposure window.

**Action:** In `.claude/skills/nightly-commit-review/SKILL.md` Step 9J, add position directive: "Run Step 9J BEFORE Steps 9F/9G/9H/9I/9K/9L to ensure Dependabot PRs are processed before token budget is consumed by later steps." Also: increase per-step budget from 2 to 5 (cap already set to 5).

**Impact:** 6 fresh PRs processed within 24h instead of accumulating. CVE window closed from 72h to 24h. Budget fix compounds permanently.

**Category:** operational

---

### Idea 4: GH #892 CI Safety Test — Add pytest Network Isolation

**Evidence:** GH #892 (bug, p1, ci, blocker, 2d old): "CI safety test escaping to network". Staging credential rejection tests are hitting real network endpoints. This bypasses the security boundary that the test is meant to verify.

**Action:** Add `pytest-socket` dependency to `backend/requirements.txt` (test only). In `backend/tests/conftest.py`, add `@pytest.fixture(autouse=True) def disable_network(): socket.setdefaulttimeout(0)` for tests in `test_staging_*` or `test_*_credential*` paths. This forces any network escape to timeout immediately.

**Impact:** Closes GH #892 blocker. Prevents test contamination. Makes CI reliable for credential rejection tests.

**Category:** code_health

---

### Idea 5: Step 9L Scope Expansion — Cover backend/services/ Subdirs

**Evidence:** check_ai_metering.py (run 117, commit 1c5b749) scans backend/routers/ and backend/services/ at top level. GH #827 notes 45 violations. Services like `automation/`, `managed_agents/`, `graph/` are subdirectories — unclear if AST scanner recurses fully into all subdirs.

**Action:** Verify check_ai_metering.py uses recursive glob (`**/*.py`) for both routers and services. If not, fix glob pattern. Add test assertion: script must find at least 1 violation in known-unguarded file (integration test for detector health).

**Impact:** Ensures Step 9L scan is complete. Prevents false PASS when violations exist in subdirs. Closes gap in GH #827 count accuracy.

**Category:** code_health
