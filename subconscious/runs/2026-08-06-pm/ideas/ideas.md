# Ideas — 2026-08-06-pm (Run 101)

## Evidence Digest

KB 14 days stale (last compile: 2026-07-23). Step 9F alerts firing daily on GH #403 but no self-repair fires. Run 100 winner (Step 9G) has been recommended/implemented across 6 unmerged PRs (#625, #626, #613, #611, #606) — none merged to main. PR backlog at 15 open (10 subconscious-adjacent). Major feature sprint landed today (e0e9be6): competitor-inspired insights — appointment briefs, daily focus, Nexlify Score, usage meter (22 files, 1528 lines). Typed KB notes shipped 2026-08-04 (#632) — tenants can type FAQs directly; no in-dashboard discovery for existing tenants. AI Workforce grandfathered plan gate fixed (2869124) — possible class-of-bug. autopilot-issue-loop stalled 33+ days (AUTOPILOT_GH_TOKEN expired), 3 ai-ready issues blocked.

---

### Idea 1: Step 9G direct implementation in nightly SKILL.md (carry-forward escalation)
**Evidence:** KB 14 days stale (last: 2026-07-23). Run 100 winner (2026-07-23 — 14 days ago). Multiple PR-channel implementations (PRs #625/#626/#613) all unmerged. PR recommendation channel has failed 6+ cycles. Run 99 precedent: when Step 9F failed 3 consecutive recommend-only cycles, it was directly implemented in SKILL.md on main in one step — it fired on the very next nightly (confirmed nightly-2026-07-22). Same escalation condition is now met for Step 9G (exceeded 3 cycles by 3x). Step 9G adds `gh workflow run kb-autopopulate.yml` after Step 9F staleness detection.
**Action:** Write Step 9G bash block directly to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F block (line 305), with verbatim implementable content. Commit to main. No PR needed.
**Impact:** Next nightly auto-triggers kb-autopopulate.yml when KB >7 days stale. Self-healing. Ends the 14-day KB stale window immediately. KB freshness → better AI chat answers → lower tenant churn.
**Category:** operational

---

### Idea 2: Step 9H nightly subconscious PR pile-up alerter
**Evidence:** 15 open PRs as of 2026-08-06. 7 are subconscious draft PRs (PRs #625, #626, #613, #611, #606, #604 plus older). Morning digest 2026-08-05 and 2026-08-06 both call this out as top concern. Each subconscious run creates a new PR instead of converging; no automated daily signal fires when pile exceeds threshold. Moratorium history (runs 15-28) shows this pattern worsens without a pressure mechanism.
**Action:** Add Step 9H bash block to nightly SKILL.md: count open draft PRs with title matching pattern `subconscious`; if count > 3, post GH comment on the oldest open subconscious PR listing all open ones and requesting "merge one or close the rest." Log count daily.
**Impact:** Prevents future 14-day PR pile-ups. Converts silent backlog into daily pressure signal. Same pattern as Step 9F (staleness alert) applied to PR debt.
**Category:** operational/workflow

---

### Idea 3: Nexlify Score token-burn guard audit
**Evidence:** e0e9be6 (2026-08-06) ships `response_score.py` (151 lines) — new Claude-calling service computing response quality scores. Nightly reviewed it as MEDIUM risk, checked client_id, cross-tenant isolation, plan gating, and Pydantic validation — but did NOT check if it routes through `ai_usage_guard.py`. widget_guard.py precedent (run 94): unbounded resource caught before scale. At 3 tenants this is safe; at 50 tenants every widget response triggering a Claude scoring call could 2-3x monthly token burn.
**Action:** Read `backend/services/response_score.py` to verify: (1) is it called per-message or on-demand? (2) does it call through `ai_usage_guard` or bypass it? (3) does it have a task_budget or max_tokens cap? File GH issue with `code-health` label if Claude call is ungated.
**Impact:** Prevents unexpected token cost explosion at scale. Protects margins. Pattern established: all new Claude-calling services must route through ai_usage_guard.
**Category:** code_health

---

### Idea 4: Typed KB notes discovery prompt for existing tenants
**Evidence:** 4853c31 (2026-08-04) ships typed knowledge notes — tenants can type FAQs, pricing, policies directly in `KnowledgeSourcesPage.jsx`. This closes the highest-friction KB gap (file upload requirement). 3 existing tenants won't discover it without in-app notification. No "new feature" banner pattern exists in dashboard. Low discovery → low adoption → low KB coverage → lower AI chat quality.
**Action:** Add a one-time dismissible info banner at top of `KnowledgeSourcesPage.jsx`: "New: Type your FAQs, pricing, and policies directly — no file upload needed." Use localStorage-safe pattern (in-app preference via backend flag, not localStorage per CLAUDE.md rule #6). Dismiss state stored in `widget_configs` or equivalent per-tenant settings.
**Impact:** Existing tenants discover and use typed notes. Better KB coverage → better AI chat answers → improved satisfaction → reduced churn.
**Category:** customer_value

---

### Idea 5: Grandfathered plan gate audit across all feature flags
**Evidence:** 2869124 (git log --since 7 days) fixes AI Workforce gate — it checked `plan == "agent_os"` but missed grandfathered plans (enterprise, growth, autopilot, professional). This is a class of bug: gates that hardcode `agent_os` instead of checking the full grandfathered list. If one gate had this bug, others likely do. `ai_usage_guard.PLAN_BASELINE_TOKENS` and billing gates in backend/services/ may have the same pattern.
**Action:** `grep -rn 'plan.*==.*"agent_os"\|plan.*in.*\["agent_os"\]' backend/` — find all places checking for agent_os plan membership without including grandfathered plans. Cross-reference with fix pattern in 2869124. File GH issue for each gate missing the grandfathered inclusion.
**Impact:** Prevents grandfathered customers from hitting broken feature walls. Protects retention for highest-paying historical customers.
**Category:** code_health
