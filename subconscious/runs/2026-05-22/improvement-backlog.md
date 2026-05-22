# Improvement Backlog — 2026-05-22 (Run 30)

## Active

### NEW: Add Interactive Approval Gate to Subconscious Phase 7
S-effort (~15 min). Modify `.claude/skills/subconscious/SKILL.md` to append approval prompt at end of Phase 7 Report. Nightly review can execute autonomously (SKILL.md modification, LOW-risk additive).
Full sketch: `subconscious/runs/2026-05-22/winning-concept.md §Implementation Sketch`

### Standing: Invoke /moratorium-sprint (unchanged from run 28/29)
Items A+B+D, ~40 min. Pending 5→2 = moratorium exits. moratorium-sprint SKILL.md ready (7985fbb). Zero blockers.
Sketch: `subconscious/runs/2026-05-21/winning-concept.md`

---

## Parking Lot (survived debate but not chosen as run 30 primary winner)

- **Create AI-to-Human Handoff v1 GH Issue** (5 min, moratorium-exempt, Critical 36d) — first target for the new Approval Gate once it's live. Body already written in `subconscious/runs/2026-05-21-pm/winning-concept.md §Step 1`. Resolves runs 4/21/29 on creation.
- **Merge safe dep PRs #102/#103/#164/#171** (~5 min, any time, independent, zero regression risk)
- **KB recompile** (~10 min, 23 days stale — check SUPABASE_ACCESS_TOKEN availability first)
- **pre-commit-guard-add skill** (workflow, parking lot from run 24, promote post-moratorium)

---

## Rejected This Run

- **/moratorium-sprint as run 30 winner** — WEAKENED. 9th consecutive recommendation in winner slot adds no new information. Remains standing highest-priority action in active_directions. Not killed — demoted from winner slot only.

---

## Questions for Next Run

1. Was the Approval Gate added to SKILL.md? If yes by nightly review: confirm it fires correctly on next interactive run. If no: re-evaluate whether nightly review is the right execution path for this item.

2. If Approval Gate is live on run 31: the Phase 7 prompt should surface the AI-to-Human Handoff GH Issue as the first fast-track item. Did the human type "do it"? Did the GH issue get created?

3. Has /moratorium-sprint been invoked? If moratorium exits before run 31: free-choice mode. First post-moratorium winner candidates: Zapier plan_status enforcement (GH #107, ROI 2.5, security), email N+1 fix (GH #112, ROI 2.3), KB recompile.

4. Is SUPABASE_ACCESS_TOKEN available? If yes: run KB recompile as bonus action alongside any run 31 winner.
