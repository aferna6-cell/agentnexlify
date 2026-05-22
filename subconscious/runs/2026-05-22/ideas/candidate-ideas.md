# Candidate Ideas — 2026-05-22 (Run 30)

## Evidence Digest

Zero production commits day 17 (since 72f8204, May 5). All recent commits are ops/subconscious/nightly-review logs. Items A/B/D (moratorium sprint) all MISSING confirmed by direct filesystem check. Nightly review working correctly — escalation comment posted to GH #169 today. Run 29 winner (AI-to-Human Handoff GH issue, ~5 min) NOT done — no new GH issues in last 24h commits. 8 consecutive non-implementations across runs 22-29, covering effort ranging from 5 min to 40 min. Root cause signal: recommendations are read in one session, not executed in the same session. Bug patterns 2379 lines, no new bugs in 3 days. KB 23 days stale.

---

### Idea 1: Add Interactive Approval Gate to Subconscious Phase 7

**Evidence:** Runs 22-29 show 8 consecutive non-implementations despite effort ranging from 5 min to 40 min. Run 22 had human present, 5-min task, not done. Run 29 had human present, 5-min task, not done. The pattern points to a structural gap: the approval gate (Phase 7 → "do it" / "reject") is outside the subconscious session. After the run produces artifacts, the human would have to come back to a different session to say "do it." That second session rarely happens. Nightly review has demonstrated autonomous SKILL.md modification capability (7985fbb moratorium-sprint, 2ce31b2 SKILL.md escalation protocol) — this recommendation is within its execution envelope.

**Action:** Modify `.claude/skills/subconscious/SKILL.md` Phase 7 (Report) to append an Approval Gate block:
```
### Approval Gate

Winner: {one sentence}
Effort: {S/M/L} | Category: {category}

Approve? Type one of:
- "do it"  → execute winning-concept.md implementation sketch in this session
- "reject [reason]" → log rejection, update governance.json
- "defer"  → mark pending_approval, end session normally

If S-effort and human is present: default to "do it" unless a reason exists not to.
```
Also add `auto_approve` check to Phase 5 synthesis: if S-effort AND moratorium-exempt, prompt for immediate approval.

**Impact:** Every future subconscious run ends with an active decision point rather than passive artifact writing. S-effort items can be executed and committed in the same 20-minute session. Eliminates the "read, don't act" pattern that has broken 8 consecutive runs. ~15 min implementation.

**Category:** workflow

---

### Idea 2: Create AI-to-Human Handoff v1 GH Issue as Phase 8B Subconscious Artifact

**Evidence:** Run 29 winner (same item), NOT done. Run 21 winner (same item), NOT done. AI-to-Human Handoff = Critical in customer-gaps.md, all 7 verticals, day 36. Infrastructure confirmed (conversations table, webhooks, Twilio, Resend). Full issue body already written in `subconscious/runs/2026-05-21-pm/winning-concept.md §Step 1`. Moratorium-exempt (documentation, not code). GitHub issues are artifacts of the planning process — the subconscious already writes .md artifacts; writing a GH issue is the same category at a different URL.

**Action:** Add a Phase 8B step to the subconscious: "For moratorium-exempt documentation artifacts, create the GH issue using mcp__github__create_issue as part of the run." Then execute Phase 8B now using the body from run 29 winning-concept.md.

**Impact:** Resolves runs 4, 21, 29 (all targeting the same gap). Unlocks issue-to-pr-loop autonomous pickup of scaffolding. Converts 36-day stale recommendation into a tracked GH ticket. ~5 min.

**Category:** customer_value

---

### Idea 3: Invoke /moratorium-sprint

**Evidence:** Items A/B/D MISSING day 17. moratorium-sprint SKILL.md exists (7985fbb). Sprint is ~40 min and exits the moratorium (pending 5→2). All 3 items have pre-written implementation sketches. This has been recommended in runs 24-29 (6 times as primary winner, 2 more as active direction). Nightly review confirmed Items A/B/D still MISSING this morning.

**Action:** Invoke `/moratorium-sprint` in current session — executes Item A (check_project_invariants pre-commit, ~5 min), Item B (widget sync script, ~15 min), Item D (CI eval workflow, ~20 min), opens draft PR.

**Impact:** Moratorium exits (pending 5→2). All 17 days of stalled recommendations resolve. Restores normal free-choice subconscious operation.

**Category:** workflow

---

### Idea 4: Merge Safe Dependency PRs (#102/#103/#164/#171)

**Evidence:** Morning digest logs have mentioned these 4 safe dependency PRs across 5+ consecutive runs. PRs aging 24+ days. Dependency updates: no logic changes, only version bumps. Independent of moratorium. Mentioned as "bonus action" in runs 25-29 but never executed.

**Action:** Merge the 4 safe dependency update PRs in the current session (~5 min, one `gh pr merge` each).

**Impact:** PR queue drops from 20 to 16. Demonstrates system can make concrete progress even during moratorium. Zero regression risk (no logic changes). Eliminates stale PR debt.

**Category:** operational

---

### Idea 5: Diagnose the Implementation Gap in bottleneck-diagnosis.md

**Evidence:** 17 days, 8 consecutive non-implementations. Even 5-minute tasks haven't been done. This is not a time/effort problem — it's a decision-context problem. The subconscious has no record of WHY recommendations aren't being invoked. Future runs lack diagnostic data.

**Action:** Write `subconscious/state/bottleneck-diagnosis.md` with 3 hypotheses: (a) approval gate is outside session, (b) moratorium backlog creates overwhelm paralysis, (c) human is using subconscious as capture system not action system. Propose a test for each hypothesis.

**Impact:** Creates searchable record. Names the bottleneck. Forces a decision: is the subconscious serving its purpose, or does the loop need redesign? ~10 min effort.

**Category:** workflow

---

## Ranking by Impact

1. Idea 1 (Interactive Approval Gate) — structural, benefits every future run
2. Idea 3 (/moratorium-sprint) — highest leverage, exits moratorium
3. Idea 2 (Handoff GH Issue as artifact) — customer value, moratorium-exempt
4. Idea 5 (Bottleneck diagnosis) — meta, useful but second-order
5. Idea 4 (Safe dep PRs) — low ROI but achievable
