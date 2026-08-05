# Run 101 — 5 Candidate Ideas
Date: 2026-08-05-pm | Total runs to date: 100

## Evidence Summary

- **Step 9G absent from SKILL.md** — 4th consecutive cycle with no merge. 2 PRs open
  (#625, #626) but neither merged. KB 13 days stale (threshold: 7 days).
- **Loop health issues accumulating** — #633 and #635 both open (loop-health label),
  both from consecutive nightly runs with no close mechanism. Morning digest issue #634
  also open (digest label) from yesterday — same pattern.
- **10 open PRs** — 5 subconscious drafts, 3 Dependabot, 1 fastapi cap, 1 kb-drift.
  Morning digest top priority: merge/triage #629/#630/#631 (Dependabot, no blockers).
- **Typed KB notes shipped (#632, 2026-08-01)** — `POST /api/v1/kb/{tenant_id}/notes`
  endpoint live. Notes land in `tenant_kb_documents` with `source='note'`. Zero monitoring
  for tenant note staleness.
- **Nightly clean 3 consecutive days (Aug 3–5)** — codebase healthy, no bugs found,
  no issues filed. Major feature sprint (Phases 1–5, PWA, AI Workforce gate fix) landed
  cleanly.
- **Global KB 13 days stale** — Step 9F alerting but cannot repair. Step 9G would
  auto-repair but PRs unmerged.

---

## Idea A: Accumulated-Issue Auto-Closer (Step 9J)
**Category:** Operational
**Effort:** XS (~15 lines of nightly bash)
**Confidence:** HIGH
**Channel:** nightly-commit-review SKILL.md-edit (proven for Steps 9B–9F)

### What
Before Step 9D creates a new `loop-health` GH issue, close all prior open `loop-health`
issues with a "Superseded by today's check (DATE)" comment. Prevents monotonic
accumulation.

### Why
Step 9D fires daily and opens a `loop-health` issue when autopilot loop is stalled.
It never closes old ones. Issues #633 and #635 are BOTH open right now, both `loop-health`,
filed within 24h of each other. A human cannot tell which is current. Same gap exists
for `digest`-labeled issues (#634 open from yesterday). GH issue list becomes progressively
noisier each cycle with no signal about which issue is "live."

### Sketch
```
9J. (Accumulated-Issue Auto-Closer — runs before Step 9D)
    Load mcp__github__ tools via ToolSearch.
    List open issues with label loop-health (state: OPEN).
    For each found (oldest first):
      - Comment: "Superseded by today's loop-health check (YYYY-MM-DD). Auto-closed."
      - Close via mcp__github__issue_write (state: CLOSED, state_reason: not_planned)
    Log: "Step 9J: closed N prior loop-health issues"
    If none found: log "Step 9J: no stale loop-health issues — skip"
```

~15 lines in Scheduled Task Prompt. Idempotent. GH history preserved (closed ≠ deleted).

---

## Idea B: Typed KB Note Staleness Monitoring
**Category:** Customer Value
**Effort:** S
**Confidence:** MEDIUM (blocked by auth architecture)
**Channel:** New nightly bash step

### What
Post-#632, tenant notes (`source='note'`) can become stale (price change, policy update)
with no alert. Add a nightly Supabase query surfacing notes older than 30 days.

### Why
If a tenant typed "$49 installation fee" and updates it 6 weeks later, the old note
stays in `tenant_kb_documents` poisoning AI answers. Global KB has Step 9F; tenant
notes have nothing.

### Kill angle
BLOCKED: querying Supabase from the nightly runner requires a service-role key in GH
Secrets. Per security policy (`claude-code-security.md`), service-role keys in GH Secrets
are a lateral-movement risk. A safer path is a new FastAPI admin endpoint — but that's
M effort. WEAKENED.

---

## Idea C: Subconscious PR Tombstoning (Step 9K)
**Category:** Operational
**Effort:** XS
**Confidence:** HIGH (mechanism) / HIGH RISK (side effects)
**Channel:** nightly-commit-review bash block

### What
Nightly: auto-close `subconscious`-prefixed draft PRs older than 14 days with
"superseded by latest recommendation" comment.

### Why
5 open subconscious draft PRs (oldest 6+ days). PR list growing each cycle. Morning
digest flagged "PR debt growing."

### Kill angles
- **Destructive**: auto-closing a PR with in-progress human review removes evidence
- **Contradicts dedup guard**: the PR dedup guard was created to REUSE existing branches;
  tombstoning eliminates them on a timer
- **Removes pressure**: fewer visible PRs might reduce urgency to merge Step 9G
- **Root cause untouched**: non-merging is an approval friction problem, not a PR-count
  problem

VERDICT: KILLED. Blunt instrument. Destroys more than it fixes.

---

## Idea D: KB Staleness Escalation Hardener
**Category:** Operational
**Effort:** XS
**Confidence:** HIGH (mechanism) / LOW (timing)
**Channel:** nightly-commit-review SKILL.md bash block

### What
After 3+ consecutive Step 9F "STALE" alerts, create a P1 GH issue tagged `critical`
instead of another #403 comment. Breaks comment-blindness.

### Why
KB 13 days stale. Step 9F fires same "check your secrets" comment every night to #403.
Alert-blindness has set in. A `critical`-labeled issue escalates past comment noise.

### Kill angle
PREMATURE DEPENDENCY: counting "consecutive Step 9G trigger failures" requires Step 9G
to be live. Step 9G isn't merged. Without Step 9G in SKILL.md, there's nothing to count.
This idea can't activate until Step 9G is merged. WEAKENED — park for run 102 if Step 9G
merges.

---

## Idea E: Subconscious PR Merge Readiness Reporter
**Category:** Operational
**Effort:** S
**Confidence:** MEDIUM
**Channel:** nightly bash + GH MCP

### What
Nightly: identify oldest AUTONOMOUS-EXECUTABLE subconscious PR with no merge conflicts.
Post "MERGE READY — action needed" comment on that PR with what it does, days pending,
and risk level.

### Why
Step 9G PRs (#625, #626) open 3+ days. Nothing actively surfaces "this is safe and ready
to merge." A targeted escalation at day-7 and day-14 would differentiate urgency.

### Confidence note
MEDIUM. Daily comments on the same PR become noise within 3 days (comment-blindness, same
as alert-blindness). The better version (day-7 comment, day-14 P1 issue) is cleaner but
adds M effort for the exponential-backoff logic. WEAKENED to next run.

---

## Summary Ranking
1. **Idea A (Step 9J)** — HIGH confidence, XS effort, zero risk, immediate fix for visible pain
2. **Idea E** — promising kernel, needs exponential-backoff refinement, park for run 102
3. **Idea D** — good idea, wrong timing (Step 9G dependency), park for when 9G is live
4. **Idea B** — WEAKENED (auth architecture blocker)
5. **Idea C** — KILLED (destructive risk)
