# Ideas — 2026-07-29 (Run 103)

**Evidence sources:** nightly-commit-review-2026-07-28.md, nightly-commit-review-2026-07-29.md, governance.json run_103_mandate, docs/skill-discovery/2026-07-27.md, KB log freshness check, PR #577 comment history, subconscious/runs/2026-07-28-pm/improvement-backlog.md

---

## Mandate check results

| Item | Status | Finding |
|---|---|---|
| god-class-splitter SKILL.md updated | ✓ DONE | grep returned 2 matches (`backward-compat re-exports`, `patch targets`) |
| feature-docs-trio SKILL.md created | ✗ MISSING | `ls .claude/skills/feature-docs-trio/SKILL.md` → not found |
| feature-build/SKILL.md references feature-docs-trio | ✗ MISSING | grep returned 0 |
| PR #577 CCR Routine warning posted | ✓ DONE | Comment posted 2026-07-28T22:16:38Z (run 102 bonus action) |
| KB freshness vs 7-day threshold | ✓ UNDER (6 days) | Last CCR run: 2026-07-23. Today: 2026-07-29. **Threshold tomorrow (2026-07-30).** |
| GH #605 ai-ready label | ✗ MISSING | 0 labels on issue |

---

## Candidate ideas (5)

### Idea 1: Step 9G CORRECTED — CCR Routine Health Check
**Category:** operational  
**Effort:** XS (~15 pseudocode lines in SKILL.md)  
**Evidence:** KB staleness is 6 days as of today — hits 7-day threshold **tomorrow** (2026-07-30). Step 9F will fire an alert. Without Step 9G CORRECTED in place, no follow-through health check occurs. Original Step 9G (gh workflow run) is obsolete (CCR Routine is the active path; GH Actions broken #500). Corrected design documented in run 102 winning-concept.md and PR #577 comment (2026-07-28). Channel proven: Steps 9B–9F all landed via this SKILL.md bash block pattern.

**Design:** After Step 9F fires (days_stale > 7), check `git log --since="48 hours ago" --oneline -- knowledge-base/`. If no recent KB commits AND KB stale > 7 days → comment on GH #403 "CCR Routine may be stalled." Distinguishes "KB stale and CCR working on it" from "KB stale and CCR genuinely down."

**Urgency: HIGH** — fires if not implemented before tomorrow's nightly.

---

### Idea 2: feature-docs-trio SKILL.md (2nd carry-forward)
**Category:** workflow  
**Effort:** S (~50 lines new SKILL.md + 3 lines in feature-build/SKILL.md)  
**Evidence:** Run 101 winner. 3 occurrences in 7 days (717c7f3, 14ebe8e, d50d1e8). 30-45 min saved per feature. MISSING after 2 subconscious runs (run 101 = 1st proposal, run 102 = 1st carry-forward, run 103 = 2nd carry-forward). Direct implementation fires at run 104 (3rd carry-forward rule). Feature velocity high: graph runtime, router semantics, route introspection, sweeper all shipped in the last 7 days. Each shipped without docs = recoverable overhead accumulating.

**Urgency: MEDIUM** — direct implementation at run 104, not today.

---

### Idea 3: GH #605 ai-ready label + issue body diagnostic
**Category:** operational  
**Effort:** XS (single API call)  
**Evidence:** Run 102 backlog Bonus B. The sweeper (8e78f5b, 2026-07-29) fixes crash-stranded runs, but GH #605 (the underlying incident issue) has 0 labels. Adding `ai-ready` enables issue-to-pr-loop to pick up related improvements. Adding a comment confirming sweeper closed the incident helps future reviewers close the loop.

**Urgency: LOW** — no time pressure, no user impact.

---

### Idea 4: Step 9F diagnostic text correction
**Category:** operational  
**Effort:** XS (~5 lines edit)  
**Evidence:** Step 9F comment body still says "Check ANTHROPIC_API_KEY in GitHub Actions secrets — may need rotation." But the CCR Routine (cloud session) is the active KB autopopulate path, not GH Actions. The diagnostic text will mislead the owner when Step 9F fires (tomorrow if KB goes stale). Updating to "Check CCR Routine ('KB Auto-Populate') at claude.ai/code" prevents a wasted debugging cycle.

**Urgency: MEDIUM** — Step 9F fires tomorrow, so stale diagnostic text will be seen then.

---

### Idea 5: widget-ai-marker-add SKILL.md
**Category:** workflow  
**Effort:** S (~70 lines new SKILL.md)  
**Evidence:** skill-discovery-2026-07-27 proposed this as Idea 2. 2 occurrences (HANDOFF_REQUESTED historical, SHOW_BOOKING_PANEL e9b4972 2026-07-23). Most error-prone step: byte-identical sync across 3 widget copies. Pattern is roughly monthly. Low urgency compared to operational items.

**Urgency: LOW** — no current active work blocked by its absence.

---

## Top 3 for debate

1. **Step 9G CORRECTED** (Idea 1) — HIGH urgency, proven channel, time-boxed (tomorrow)
2. **feature-docs-trio 2nd carry-forward** (Idea 2) — MEDIUM urgency, carry-forward pattern
3. **Step 9F diagnostic text correction** (Idea 4) — MEDIUM urgency, also fires tomorrow
