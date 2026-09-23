# Run 127 — Winning Concept

**Winner:** Step 9E — Add 10-Day P0 Credential Expiry Escalation Tier
**Category:** Operational / Workflow Efficiency
**Carry count:** 7 (autonomous-executable since run 122)
**Status:** Recommend (task-prompt constraint: "Do NOT implement. Only recommend.")

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` checks credential rotation at the 76-day threshold (14-day warning window before 90-day expiry). It creates or updates a `credential-rotation` issue. But it has no P0 escalation tier.

**Result:** When AUTOPILOT_GH_TOKEN crossed into final 10 days (2026-09-22), no automated P0 issue fired. GH #893 was filed manually as a one-time workaround. Without Step 9E, every future credential entering its final 10 days will require the same manual intervention — or will silently reach zero days.

**Current state:** AUTOPILOT_GH_TOKEN expires **2026-10-02 (9 days)**. P0 threshold crossed 1 day ago.

---

## Evidence

- `grep -n "days_remaining\|P0\|<= 10" .claude/skills/nightly-commit-review/SKILL.md` → 0 P0-context hits, 0 days_remaining hits in Step 9E block (lines 277-300)
- Step 9G confirmed IMPLEMENTED by nightly-2026-09-23 (LOW-risk auto-fix) — KB recovery pipeline now has a working trigger
- GH #893 filed 2026-09-22 (P0 human notification, manual, one-time)
- Autonomous-executable mandate binding since run 122 (3rd consecutive carry, governance precedent runs 97-99/Step 9F)
- Step 9E parked run 126 for Step 9G (rotation winner) — Step 9G now done; Step 9E restored as winner
- Same SKILL.md channel as Steps 9F/9G/9I/9J/9K/9L — all implemented via this path
- Effort: S (~15 lines added to Step 9E block, same file, same edit pattern as prior steps)

---

## Proposed Fix

In `.claude/skills/nightly-commit-review/SKILL.md`, Step 9E block (lines 277-300), extend step 2 to compute `days_remaining` and add step 2b as a P0 sub-tier:

**Current Step 9E step 2 (lines 283-288) checks:**
```
For each credential row: parse "Last rotated" date field.
Compute days_since_rotation = (today - last_rotated_date).
Flag as approaching_expiry if days_since_rotation >= 76 (= 90 days - 14-day warning window).
```

**Add after `days_since_rotation` computation:**
```
Compute days_remaining = 90 - days_since_rotation.
If days_remaining <= 10 AND days_remaining >= 0:
  a. Search open GH issues with labels ["P0", "ops"] and title containing credential name:
     mcp__github__list_issues with labels: ["P0", "ops"], state: OPEN
  b. If NO matching P0 issue found for that credential:
     Create GH issue via mcp__github__issue_write:
       title: "P0: {credential_name} expires in {days_remaining} days — rotate now"
       body: credential name, last_rotated date, days_since_rotation, exact_expiry_date, rotation steps link, urgency note
       labels: ["P0", "ops", "human-action-required"]
  c. If matching P0 issue FOUND: add comment with updated days_remaining.
  Log: "Step 9E P0 ALERT: {credential_name} expires in {days_remaining} days — issue filed/updated"
```

**Add to step 4 (log result):**
```
"Step 9E: {N} credentials checked, {M} approaching expiry (>=76 days), {K} at P0 (<= 10 days), {J} unknown state"
```

---

## Expected Impact

1. Nightly run on 2026-09-24 will fire P0 for AUTOPILOT_GH_TOKEN (8 days remaining)
2. Dedup guard prevents duplicate P0 issues across consecutive nightly runs
3. Every future credential entering final 10 days auto-files a P0 — permanent, no human memory required
4. Compounds: as credential count grows (Supabase, Railway, Twilio, etc.), each gets the same automatic P0 coverage

---

## Scope

- File: `.claude/skills/nightly-commit-review/SKILL.md`
- Section: Step 9E (lines 277-300 approximate)
- Change: ~15 lines added to step 2 block; step 4 log line extended
- Blast radius: zero (Step 9E only fires when credentials approaching expiry; P0 sub-tier only fires within final 10 days; dedup guard prevents noise)
- No new dependencies (mcp__github__list_issues + mcp__github__issue_write already used by Steps 9D/9F/9G)

---

## Why This Run (vs Prior 6 Carries)

Run 126 rotated winner to Step 9G (broken KB trigger, 3-carry). Step 9G is now confirmed IMPLEMENTED (nightly-2026-09-23). Step 9E is the next systemic fix with concrete urgency: AUTOPILOT_GH_TOKEN at 9 days, P0 threshold crossed, GH #893 was manual-only. The task-prompt constraint is the only blocker; implementation takes <10 minutes; human review is the intended path.

**AUTOPILOT_GH_TOKEN expires 2026-10-02. Human action required. See GH #893.**
