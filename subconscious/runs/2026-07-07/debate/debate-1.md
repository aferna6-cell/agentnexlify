# Debate 1: Add `ai-ready` Label to GH #385 (SMS Compliance Dashboard)

**Verdict: SURVIVES → WINNER**

---

## Opening Case

GH #385 exists (filed 2026-07-01) with full spec, paste-ready code reference, and acceptance criteria. Missing: `ai-ready` label. Without it, issue-to-pr-loop never picks it up. The governance run_81_mandate explicitly required: "verify GH issue exists and is ai-ready labeled." Mandate fired — issue exists but label absent. Adding one label is XS autonomous action that unblocks 12/12 council score customer value.

---

## Challenge 1: This is a meta-action, not a real improvement

Adding a label doesn't ship code. The SMS Dashboard could still sit unimplemented after the label is added if issue-to-pr-loop has any failure mode.

**Defense:** The subconscious is a recommendation layer. Its job is to identify and unblock, not to implement. The real blocker is the missing label — not missing code (code is paste-ready in run 74). Adding `ai-ready` turns a dormant GH issue into an actively-queued autonomous task. If issue-to-pr-loop succeeds, this XS action delivers a 12/12-score feature with zero human coding.

The improvement here IS the channel activation. The subconscious's highest-leverage action is removing friction from autonomous systems, not doing the implementation itself.

---

## Challenge 2: Issue-to-pr-loop might not pick it up anyway — it may be broken or stalled

**Defense:** Issue-to-pr-loop is an established skill (`.claude/skills/issue-to-pr-loop/SKILL.md`). GH #385 has all the metadata the loop needs: labels for layer (backend, frontend), full spec in body, paste-ready code reference. If the loop fails after label is added, that's a separate problem — one that becomes visible and diagnosable. Today the issue is invisible to the loop. Visibility is step 1.

---

## Challenge 3: The SMS Dashboard is medium-risk (new API + frontend). Autonomous implementation could introduce bugs.

**Defense:** The issue-to-pr-loop opens a DRAFT PR for human review before merge. It doesn't auto-merge. Adding `ai-ready` queues autonomous implementation of a draft PR, not a direct commit to main. Human review gate remains intact. The risk is exactly the same as any other PR review — not eliminated but managed.

---

## Challenge 4: Run 80 already forecast this as the run 81 winner — running the same recommendation twice is low-value.

**Defense:** Run 80 forecast said "verify GH issue exists and is ai-ready labeled." The verification was not done by run 80 (no tool calls available at time of that run). This run actually checked and found the gap. Finding a gap and fixing it is not "running the same recommendation twice" — it's executing on the mandate. The value is the label add, not the recommendation.

---

## Verdict: SURVIVES — WINNER

- Governance-mandated verification found a real gap (missing `ai-ready` label)
- XS autonomous action with zero moratorium impact
- Highest downstream value: unblocks 6-week-old 12/12-score feature
- Zero risk (reversible, no code change)
- Consistent with governance forecast from run 80
