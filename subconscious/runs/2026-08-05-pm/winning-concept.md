# Run 101 Winner — Step 9J: Accumulated-Issue Auto-Closer

AUTONOMOUS-EXECUTABLE

**Run:** 104 (2026-08-05-pm)
**Confidence:** HIGH
**Effort:** XS (~15 lines in Scheduled Task Prompt)
**Category:** Operational
**Execution channel:** nightly-commit-review SKILL.md-edit (proven: Steps 9B–9F all
implemented in 1 cycle each via this exact channel)
**Requires human approval:** Yes (same gate as all SKILL.md additions)
**Requires human action after merge:** No — autonomous once live

---

## Problem

Step 9D fires daily and may open a new `loop-health` GH issue when it detects a stalled
autopilot loop or stalled ai-ready issue. No nightly step ever closes prior open issues
with the same label. Result:

- Issue #633 (loop-health) — open, filed by nightly 2026-08-04
- Issue #635 (loop-health) — open, filed by nightly 2026-08-05
- Both OPEN simultaneously. A human cannot tell which is "current."

Same gap for `digest`-labeled issues:
- Issue #634 (digest) — open since yesterday, superseded by today's digest but never closed

GH issue list grows monotonically. Each nightly run adds to the noise instead of
maintaining a single authoritative "current state" issue per condition.

## Root Cause

No "close-before-open" primitive exists in any nightly step. Steps 9A–9G all open issues
or add comments but never close prior open ones with the same label. Standard practice
(GitHub Dependabot, Sentry) is to supersede old alerts when a new one opens.

## Fix

Add Step 9J to `.claude/skills/nightly-commit-review/SKILL.md` Scheduled Task Prompt.
Step 9J runs **before** Step 9D.

```
9J. (Accumulated-Issue Auto-Closer) Before Step 9D fires, clean up stale loop-health issues:
    Load mcp__github__ tools via ToolSearch (mcp__github__list_issues, mcp__github__issue_write,
    mcp__github__add_issue_comment).
    List open issues with label loop-health (state: OPEN):
      mcp__github__list_issues with labels=["loop-health"], state=OPEN, owner=aferna6-cell,
      repo=agentnexlify
    For each issue found (process oldest first — lowest issue number):
      a. Add comment via mcp__github__add_issue_comment:
         "Superseded by today's loop-health check (YYYY-MM-DD). Auto-closed to maintain
          single authoritative open issue per condition."
      b. Close via mcp__github__issue_write:
         state: CLOSED, state_reason: not_planned
    Log: "Step 9J: closed N prior loop-health issues before Step 9D"
    If no open loop-health issues found: log "Step 9J: no stale loop-health issues — skip"
```

~15 lines in Scheduled Task Prompt. Idempotent (if 0 open issues → no-op). GH history
fully preserved (closed ≠ deleted; searchable in GH with `is:closed label:loop-health`).

## Placement

In the Scheduled Task Prompt, insert "9J." immediately before "9D." The current sequence:

```
...
9D. (Issue-to-PR Loop Health Check) Check for stalled ai-ready issues and loop health:
```

Becomes:

```
...
9J. (Accumulated-Issue Auto-Closer) Before Step 9D fires, close all prior open
    loop-health issues ... [full step as above]
9D. (Issue-to-PR Loop Health Check) Check for stalled ai-ready issues and loop health:
```

Steps 9A–9C remain unchanged. The existing "9D." label is preserved (no renumbering).

## Why This Wins Over Alternatives

| | Idea A (9J) | Idea C (PR tombstone) | Idea E (merge reporter) |
|---|---|---|---|
| Evidence | 3 issues accumulating NOW | 5 PRs, cosmetic | PRs ignored (real) |
| Risk | Zero (closed = preserved) | HIGH (destroys PRs) | Low (comment noise) |
| Dependency | None | None | None |
| Reversible | Yes | No (PR deleted) | Yes |
| Root cause | Addresses directly | No | No |
| Effort | XS | XS | S |

## Expected Signal (Run 102 Mandate)

After Step 9J is live:

1. `loop-health` open issue count stays ≤ 1 (the fresh one from that night's 9D)
2. Step 9J log line present: "Step 9J: closed N prior loop-health issues"
3. GH #403 / loop-health closed issues show "Superseded by today's check" comments
4. Morning digest stops flagging accumulating loop-health issues

## What This Doesn't Fix

- The underlying stalled autopilot loop (Step 9D handles diagnosis and escalation)
- KB staleness (Step 9F alerts; Step 9G — still in PRs #625/#626 — would repair)
- PR debt (human decision required)

## Governance Addition

Add to `active_directions` in `subconscious/state/governance.json`:

```json
{
  "title": "Step 9J: Accumulated-issue auto-closer in nightly-commit-review SKILL.md (run 101 winner)",
  "date": "2026-08-05",
  "confidence": "HIGH",
  "status": "recommended",
  "autonomous_executable": true,
  "requires_human": false,
  "category": "operational",
  "moratorium_override": false,
  "source_run": 101,
  "effort": "XS",
  "evidence": "Issues #633 and #635 both open (loop-health label) as of 2026-08-05, both from consecutive nightly runs with no auto-close. Morning digest issue #634 also open from yesterday. 3 accumulating issues signal a systematic gap: no close-before-open primitive exists in any nightly step. Steps 9B-9F confirmed viable via SKILL.md-edit channel (all implemented in 1 cycle).",
  "action": "Add Step 9J sub-step to .claude/skills/nightly-commit-review/SKILL.md Scheduled Task Prompt, placed before Step 9D. Load mcp__github__ tools, list open loop-health issues (state=OPEN), for each: add 'Superseded' comment then close (state=CLOSED, state_reason=not_planned). Log result. ~15 lines.",
  "implementation_sketch": "subconscious/runs/2026-08-05-pm/winning-concept.md",
  "note": "Run 101 winner. AUTONOMOUS-EXECUTABLE via nightly SKILL.md-edit channel. Same class as Steps 9B-9F. Addresses close-before-open gap absent from all prior steps 9A-9G. Idempotent: 0 open issues → no-op. GH history preserved."
}
```

## Run 102 Mandate

1. Step 9J in SKILL.md? (grep 'Step 9J' — SHOULD PASS if this run's winner is approved)
2. Loop-health open issues ≤ 1?
3. Step 9J nightly log line: "closed N prior loop-health issues"?
4. Step 9G: still unmerged after 4 cycles? If yes and days-since-creation > 21 (2026-08-13):
   raise a P1 GH issue `subconscious-stalled` (tiered escalation — Idea E variant)
5. KB freshness: still stale? Manual trigger recommended via GH Actions UI
6. Agent OS tenant count: >5 (LoopHealthPage promote condition)?
