# Candidate Ideas — Run 27 (2026-05-20-pm)

**Moratorium status:** Active, day 15. Items A, B, D confirmed missing.
**Run 26 governance note fires:** "If not invoked by run 27: recommend triggering sprint from nightly review."
**Human:** Present in interactive session (triggered this run manually).

---

### Idea 1: Invoke /moratorium-sprint NOW — 3 Items, Interactive Session (~40 min)

**Evidence:**
- Items A (check_project_invariants pre-commit), B (check-widget-sync.sh), D (lead-qualifier-eval.yml) all confirmed MISSING on direct filesystem check
- moratorium-sprint SKILL.md created by nightly review 2026-05-19 (7985fbb) — tool ready
- Human is present in this interactive session (triggered subconscious manually — highest engagement signal)
- Sprint now 3 items only (down from 4 — Item C done autonomously 2026-05-20)
- moratorium-sprint SKILL.md handles context loading automatically (15-20 min previously wasted)
- Governance note from run 26: hard escalation fires run 28 if sprint not invoked this session

**Action:** Type `/moratorium-sprint` or "execute pending" in this session. Skill reads governance.json → executes Items A, B, D → opens draft PR → pending 9→6 when merged.

**Impact:** Draft PR opens. One human merge = pending 9→6. Moratorium exit path begins. Items A (run 8, 25 days), B (run 7/15, 26 days), D (run 14, 15 days) cleared.

**Category:** workflow

---

### Idea 2: Authorize Nightly Review to Execute Items A + D (Autonomous Path)

**Evidence:**
- Nightly review has proven autonomous execution: moratorium-sprint SKILL.md (7985fbb, 2026-05-19) + Moratorium Escalation Protocol (2ce31b2, 2026-05-20) — 2 consecutive implementations
- Items A (3 additive lines to scripts/hooks/pre-commit) and D (new .github/workflows/lead-qualifier-eval.yml) both qualify as LOW-risk additive changes
- Run 26 governance note mandates: "If not invoked by run 27: recommend triggering sprint from nightly review"
- Item B (check-widget-sync.sh + pre-push hook) has slightly higher blast radius — keep for human-supervised sprint
- Eliminates human-action gap that has stalled sprint for 2+ interactive sessions

**Action:** Update nightly-commit-review SKILL.md step 9B to authorize Items A and D as autonomous implementations (using pre-written sketches from subconscious/runs/2026-05-18/winning-concept.md §Steps 1,4).

**Impact:** Items A and D done autonomously within 24 hours. Pending 9→7. Item B still needs human action. Partial moratorium progress without requiring interactive session.

**Category:** workflow

---

### Idea 3: Merge 4 Safe Dependency PRs (#102, #103, #164, #171)

**Evidence:**
- Morning digest 2026-05-20 explicitly flagged as SAFE to merge (no testing needed): #102 (youtube-transcript-api, 23d), #103 (python-multipart patch, 23d), #164 (@playwright/test minor, 9d), #171 (@typescript-eslint/parser patch, 2d)
- 15 total open PRs aging — dep debt accumulating
- These are independent of moratorium exit (different governance queue)
- ~5 min via mcp__github__merge_pull_request × 4

**Action:** Merge PRs #102, #103, #164, #171 using GitHub MCP. No testing required per morning digest assessment.

**Impact:** PR backlog 15→11. Deps current. No moratorium effect (subconscious pending_approvals unchanged).

**Category:** operational

---

### Idea 4: Create AI-to-Human Handoff v1 GH Issue (Oldest Pending Item)

**Evidence:**
- Run 4 winner (2026-04-16), 34 days pending — oldest active recommendation
- customer-gaps.md: Critical impact, all 7 industries, infrastructure exists (conversations table, webhooks, Twilio, Resend)
- Run 21 winner was this exact idea (create GH issue with implementation sketch) — not executed
- Morning digest lists this as open active issue context
- Conversations.py has 3 endpoints — no handoff route exists

**Action:** Create GitHub issue for AI-to-Human Handoff v1 with full implementation sketch. M-effort ~1.5-2 days. Parallel track explicitly authorized by run 20.

**Impact:** Oldest pending item gets an actionable GH issue. Unblocks post-moratorium first sprint. But doesn't reduce moratorium pending count (GH issue creation ≠ implementation).

**Category:** customer_value

---

### Idea 5: pre-commit-guard-add Skill (Parking Lot Promotion)

**Evidence:**
- Skill discovery 2026-05-18 ranked #2 after moratorium-sprint — 15-20 min saved per new pre-commit guard addition
- Pattern: every new bug class → new numbered check. Recurs 1-2x/month
- Implementation sketch pre-written in skill-discovery/2026-05-18.md §Proposed Skills §2
- Parking lot from runs 24, 25, 26 — "promote when moratorium exits"

**Action:** Create .claude/skills/pre-commit-guard-add/SKILL.md implementing the 9-step pattern.

**Impact:** 15-20 min saved per future guard addition. ~2-4 sessions/year benefit.

**Category:** workflow

**Note:** Moratorium still active — same disqualifier as runs 24-26. Promote to run 28 if moratorium exits.
