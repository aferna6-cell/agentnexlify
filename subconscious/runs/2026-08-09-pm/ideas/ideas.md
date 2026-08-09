# Candidate Ideas — Run 102 (2026-08-09-pm)

## Evidence Digest

- **Step 9G CONFIRMED FIRING** (nightly-2026-08-07): triggered `gh workflow run kb-autopopulate.yml` — 204 (queued). Conclusion after 30s: `pending`. KB still stale 17 days (last log entry: 2026-07-23). Workflow likely failed due to GH #500 (Actions billing limit) or GH #403 (missing ANTHROPIC_API_KEY) — no failure diagnostic posted because conclusion was `pending`, not `failure`.
- **4 open subconscious draft PRs**: #606 (2026-07-28, 12 days), #611 (2026-07-30, 10 days), #613 (2026-07-31, 9 days), #626 (2026-08-02, 7 days — updated today). Mandate: re-raise Step 9H with idempotent design.
- **GH #399, #403, #500 all still open**: autopilot stalled 36+ days, ANTHROPIC_API_KEY missing, GH Actions billing limit. Three blocked pipelines.
- **buy-usage block_demo_role fix (GH #640)**: 3-commit chain across nightly-08-07/08/09. Pattern: 3rd time a billing/payments route was missing a guard.
- **Nexlify Score (e0e9be6, 2026-08-06)**: response_score.py is FULLY DETERMINISTIC — no LLM calls. Parking lot item "Nexlify Score token-burn guard" is invalid; closing.
- **connector_awareness client_id bug (2026-08-01)**: `.eq("tenant_id", client_id)` on `tenant_api_keys` — 4th occurrence of client_id/tenant_id mixup. Nightly client_id sentinel only covers `leads` and `conversations`, NOT `tenant_api_keys`.

---

### Idea 1: Step 9H — Idempotent PR Pile Alerter
**Evidence:** 4 open subconscious draft PRs (#606, #611, #613, #626), oldest 12 days. Run 102 governance mandate: "If not merged or closed, re-raise Step 9H but with redesigned idempotent alerting." Prior Step 9H killed for MCP tenant monitoring (different concept); the PR pile version was PARKED with note "current design would fire every nightly indefinitely." Human has no automated signal about PR pile age.
**Action:** Add Step 9H bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9G: query `gh pr list --repo aferna6-cell/agentnexlify --state open --search "head:subconscious" --json number,title,createdAt`; count open PRs; if count > 0 AND (count changed from last nightly OR oldest PR age > 7 days with no 9H log in last 7d), post summary comment on oldest open PR: "Subconscious PR pile: N open draft PRs, oldest created YYYY-MM-DD. Please review/merge or close." Store last 9H alert date as single-line note in nightly log to prevent daily re-fire.
**Impact:** Human gets exactly-once weekly signal per stale pile vs. no signal (current state).
**Category:** workflow

---

### Idea 2: GH #500 Diagnostic Comment — Billing Limit Blocking Step 9G
**Evidence:** GH #500 "GitHub Actions down repo-wide: all hosted-runner jobs fail in 3s since 12:21 UTC" filed 2026-07-27, last updated 2026-07-27 (13 days with 0 activity). Step 9G triggered kb-autopopulate.yml (204 queued) nightly-08-07 but KB still stale 17 days — meaning the workflow either never ran or failed silently. Step 9G only posts failure diagnostic on `failure` conclusion; `pending` conclusion exits silently. No existing GH comment connects #500 → Step 9G failure → KB staleness chain.
**Action:** Post comment on GH #500 via `mcp__github__add_issue_comment` establishing the connection: kb-autopopulate.yml was triggered 2026-08-07 by Step 9G but KB is still stale 17 days. If the hosted-runner billing limit is still active, this is why. Impact scope: KB fresh AI answers for tenants (17 days stale), autopilot-loop (40 ai-ready issues queued for 36+ days), all future Step 9G self-healing attempts.
**Impact:** Human understands #500 now blocks 3 active systems, not just historical context. Potentially unblocks 3 pipelines with one billing settings fix.
**Category:** operational

---

### Idea 3: Extend Client-ID Sentinel to tenant_api_keys Table
**Evidence:** bug-patterns.md latest entry (2026-08-01): connector_awareness.py used `.eq("tenant_id", client_id)` on `tenant_api_keys` — 4th occurrence of client_id/tenant_id mixup in codebase. Nightly Step 3 already checks `leads` and `conversations` for `.eq("tenant_id"` misuse. The check does NOT cover `tenant_api_keys` or `connector_registry` (confirmed via SKILL.md read). The missing coverage directly caused the 2026-08-01 bug.
**Action:** Update Step 3 (client_id check) in nightly SKILL.md to also grep for `.eq("tenant_id"` on `tenant_api_keys` and `connector_registry` table references. Any match in backend/**/*.py → flag as MEDIUM, add to nightly report.
**Impact:** Prevents 5th occurrence of most-frequent bug class. The bug always reaches production undetected (caught by nightly after the fact, not before); adding the sentinel catches it at next nightly review.
**Category:** code_health

---

### Idea 4: Step 9I — Next-Nightly KB Completion Verification
**Evidence:** Step 9G's design limitation: it checks conclusion 30s after trigger. If the workflow takes 5+ minutes (common for Claude code CI jobs), conclusion is `pending` at 30s. Step 9G exits without posting any diagnostic. Next nightly has no mechanism to check if the workflow eventually completed or failed. KB is now stale 17 days with Step 9G having fired once — and no follow-up.
**Action:** Add Step 9I to nightly SKILL.md after Step 9G: if previous nightly log contains "Step 9G: kb-autopopulate trigger attempted" with `pending` or `in_progress`, run `gh run list --workflow=kb-autopopulate.yml --limit=3 --json conclusion,url,createdAt` and check the most recent run's conclusion. If `failure`: post GH #403 comment with URL. If `success`: verify knowledge-base/log.md last entry is newer than trigger date; if still stale despite `success`, note in log and post diagnostic to GH #403.
**Impact:** Closes the monitoring gap where Step 9G fires and thinks it's done, but the workflow failed silently after the 30s check window.
**Category:** operational

---

### Idea 5: Grandfathered Plan Gate Audit — New Features from e0e9be6
**Evidence:** Run 101 parking lot: "Grandfathered plan gate audit (grep agent_os without grandfathered — code_health)." Commit e0e9be6 (2026-08-06, 22 files, 1528 lines) shipped appointment briefs, daily focus, Nexlify Score, usage meter — all agent_os features. CLAUDE.md: grandfathered plans (growth, autopilot, professional, enterprise) "gates include them." If any gate in the new sprint checks only `agent_os` without grandfathered, paying old-contract customers get silently blocked.
**Action:** Grep backend for plan gate calls in new e0e9be6 files; cross-reference `backend/services/stripe_service.py::PLAN_BASELINE_TOKENS` grandfathered list. File GH issue listing any gate that checks `agent_os` only (without grandfathered plans). Include exact file:line refs.
**Impact:** Prevents revenue churn from grandfathered customers being silently blocked from features they've paid for. Pattern: 2026-07-15 nightly independently caught a grandfathered gate gap (AI Workforce); this is the same class applied to the new sprint.
**Category:** customer_value / code_health
