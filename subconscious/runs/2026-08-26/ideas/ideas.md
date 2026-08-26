# Candidate Ideas — Run 112 (2026-08-26)

## Evidence Digest

**3-day commits:** Two major commits. (1) `10acf83` — Revenue sprint: 46 files, 2866+ lines. Annual prepay, voice add-on, partners program, outreach tools, billing_addons.py (113 lines), migration 194, 957+ new test lines. (2) `13772f1` — nightly 2026-08-26 filed GH #687 (voice addon double-billing gap, MEDIUM risk).

**Step 9J first run (nightly-2026-08-25):** 19 Dependabot PRs found. 6 major-version bumps skipped (safety gate). 2 minor/patch candidates had `mergeable_state: "unknown"` → 0 PRs merged. Corrected log filed (5bc0288). Expected behavior — CI not yet evaluated on aging PRs.

**Step 9I (nightly-2026-08-25):** 10 more routers missing block_demo_role found; all already tracked under GH #669. No new issues filed (dedup guard working).

**KB freshness:** GH Actions dark (GH #500). GH #403 unresolved. Step 9G still triggering but failing. KB log shows recent article indexing from session-level run (not Actions).

**GH #399:** OPEN Day 41+. AUTOPILOT_GH_TOKEN still expired.

---

### Idea 1: Fix voice addon double-billing on plan upgrade (GH #687)
**Evidence:** nightly-2026-08-26 filed GH #687. `billing_change_plan` in `auth_billing.py` has no logic to detect/cancel active voice_addon Stripe subscription when upgrading to `agent_os` (which bundles voice). `billing_addons.py` (new, 10acf83) prevents buying voice addon on `agent_os` but the upgrade path from chatbot+voice → agent_os is unguarded. Any customer in that path gets double-billed until they notice.
**Action:** In `auth_billing.py:billing_change_plan`, after detecting upgrade to `agent_os`, list tenant's active Stripe subscriptions, find voice_addon item, cancel it. Add regression test in `test_voice_addon.py`.
**Impact:** Revenue correctness for any chatbot+voice tenant who upgrades. Prevents churn (surprise double charge). No customer affected yet (voice addon just shipped), window to fix cleanly.
**Category:** code_health

---

### Idea 2: Step 9K — Add stale subconscious PR report to nightly SKILL.md
**Evidence:** Run 109 mandate item 6 explicitly: "Step 9K (stale autonomy PR closer, report-only) if ≥3 subconscious PRs open." Run 108 noted "4 draft PRs aging." Run 107: "4 draft PRs aging." Pattern: subconscious draft PRs accumulate without review, creating governance noise. Autonomous-executable via SKILL.md edit (same channel as Steps 9C/9F/9G/9I/9J).
**Action:** Add Step 9K block to nightly-commit-review SKILL.md after Step 9J. List open PRs with head branch starting "subconscious". Log count + ages. If oldest >30 days AND no commits in last 7 days: post comment "Stale subconscious PR — no activity 30d+. Consider closing or rebasing." Report-only (no auto-close).
**Impact:** Surface subconscious PR pile-up daily. Human gets daily nudge on oldest. Zero risk (report-only).
**Category:** workflow

---

### Idea 3: Improve Step 9J — explicit "unknown state" retry with 30s delay
**Evidence:** All 2 minor/patch Dependabot candidates had `mergeable_state: "unknown"` on first check (nightly-2026-08-25). 0 PRs merged. This is a GitHub API timing issue — state computation is async. A 30s re-fetch would catch cases where state resolved during the run. Without retry, Step 9J may never merge PRs that resolve quickly.
**Action:** Edit Step 9J block in nightly SKILL.md: after first pass, collect PRs with `mergeable_state: "unknown"`. Wait 30 seconds. Re-fetch and re-check. Attempt merge if now "clean". Log both passes.
**Impact:** Converts "unknown" timing gap into successful merges. Step 9J gets its first actual merges. Compounding: security patches land same-night.
**Category:** operational

---

### Idea 4: Add block_demo_role to billing_addons.py POST endpoints
**Evidence:** `billing_addons.py` (113 lines) shipped in 10acf83 with POST /billing/addons/voice/purchase and POST /billing/addons/voice/cancel. Step 9I in nightly-2026-08-25 found these are missing block_demo_role (tracked under GH #669 class-wide). These are revenue-touching endpoints — demo tenants must not be able to trigger addon purchases/cancellations.
**Action:** Add `Depends(block_demo_role)` to both POST endpoints in `billing_addons.py`. 2-line change. Also check `billing.py` new annual prepay endpoints.
**Impact:** Closes immediate security gap on new revenue endpoints. Autonomous-executable by nightly code-change channel (LOW risk, 2 lines, no migration).
**Category:** code_health / security

---

### Idea 5: Add middleware-level block_demo_role FastAPI guard
**Evidence:** GH #669 — 97/97 routers missing block_demo_role (nightly-2026-08-20 filing). Step 9I files issues daily but each requires individual fix. The root fix is a FastAPI middleware or router-level dependency. Each new router (billing_addons.py, partners.py from 10acf83) inherits the problem. Parking lot from run 108.
**Action:** Add `block_demo_role` as a global FastAPI dependency on the main router group. All routes inherit it without individual `Depends()` calls. Exemptions list (webhooks, widget, auth) in a single config.
**Impact:** Eliminates the entire class of missing-block_demo_role forever. Step 9I becomes "0 new violations" every nightly. GH #669 closes.
**Category:** code_health / security
