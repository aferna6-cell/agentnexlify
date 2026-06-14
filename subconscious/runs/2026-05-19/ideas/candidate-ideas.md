# Candidate Ideas — Run 25 (2026-05-19)

## Evidence Digest (200 words)

**Key state change:** moratorium-sprint SKILL.md created by nightly review (commit 7985fbb, 2026-05-19) — first production-impactful commit in 14 days. Run 24 winner implemented without human action (autonomous loop). Skill exists, triggers wired, ready for invocation.

**Still unchanged:** 4 S-effort items pending (check_project_invariants pre-commit, widget sync guard, SKILL.md escalation protocol, CI eval workflow). All implementation sketches pre-written in subconscious/runs/2026-05-18/winning-concept.md. Zero production code commits 14 days.

**Skill discovery (2026-05-18):** proposed `pre-commit-guard-add` (new tool, 15-20 min saved per guard, historical 1-2/month cadence) and `dep-batch-merge` (4 aging PRs: #102/#103 21d, #163/#164 7d). Both are execution-layer patterns consistent with run 24's mechanism change.

**Customer gaps:** AI-to-Human Handoff = Critical, all 7 industries, 33 days pending. Zapier plan_status bug (issue #107) 25+ days open, security.

**Bug patterns:** No new bugs this week. Zapier #107 and email N+1 #112 open but tracked.

**Moratorium:** still active. pending=11 (10 pre-run + 1 run 24 added but now implemented). Governance.json needs correction: run 24 status should be `implemented`.

---

## Idea 1: Invoke /moratorium-sprint — Execute 4 S-Effort Items This Session

**Evidence:** moratorium-sprint skill created today (7985fbb). 4 S-effort items have pre-written implementation sketches at subconscious/runs/2026-05-18/winning-concept.md §Steps 1-4. User present in interactive session. No blockers. Script check_project_invariants.py PASSES. Widget copies confirmed in sync.

**Action:** Human invokes `/moratorium-sprint` in this or the next interactive session. Skill reads governance.json → loads 4 sketches → executes A (5 min), B (15 min), C (10 min), D (20 min) → opens draft PR against main. Total ~50 min.

**Impact:** pending 11→7 when PR merged. Moratorium exit path: after PR merged + 5 more resolutions → pending ≤ 2 → moratorium exits. Zero new file creation needed — tool is ready.

**Category:** workflow

---

## Idea 2: Create pre-commit-guard-add Skill

**Evidence:** Skill discovery 2026-05-18 proposed this as Skill #2. Pattern confirmed by history: every new bug class → new pre-commit check. Current cadence ~1-2 new guards/month. Each guard currently costs 15-20 min of context loading (read hook, find insertion point, format check, test). Run 22 winner (check_project_invariants) has been proposed 8 times in 7 runs — evidence that guard-adding is a recurring, high-friction task.

**Action:** Create `.claude/skills/pre-commit-guard-add/SKILL.md` — a skill that reads `scripts/hooks/pre-commit`, finds current check count, inserts new check in correct format, tests it, and commits. ~25 min effort.

**Impact:** 15-20 min saved per new guard, 1-2x/month recurrence. ~20 min/month in perpetuity.

**Category:** workflow

---

## Idea 3: Merge 4 Safe Dependency PRs

**Evidence:** Morning digest 2026-05-18 flagged 4 aging PRs as safe: #102 (youtube-transcript-api ≥1.2.4, 21d), #103 (python-multipart 0.0.26→0.0.27, 21d), #163 (@typescript-eslint/parser 8.58→8.59.3, 7d), #164 (@playwright/test 1.59.1→1.60.0, 7d). All classified as patch/dev-only — safe to merge per prior analysis. Independent of moratorium.

**Action:** Merge all 4 via `mcp__github__merge_pull_request`. ~5 min. No code to write.

**Impact:** Reduces dep drift, eliminates aging PR noise from morning digest. Security surface reduced (youtube-transcript-api 1.2.4 has a patch fix).

**Category:** operational

---

## Idea 4: AI-to-Human Handoff v1 Feature Build (Escalate to Sprint)

**Evidence:** customer-gaps.md: AI-to-Human Handoff = Critical, all 7 industries. Pending 33 days (run 4, 2026-04-16). Infrastructure exists: conversations table, webhooks router, Twilio, Resend. Run 21 recommended creating a GH issue for this; that issue was never created. This is the oldest unresolved CRITICAL gap.

**Action:** Create GH issue with full implementation sketch for AI-to-Human Handoff v1 (explicit trigger only). Issue body: user story, API contract, files to change, test cases. Routes to issue-to-pr-loop for autonomous implementation.

**Impact:** Clears oldest CRITICAL customer gap. ~1.5-2 day implementation. All 7 industry verticals benefit. Competitive moat vs GoHighLevel.

**Category:** customer_value

---

## Idea 5: Governance Cleanup — Mark Run 24 Implemented

**Evidence:** governance.json lists moratorium-sprint skill (`date: "2026-05-18-pm"`) with `status: "pending_approval"`. Nightly review created the file today (7985fbb). The status is stale — it should be `implemented`. `implementation_lag_warning.runs_pending_approval` reads 10 but is now 9 (run 24 implemented). Counter drift underreports real state.

**Action:** Update governance.json: set run 24 status → `implemented`, decrement `runs_pending_approval` 10→9, add `implementation_lag_warning.governance_correction` note.

**Impact:** Accurate governance state. Next run starts with correct pending count. Prevents compounding miscounts.

**Category:** operational
