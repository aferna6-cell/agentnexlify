# Improvement Backlog — Run 2026-09-18 (Run 122)

## Active (in progress or next-run mandate)

### Step 9E: 10-Day P0 Escalation Tier ← RUN 122 WINNER (autonomous-executed this run)
- Implementation: edit Step 9E block in `.claude/skills/nightly-commit-review/SKILL.md`
- Adds `days_remaining <= 10` tier that files P0 GH issue with dedup guard
- Run 123 mandate: verify grep shows `days_remaining` + `P0` in Step 9E block

### Step 9G: Replace `gh workflow run` with `mcp__github__actions_run_trigger` ← 2nd carry-forward
- Source: run 121 winner
- Status: 2nd carry-forward. Autonomous-executable at run 124 (3rd carry-forward)
- In-session workaround applied nightly; SKILL.md still has broken bash command
- Run 123: 2nd carry-forward → run 124: MUST implement
- Evidence confirmed: MCP trigger works (status 204 on 2026-09-18 nightly)

---

## Parking Lot (valid, deferred)

### os_tool_executions.py 783L God Class Split
- 6th consecutive mention (run 117→118→119→120→121→122)
- File: `backend/services/os_tool_executions.py`, 783 lines, stable 19d+
- Rule 9 threshold (600L) exceeded
- Action needed: file GH issue for owner review; propose split into executor/parser/validator modules
- No code change — human approves the refactor plan
- Deferred: no governance mandate yet; escalate at run 123 if no GH issue exists

### Brain Connector Staleness (GH #800)
- Last run 2026-07-23 (57 days ago, threshold 14d, STALE)
- Human-action-required: rotate credentials
- GH #800 open and tracking
- Subconscious cannot resolve — human must rotate credentials

### AI Metering 45 Violations (Step 9L)
- 45 violations unchanged for 2+ nightly reviews (16 routers, 29 services)
- Step 9L reports "owner tracking separately" — canonical GH issue number unconfirmed
- Action: verify or file canonical tracking issue
- Deferred: unclear if issue exists; run 123 — investigate GH issue status

---

## Rejected / Frozen

### ai_human_handoff (frozen)
- governance.json: frozen_ideas includes "ai_human_handoff"
- Do not re-propose

### widget_drift_topic_retired (retired)
- governance.json: widget_drift_topic_retired: true
- Do not re-propose widget sync improvements in subconscious

---

## Open Questions

1. **SUPABASE_ACCESS_TOKEN rotation status**: `ops/credential-rotation-schedule.md` notes "unknown state." Has this been set in environment? Run 123: check if owner has resolved.

2. **GH #403 KB autopopulate resolution**: Step 9G trigger was queued 2026-09-18, but may fail if ANTHROPIC_API_KEY missing from Actions secrets. Monitor: did the triggered workflow succeed?

3. **memory.jsonl line 122 git conflict artifact**: Last line of `subconscious/state/memory.jsonl` has a stale git conflict marker (`>>>>>>> 878f739 ...`). Should be cleaned up. Low priority but data integrity concern.
