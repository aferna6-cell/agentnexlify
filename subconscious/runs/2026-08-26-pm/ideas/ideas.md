# Ideas — Run 110 (2026-08-26-pm)

## Evidence Digest
- KB autopopulate ran today at 08:18 (4 articles compiled, embeddings skipped — no API creds). Staleness resolved for now.
- Step 9J (Dependabot auto-merge) first execution on nightly-2026-08-25: 19 PRs open, **0 merged**. All minor/patch candidates returned `mergeable_state: "unknown"`. Major-version bumps correctly skipped. Block is active but producing zero security merges.
- Revenue commit #686 (2026-08-26): annual billing, voice addon (+$49.99/mo), managed tier, partners endpoint, churn watch list — 7 new backend files. Nightly found MEDIUM risk: voice addon double-billing gap on `agent_os` plan upgrade → GH #687 filed.
- GH #669: 97/97 routers missing `block_demo_role`, filed 2026-08-20. No middleware PR. Per-file patching confirmed whack-a-mole by Step 9I pattern.
- run_109_mandate explicitly named Step 9K (stale subconscious PR closer) as run 110 candidate.
- GH #399 (AUTOPILOT_GH_TOKEN) still open Day 41+.

---

### Idea 1: Fix Step 9J — Switch from `mergeable_state` to commit check-runs for CI gate
**Evidence:** nightly-2026-08-25 Step 9J result: 19 Dependabot PRs open, 0 merged. All minor/patch PRs returned `mergeable_state: "unknown"` — GitHub computes this lazily and resets it to `unknown` after a period of inactivity. PRs aging 4+ weeks still showed `unknown`. This is a known GitHub API behavior: `mergeable_state` is not reliable for automated merging; commit check-run statuses are the correct signal.
**Action:** Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`: replace `mergeable_state == "clean"` check with a commit check-run query — fetch the PR's head SHA, list its check runs via `mcp__github__get_check_run` or `actions_list`, gate on `status: "completed"` + `conclusion: "success"` for all required checks. Also add: if no check runs exist (new PR, CI not triggered), skip with log. Keep major-version bump guard unchanged.
**Impact:** Security dep patches start merging within 24h of CI completing, eliminating 4-week+ CVE exposure window. 19 PRs currently eligible; indefinitely compounding.
**Category:** operational

---

### Idea 2: Add `block_demo_role` FastAPI middleware to `backend/main.py` — close GH #669
**Evidence:** GH #669 (2026-08-20): Step 9I sweep found 97/97 checked routers missing `Depends(block_demo_role)`. GH #643 (appointment_briefs.py) and GH #661 (scoring_config.py) were per-file fixes that took 6+ days each — same class bug filed twice in 6 days proves whack-a-mole. Nightly-2026-08-25 Step 9I: 10 more missing routers found, all already tracked under #669. Per-file patching cannot keep up with new feature velocity.
**Action:** Enrich GH #669 with a detailed implementation sketch: add FastAPI middleware in `backend/main.py` that intercepts POST/PUT/DELETE/PATCH requests, checks `block_demo_role` (or re-uses the existing `Depends` logic), unless path matches allowlist (`/api/auth/*`, `/api/webhooks/*`, `/widget/*`, `/api/admin/*`). Add `test_demo_role_middleware.py`. M-effort, requires human approval.
**Impact:** Closes entire class of recurring security issue. 97 routers protected in one PR vs 97 individual patches. Eliminates future Step 9I findings.
**Category:** code_health

---

### Idea 3: Enhance GH #687 with full implementation sketch — voice addon double-billing fix
**Evidence:** nightly-2026-08-26 found MEDIUM risk in revenue commit #686: `auth_billing.py::billing_change_plan` has no logic to detect or cancel an active voice addon subscription when a `chatbot` tenant upgrades to `agent_os` (which already includes voice). GH #687 filed. Revenue commit is same-day — fix window is short before real customers hit this.
**Action:** Add implementation sketch to GH #687: in `billing_change_plan`, after determining new plan is `agent_os`, query `stripe_service` for active voice addon subscription (filter by `metadata.addon == 'voice'` on customer's subscriptions), cancel if found. Add test `test_voice_addon_cancelled_on_agent_os_upgrade`. Labels: `billing`, `ai-ready`.
**Impact:** Prevents double-billing real customers. Trust + revenue protection. GH #687 becomes executable by issue-to-pr-loop when GH #399 unblocks.
**Category:** customer_value

---

### Idea 4: Step 9K — Add stale subconscious PR report step to nightly SKILL.md
**Evidence:** run_109_mandate explicitly named Step 9K as run 110 candidate if ≥3 open subconscious PRs. Historical context: 5-6 open draft subconscious PRs at runs 102-107. run_109 merged into existing PR (#674). PR pile-up creates governance noise and makes it harder to track which recommendations are actionable.
**Action:** Add Step 9K block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9J: list open PRs with head branch matching `subconscious/*`, log those >7 days old, post a comment noting supersession status. Report-only (no auto-close). S effort, autonomous-executable.
**Impact:** Governance hygiene — PR count visible daily; owner can decide to close superseded drafts. Reduces review overhead.
**Category:** workflow

---

### Idea 5: Wire `churn_watch.py` as a daily Routine or morning-digest step
**Evidence:** Revenue commit #686 ships `backend/services/churn_watch.py` with activity queries to surface at-risk tenants (last seen, conversation rate, booking rate). No Routine trigger exists. Same dark-until-triggered pattern as KB autopopulate (72+ days dark before Step 9F). `churn_watch.py` = value waiting to be activated.
**Action:** Add a Step in morning-digest SKILL.md (or new Routine): call `/api/admin/churn-watch` or run `churn_watch.py` directly; surface top-3 at-risk tenants in the digest output. Requires verifying the endpoint exists (may be internal-only CLI script vs exposed endpoint).
**Impact:** Converts churn intelligence from passive (run manually) to active (owner sees it every morning). Could prevent 1-2 churns per month = $240-$2,400/yr revenue retained.
**Category:** customer_value
