# Run 115 Winner: Step 9L — Dead Service Detector

**Status:** RECOMMENDED THIS RUN (first recommendation → human-approve next cycle)
**Category:** code_health
**Effort:** S
**Confidence:** HIGH
**Source run:** 115 (parking lot from run 114)

---

## Mandate Check (run 115)

From run_115_mandate in governance.json:

| Item | Result |
|------|--------|
| Step 9J SKILL.md fix in place (dirty/blocked/unknown)? | ✅ YES — lines 398-403 confirm |
| Nightly-2026-08-28: any Dependabot PRs merged? | N/A — no AM run today; first nightly with fix will be tonight |
| Pre-commit block_demo_role hook implemented? | ❌ NO — run 111 winner pending human approval (PR #683) |
| GH #399 Day 60+: resolved? | ❌ NO — still open (Day 60+) |
| GH #684 brain connector PAT rotated? | ❌ NO — still open |
| agent_escalation.py: still 0 callers? | ✅ CONFIRMED — 0 grep hits from routers |
| GH #669 middleware PR opened? | ❌ NO — still open, blocked by GH #399 |

---

## What

Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md`.

Step 9L: **Dead Service Detector** — scan `backend/services/` for Python files that have zero import references from `backend/routers/`. Flag any file with 0 callers as a dead-code candidate and log it. If a file has been dead for 2+ consecutive nightly runs, file a GH issue.

## Why

`backend/services/agent_escalation.py` has 88 LOC and 0 import references from any router file. This was flagged in run 114 parking lot as "dead code risk". Without automated detection, these files accumulate silently — dead code that confuses future agents and inflates codebase size.

The detector is cheap to add (grep-based, deterministic) and compounds indefinitely — every nightly scan catches newly-orphaned services before they become confusing.

## Implementation Sketch (SKILL.md insertion after Step 9K)

```
9L. (Dead Service Detector) Scan for backend service files with zero router callers:
    1. List files: glob `backend/services/*.py`, excluding `__init__.py`, `base*.py`, `*test*.py`.
    2. For each file, grep `backend/routers/` for any import of that module name.
       - Module name = filename stem (e.g. `agent_escalation` from `agent_escalation.py`)
       - Grep pattern: `from backend.services.{name}|import backend.services.{name}`
    3. Collect files with 0 grep hits → dead_candidates list.
    4. Filter known-exclusions list (hardcoded in SKILL.md; start empty, add as needed):
       - Exclude: `managed_agents.py` (used via MCP, no router import)
       - Exclude: `kb_provenance.py` (called by background tasks, not routers)
    5. Compare against previous run's dead_candidates (if memory.jsonl has prior entry).
       - First-time dead (not in prior run): log "Step 9L: new dead candidate {file} — monitor"
       - Repeated dead (2+ runs): file GH issue via mcp__github__issue_write with label "dead-code"
    6. Log result: "Step 9L: {N} services scanned, {M} dead candidates, {K} issues filed"
```

## Dedup Guard

Track dead_candidates in memory.jsonl per-run. Issue filing only on 2nd consecutive detection prevents noise from transient false positives (e.g. a service imported only in tests, not routers).

## Expected Outcome

- Next nightly: `agent_escalation.py` detected as dead candidate (first sighting)
- Run after: GH issue filed if still dead — human triages (delete or wire up)
- Ongoing: catches future orphaned services within 24-48h

## Run 116 Mandate

1. Step 9L added to SKILL.md? (this is first recommendation — human approve + implement)
2. Nightly-2026-08-28: did Step 9J merge any Dependabot PRs? (first night with fix active)
3. Pre-commit block_demo_role hook (run 111 winner, PR #683): merged?
4. GH #399 Day 61+: any resolution?
5. GH issue filed for agent_escalation.py dead code?
