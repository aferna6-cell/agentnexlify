# Candidate Ideas — Run 24 (2026-05-18-pm)

## Evidence Summary (200 words)

Zero production commits day 13 (since 72f8204 May 5). Run 23 NOT implemented: all 4 sprint items still MISSING — check_project_invariants.py not in pre-commit, scripts/check-widget-sync.sh absent, .github/workflows/lead-qualifier-eval.yml absent, nightly-commit-review SKILL.md has zero Moratorium Escalation Protocol lines. Pending now 10 (runs 4, 7, 8, 14, 18-partial, 19, 20, 21, 22, 23). max_pending_approvals=2 (run 20 mandate already applied). Moratorium exit condition: pending ≤ 2.

**New signal today**: Skill discovery report 2026-05-18 explicitly proposed `moratorium-sprint` skill — the system's first self-generated proposal to automate sprint execution. 9 consecutive moratorium-mode runs + zero implementations confirms the bottleneck is *execution friction* (65 min multi-session effort to load context + make 4 edits), not approval friction alone. Morning digest: 4 safe dependency PRs aging 7-21 days (#163, #164, #102, #103). KB last compiled 13 days ago (4 slugs pending).

What changed: the system has now produced enough evidence (9 runs × ~15 min context load) to quantify execution friction. Tool creation is the mechanism shift.

---

## Idea 1: Create `moratorium-sprint` Skill
**Evidence:** Skill discovery 2026-05-18 explicitly proposed this. 9 consecutive moratorium runs (runs 15–23) all reached same conclusion: S-effort items ready but no command exists to execute them. Run 23 winning concept §After explicitly proposed a `/sprint` command. Each attempt takes 15-20 min of context loading before any execution begins.
**Action:** Create `.claude/skills/moratorium-sprint/SKILL.md`. Skill reads `governance.json` → filters `pending_approval` items with S-effort → locates their `winning-concept.md` sketches → executes items sequentially in a single session → opens draft PR. Single invocation replaces 65-min multi-session effort.
**Impact:** Execution friction eliminated. Recurs every moratorium cycle (already triggered twice). One-time S-effort investment (~20 min file creation). Converts recommendation-loop into execution-loop.
**Category:** workflow

---

## Idea 2: Merge 4 Safe Dependency PRs (#163, #164, #102, #103)
**Evidence:** Morning digest 2026-05-18: #163 (@typescript-eslint/parser patch, 7d), #164 (@playwright/test minor, 7d), #102 (youtube-transcript-api patch, 21d), #103 (python-multipart patch, 21d) — all flagged "Safe — merge." Skill discovery proposed `dep-batch-merge`. Aging deps create merge conflict risk daily. Safe to merge without testing.
**Action:** Recommend merging #163, #164, #102, #103 via GitHub MCP in next session. Independent of moratorium (external maintenance, not pending recommendation queue). Sketch: `mcp__github__merge_pull_request({...})` × 4.
**Impact:** 4 aging PRs cleared, merge conflict risk reduced, deps fresh. No production code modified.
**Category:** operational

---

## Idea 3: Moratorium Exit Sprint PR — again (run 23 echo)
**Evidence:** All 4 sprint items still MISSING. Same evidence as run 23. 10 pending items now vs. 9.
**Action:** Same as run 23: create branch moratorium-exit-sprint, 4 items, draft PR. Run 23 had the strongest-ever framing.
**Impact:** Pending 10→6 if approved. But identical to run 23 recommendation — 10th consecutive moratorium recommendation.
**Category:** workflow / code_health

---

## Idea 4: Create `governance-state-sync` Skill
**Evidence:** Skill discovery 2026-05-18 proposed this explicitly. governance.json corrected in runs 9, 16, 22 (wrong pending counts, stale statuses). Current governance state unverified — `implemented_unverified` entries from months ago may be stale.
**Action:** Create `.claude/skills/governance-state-sync/SKILL.md`. Skill cross-checks governance.json claims against codebase reality (grep for scripts, check git log for commits, verify files exist).
**Impact:** Eliminates governance drift. Each subconscious run starts with accurate state. Prevents wrong-direction recommendations based on stale data.
**Category:** workflow

---

## Idea 5: KB Reindex + Health Pass
**Evidence:** Morning digest: KB last compiled 13 days ago, 4 slugs pending embedding backfill. `npm run kb:health` → `npm run kb:lint` → `python3 scripts/reindex_contextual.py` when credentials available. kb-drift sweep today came clean — structure OK, embeddings stale.
**Action:** Schedule or recommend a KB reindex pass. Update HOT.md (500-token hot-cache). Verify 4 pending slugs are promoted to wiki.
**Impact:** KB query accuracy improves. kb-first rule gets fresher cache. Low effort, high passive value.
**Category:** operational
