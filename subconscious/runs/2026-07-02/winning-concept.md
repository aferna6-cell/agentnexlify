# Winning Concept — Run 77 (2026-07-02)

## Recommendation

Add a file-location verification step to Phase 2 of `.claude/skills/subconscious/SKILL.md` so the subconscious greps for a function/symbol before concluding a feature is unimplemented based on a missing file path.

---

## Why This, Why Now

Runs 75 and 76 each recommended Zapier plan_status enforcement as unimplemented — a fix that shipped on 2026-06-13. The error: both runs searched for `backend/services/zapier_auth.py` (a file that does not exist), found nothing, and concluded the feature was unimplemented. The nightly on 2026-07-02 caught it by verifying the actual implementation at `backend/routers/zapier.py:121-128`. Two full debate cycles wasted. The same failure mode is visible again this run: `email_sequences.py` is NOT FOUND at `backend/services/email_sequences.py` (the path cited in run 41's governance note), yet the run 41 active_direction has been pending_approval for 33 days — likely stale.

A one-paragraph patch to the SKILL.md evidence phase prevents the next occurrence. It's AUTONOMOUS-EXECUTABLE (nightly review has been executing SKILL.md patches since run 40/43 precedent). It compounds: every future run benefits.

---

## Implementation Sketch

**Target file:** `.claude/skills/subconscious/SKILL.md` — Phase 2 (Gather Evidence) section.

**After the existing bash evidence commands, before the 200-word summary instruction, insert:**

```markdown
#### Active Direction Status Verification

When reviewing `active_directions` items to assess implementation status:

1. **Do NOT trust a file path in governance notes as ground truth.** File paths go stale after refactors.
2. **If a note specifies a file path, verify it exists first:**
   ```bash
   ls <expected_file_path>
   ```
3. **If the file does NOT exist, grep for the key function or symbol:**
   ```bash
   grep -r "<function_name>" backend/ --include="*.py" -l
   ```
4. **Only mark as unimplemented if grep returns zero results** — not if the expected path is absent.
5. **If grep finds an alternate path**, note the correct path, mark governance entry as stale, and update in Phase 6.
```

**Estimated diff:** ~15 lines added to SKILL.md.  
**No other file changes needed.**

---

## Governance Actions (Phase 6 — This Run)

These happen autonomously as part of run persistence — no human approval required:

1. **Mark Zapier active_directions (runs 75+76) as `implemented`** — fix shipped 2026-06-13 at `backend/routers/zapier.py:121-128`, GH #107 closed.

2. **Add `ai_human_handoff` to `frozen_ideas`** — 7 consecutive debate kills (runs 4, 21, 29, 38, debate kills in runs 62, 73, 74). Freeze threshold in governance.json is 3. Overdue.

3. **Mark `email_sequences.py` split (run 41) as `moot`** — `backend/services/email_sequences.py` does NOT exist. Original god-class may have already been split or renamed. Run 41's active_direction should not be tracked until the correct file path is identified.

4. **Mark widget-drift active_directions (runs 65/66/67) as `superseded`** — widget drift topic retired at run 70 (governance `widget_drift_topic_retired: true`). These entries are residual noise.

5. **Update `total_runs` to 77** and `last_run` to `2026-07-02`.

---

## What This Replaces

Run 76 active direction was Zapier de-scoped mandate (VOID per nightly 2026-07-02 correction).  
Run 77 winner is a meta-improvement to the subconscious evidence phase — the first "improve the improvement system" winner since the moratorium-sprint SKILL.md (run 24).

---

## Confidence: HIGH

Evidence is direct: two wasted runs with identical root cause, second instance (`email_sequences.py`) already visible in run 77 evidence. Fix is a SKILL.md addition with zero blast radius. Nightly can execute without human approval.

---

## Bonus Action

Move "Lead source analytics" from Open to Resolved in `docs/dev-knowledge/customer-gaps.md`. XS, 2-minute doc fix. Prevents future agents recommending already-implemented work. Run alongside winner.

---

## Run 78 Forecast

After Phase 6 corrections:
- Zapier (runs 75+76): implemented
- AI-to-Human Handoff (runs 4, 21, 29, 38): frozen
- Widget drift runs 65/66/67: superseded
- email_sequences run 41: moot (pending correct path identification)
- True pending: SMS Dashboard (2 items = 1 feature) + Widget Sync Guard (run 7)

True pending count = ~2 = exactly at max_pending_approvals (2). **Moratorium may lift for run 78** if SMS Dashboard ships via issue-to-pr-loop before next run. If it ships: pending = 1 < 2 = moratorium exits. Run 78 should check moratorium condition and, if lifted, recommend the first Medium-effort customer value feature.

---

## Run 78 Mandate

If the SKILL.md patch is NOT applied by run 78 check:
- Escalate: add explicit nightly directive to apply the patch (same mechanism as run 66 mandate for Step 9B).
- Note the `email_sequences.py` path mystery: run 78 should grep the codebase to either find the file's new location or confirm the split already happened, and update run 41's governance entry accordingly.
