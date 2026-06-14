# Improvement Backlog — 2026-05-17 (Run 21)

## Active

### Winner: Run 21
**Create GH issue with full implementation sketch for AI-to-Human Handoff v1**
- Oldest pending item (31 days), Critical gap all 7 industries
- Parallel track authorization: run 20 backlog explicitly approves
- Implementation sketch in winning-concept.md §Step 1
- ~1.5-2 day implementation once GH issue is approved
- Labels: `customer-value`, `medium-effort`, `p0`, `moratorium-parallel-track`

### Moratorium items (clear these — ~50 min total)
All 4 have pre-written implementation sketches in subconscious/runs/2026-05-15-pm/winning-concept.md:

| Run | Item | Days pending | Effort |
|-----|------|-------------|--------|
| 19 | SKILL.md Moratorium Escalation Protocol | 1 | ~10 min |
| 8 | Wire check_project_invariants.py into pre-commit | 22 | ~5 min |
| 7 | Widget 3-Copy Sync Guard (scripts/check-widget-sync.sh) | 23 | ~15 min |
| 14 | Wire lead qualifier eval to CI | 12 | ~20 min |

Implementing all 4: pending drops 6→2 (only runs 4+21 remain).

### Run 20 governance mandate (still unfulfilled)
- Reduce governance.json max_pending_approvals 3→2
- Create GH milestone "Moratorium Exit Sprint" with 4 S-effort issues
- Note included inside run 21 GH issue body (moratorium context section)

---

## Parking Lot (survived debate / deferred)

**After moratorium exits or moratorium items auto-implemented:**

- **Zapier API key plan_status enforcement** (GH #107, ROI 2.5, HIGH security) — First post-moratorium
  code fix. `backend/services/zapier_auth.py::_get_api_key_client` resolves keys without plan_status
  check. Add `plan_status IN ('active','trialing')` filter + regression test.

- **Fix email_sequences N+1 queries** (GH #112, ROI 2.3) — list_enrollments: 1001 queries per
  1000 enrollments. Bulk .in_() fix.

- **Restart autopilot-issue-loop.yml** — Loop confirmed dormant (zero production commits last 14d).
  Restarting it enables auto-implementation of ai-ready labeled issues. Conditional on run 22
  if run 21 not implemented.

- **Stripe billing smoke tests** (ROI 2.2) — 821f660 touched 16 billing files, zero QA planned.

- **Bug-patterns.md split by month** (ROI 1.8, 2379 lines) — Auto-logger writes to monolithic file.
  Split into monthly files + INDEX.md.

- **Extract _process_pending_sends()** (GH #113, ROI 1.8) — 120-line duplication in email_sequences.

- **Onboarding V2 characterization tests** (ROI 1.7) — Write before first sprint issue.

- **California AI companion disclosure audit** (ROI 1.6) — SB 243 + companion chatbot law in effect.

---

## Rejected This Run

- **P0 GH Issue as standalone winner** — WEAKENED. Run 20 governance mandate fires, but pure meta-
  escalation as 4th consecutive standalone meta recommendation adds marginal force. Mandate honored
  inside run 21 GH issue body (moratorium context). Mechanism preserved, not abandoned.

- **ai-ready tags for autopilot loop** — KILLED. Loop confirmed dormant: zero issue-to-pr-loop
  commits in last 14 days (git log). Tagging issues for a dormant loop produces no execution force.
  Promote when loop activity confirmed in git log.

---

## Questions for Next Run (Run 22)

1. **Was run 21 GH issue created (AI-to-Human Handoff sprint planning)?** Check GH issues for
   title containing "AI-to-Human Handoff" or "Handoff v1". If YES → free-choice for implementation.
   If NO → run 22 governance action: restart autopilot loop + tag S-effort items as ai-ready.

2. **Did any moratorium S-effort items get implemented since run 21?** Count pending_approval items:
   - pending ≤ 3 → moratorium exits; free-choice runs resume
   - pending = 2 (only runs 4+21) → final sprint needed on run 4

3. **Was governance.json max_pending_approvals updated 3→2?** Mandate from run 20, carried forward.
   Check config block. If still 3 → mandate carries to run 22.

4. **Is autopilot-issue-loop.yml now running?** `git log --oneline --grep="issue-to-pr-loop"
   --since="7 days ago"` — if any production commits appear, loop is active and ai-ready tagging
   becomes viable for run 22.

5. **Run 4 now 31+ days.** Any sprint allocation signal? Check GH for "handoff" in issue titles
   created after 2026-05-17. If none: the run 21 GH issue creation itself IS the sprint signal.
