# Candidate Ideas — 2026-05-21-pm (Run 29)

## Evidence Digest

Run 28 completed this morning (2057df2). Governance audit applied: true pending 12→4 (runs 4, 20, 21, 28). Items A/B/D all MISSING confirmed. Moratorium day 16. Zero production commits day 16. Nightly review 2026-05-21 declined run 27 hard mandate on governance grounds — interactive-only path confirmed. Morning digest reveals 20 open PRs: 4 safe dep merges (24d), stale sprint blocker #80 (onboarding v2, 28d), stale memory hygiene PRs #71-74 (31d). GH #169 receiving daily escalation comments. AI-to-Human Handoff (run 4) now 35 days pending, Critical gap all 7 industries. Run 21 recommended the GH issue (May 17, not done). KB 22 days stale. No production bugs.

---

### Idea 1: Invoke /moratorium-sprint (Items A+B+D, ~40 min)

**Evidence:** moratorium-sprint SKILL.md ready (7985fbb). Items A/B/D all MISSING (confirmed). True pending = 5 (run 29 adds 1). After sprint: pending = 2 = moratorium exits. Run 28 governance audit made exit path visible as never before.

**Action:** Invoke `/moratorium-sprint` in current session. Skill executes: (A) wire check_project_invariants.py into pre-commit as Check 10 (~5 min), (B) create scripts/check-widget-sync.sh + pre-push hook + CLAUDE.md Invariant #4 fix (~15 min), (D) create .github/workflows/lead-qualifier-eval.yml (~20 min). Opens draft PR.

**Impact:** Moratorium exits. All future subconscious work becomes free-choice again. Unlocks AI-to-Human Handoff, Zapier security fix, pre-commit-guard-add skill. Highest leverage-per-session of any option.

**Category:** workflow

---

### Idea 2: Write AI-to-Human Handoff v1 GH Issue (~5 min, docs-only)

**Evidence:** customer-gaps.md: AI-to-Human Handoff = Critical, all 7 industries, Medium effort. Run 4 (2026-04-16, day 35): first subconscious winner, pending_approval for 35 days. Run 21 (2026-05-17) recommended writing this GH issue — not done. Run 20 backlog explicitly authorized parallel track: "Create GH issue with full implementation sketch for AI-to-Human Handoff v1. Parallel track explicitly authorized." Infrastructure confirmed: conversations table, webhooks, Twilio, Resend all exist. issue-to-pr-loop can pick up from GH issue once created.

**Action:** Write GH issue using mcp__github__create_issue with full implementation sketch: explicit trigger flow (human types "talk to someone"), route to webhook + Twilio SMS to owner, fallback to email, lead status → "needs_follow_up". ~5 min. Moratorium-exempt (docs/planning, not code).

**Impact:** Converts 35-day stale Critical gap into autonomous pickup by issue-to-pr-loop. Run 4 + Run 21 both become "implemented" state (GH issue created). Does not depend on 40-min sprint window. Highest customer-value action that's moratorium-exempt.

**Category:** customer_value

---

### Idea 3: PR Board Triage — Merge Safe Deps + Decision on #80 (~15 min)

**Evidence:** Morning digest 2026-05-21 lists 20 open PRs. Four are safe to merge now: #102 (youtube-transcript-api, 24d), #103 (python-multipart, 24d), #164 (@playwright/test 1.59→1.60, 10d), #171 (@typescript-eslint 8.58→8.59, 3d). PR #80 (feat: onboarding-v2 Week 1 foundation, 28d, labeled "SPRINT BLOCKER") needs decision before moratorium exits to avoid creating a dirty state. PRs #71-74 (31d, memory hygiene + Zapier docs) cluttering board.

**Action:** Merge #102/#103/#164/#171 (5 min, automated dep bumps, safe). Triage #80: review state and either (a) merge if functionally complete, (b) convert to regular PR if close, or (c) close and re-create clean. Archive/close #71-74 or merge (docs only, 31d stale).

**Impact:** Board drops from 20 to ~12 PRs. Moratorium exit sprint runs into clean state. #102/#103 close security exposure from outdated deps. ~15 min total.

**Category:** operational

---

### Idea 4: KB Emergency Recompile (~10 min, if SUPABASE_ACCESS_TOKEN available)

**Evidence:** Morning digest 2026-05-21 KB status: "Last compile: 2026-04-29 (no cron activity since). 98 wiki articles. Embedding backlog exists (4 articles pending reindex via scripts/reindex_contextual.py once SUPABASE_ACCESS_TOKEN present)." KB has been stale 22 days. New raw/ articles accumulated. KB staleness degrades tenant-facing AI response quality as widget uses KB for context.

**Action:** Run `bash scripts/daily/kb-autopopulate.sh` then `python3 scripts/reindex_contextual.py` (if SUPABASE_ACCESS_TOKEN available). Promotes raw/ articles to wiki/, rebuilds embeddings. Freshens tenant AI responses.

**Impact:** Fresh KB improves response quality for all tenants. 22-day staleness = 22 days of potentially outdated widget answers. Low effort if token available.

**Category:** operational

---

### Idea 5: Create pre-commit-guard-add Skill

**Evidence:** Run 24 parking lot: "pre-commit-guard-add skill (workflow improvement)." Item A has been pending 5+ sprints — the activation energy for adding a pre-commit check is 3 lines plus knowing which check number to use. A skill reduces this to one command. Skill discovery 2026-05-18 report listed it as a viable improvement. moratorium-sprint SKILL.md (run 24 winner) already proved the autonomous-implementation pattern works for skill files.

**Action:** Create `.claude/skills/pre-commit-guard-add/SKILL.md` — skill that reads current pre-commit hook, identifies highest check number, adds a new check block. Future additions to pre-commit are one command.

**Impact:** Reduces pre-commit addition effort from "read 225-line hook, find right number, add block" to `/pre-commit-guard-add <script>`. Reusable indefinitely. Moratorium-exempt (new skill file). ~15 min.

**Category:** workflow
