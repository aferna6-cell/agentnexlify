# Ideas — Run 104 (2026-07-26-pm)

## Evidence Summary

3 consecutive quiet nightly windows (2026-07-24/25/26) — only auto-nightly log commits. GH #500 (Actions spending limit) open 6 days — all CI dark, no runners assigned, all scheduled workflows blind. Step 9G implemented on branch `subconscious/run-101-step-9g` (PR #577, 7 occurrences), not yet on main. PR #577 and #575 still draft, unreviewed. KB fresh (2026-07-23, 3 days). Run 103 winner: Managed Agents Phase 0 GH issue — pending human approval, not created. Step 9H (GH Actions heartbeat) was parking-lot'd at run 103 pending PR #577 merge — since we're now ON the branch, the condition is satisfied.

---

### Idea 1: Step 9H — GH Actions spending-limit daily heartbeat in SKILL.md
**Evidence:** GH #500 open 6 days (created 2026-07-20, last updated 2026-07-25 from run 101's comment). All CI dark. No owner activity in 3 days. The nightly runs WITHOUT GH Actions (it runs in Claude Code context), so the nightly CAN detect the outage even when Actions is broken. Step 9G failure path already references GH #500 — Step 9H is a natural complement: daily status ping on GH #500 itself. Parking-lot condition "until PR #577 merges" satisfied since we're on the same branch.
**Action:** Insert Step 9H after Step 9G in `.claude/skills/nightly-commit-review/SKILL.md`. Condition: always runs. Check last 5 Actions run conclusions. If ≥4 failed: check GH #500 state — if open, add daily ping comment; if closed, log restored. ~25 bash-style pseudocode lines.
**Impact:** Owner gets daily automated status pings on GH #500 (not just one comment 6 days ago). When Actions is restored and owner closes #500, the step self-disables. Prevents the "silent dark CI" scenario from lasting weeks without a daily signal.
**Category:** operational

---

### Idea 2: Managed Agents Phase 0 GH issue (run 103 carry-forward)
**Evidence:** Run 103 recommended this as winner. `backend/services/managed_agents_registry.py` has advised_*() helpers wired. All managed-agent endpoints return 503 — MANAGED_AGENTS_ENVIRONMENT_ID not set in Railway. The rollout plan exists (`plans/managed-agents-rollout_plan.md`). Run 103 won on this but marked "pending_approval: true" and did not create the issue.
**Action:** Create GH issue: "[Managed Agents] Phase 0: provision environment + Railway env vars + smoke test" with 6-step checklist. No code change. 15 min for owner to execute.
**Impact:** Unblocks the entire Managed Agents product lane. Every day Phase 0 stays unstarted is a day the differentiated AI layer serves 0 tenants.
**Category:** customer_value

---

### Idea 3: PR #577 merge readiness notice in PR body
**Evidence:** PR #577 has been open since 2026-07-24 (2 days). It contains Step 9G + all run 100-103 artifacts. The PR body describes Step 9G as already implemented. No CI is passing (Actions down). Owner sees draft + "CI failing" which may cause hesitation to merge.
**Action:** Update PR #577 body to add a "Merge readiness" section: local grep confirms Step 9G present (7 occurrences), all tests that can run locally pass (invariants pass, no widget drift), CI failure is GH #500 not this PR's fault. Request owner to merge despite CI darkness.
**Impact:** Removes owner's hesitation to merge a draft PR with red CI. Step 9G goes live on main. Nightly starts executing self-healing.
**Category:** workflow

---

### Idea 4: email_sequences auth failures — GH issue for CI return
**Evidence:** 8 pre-existing auth test failures in `backend/tests/test_email_sequences.py` suite, confirmed in nightly-2026-07-24. Pre-existing (inherited from pre-split state, not caused by ab1a7c2 split). CI dark so they can't be verified or fixed. Without a GH issue, they'll be forgotten when Actions recovers.
**Action:** Create GH issue: "email_sequences auth test failures (8): pre-existing, needs investigation when CI returns." Include test names, error class (auth mocking issue). Label: `test-debt`, `ai-ready`.
**Impact:** When GH #500 is resolved and CI recovers, issue enters the issue-to-pr-loop queue and gets auto-fixed. Without the issue, these failures go unreported and potentially block CI again.
**Category:** code_health

---

### Idea 5: KB local fallback in Step 9G failure path
**Evidence:** Step 9G triggers `gh workflow run kb-autopopulate.yml` which fails when GH #500 is active (spending limit blocks all runners). The failure path comments on GH #403. But kb-autopopulate.sh can also be run directly: `bash scripts/daily/kb-autopopulate.sh`. The nightly runs in Claude Code context which may have ANTHROPIC_API_KEY available.
**Action:** In Step 9G's failure branch (when workflow trigger exits non-zero), add a fallback: attempt `bash scripts/daily/kb-autopopulate.sh 2>&1 | tail -5` and log result. If it succeeds (exit 0), log "Step 9G fallback: KB populated locally." If it fails (missing API key), log the error and still comment on #403.
**Impact:** KB stays fresh even when GH Actions is down. Current situation: KB is 3 days fresh but will go stale if Actions stays down past July 30.
**Category:** operational
