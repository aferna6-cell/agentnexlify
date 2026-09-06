# Winning Concept — Run 117 (2026-09-06-pm)

## Recommendation
Add Step 9L block to `.claude/skills/nightly-commit-review/SKILL.md` — the detector (`scripts/check_ai_metering.py`) is confirmed working and finds 30+ unguarded AI-calling functions; the nightly step is the only remaining deliverable to close the billing coverage gap permanently.

## Why This, Why Now

`check_ai_metering.py` shipped in commit `1c5b749` (today) with 325 lines of regression tests covering all 11 fixture cases from the run 115 winning-concept. Live scan this run confirms 30+ violations across 16 router files and 14 service files — every function calling `call_claude_messages` or `client.messages.create` without `ai_usage_guard` or the reserve/record/release lifecycle. The 7-PR emergency sprint (#792-#799) that retrofitted 6 AI endpoints took 3 days and 1726 test lines. Without Step 9L, every new AI route starts unguarded and accumulates billing debt until a human notices. The governance `autonomous_executable_run: 117` mandate has been active since run 115, carried forward through run 116 only because the task prompt overrode escalation ("recommend only"). This run carries the same override — escalation condition resets to run 118 (3rd carry-forward per governance = direct implementation precedent set by Steps 9F/9G/9I/9J/9K).

## Implementation Sketch

### Deliverable — Step 9L block for `nightly-commit-review/SKILL.md`

Insert after Step 9K summary line and before "10. Commit report":

```markdown
### Step 9L — AI Usage Guard Coverage Sweep

1. Run detector:
   ```bash
   python3 scripts/check_ai_metering.py > /tmp/step9l-violations.txt 2>&1
   METERING_EXIT=$?
   ```
   If METERING_EXIT != 0: log "Step 9L: detector error — skipping" and continue.

2. Read /tmp/step9l-violations.txt. If empty: log "Step 9L: 0 violations — all AI-calling functions are metered — PASS" and continue.

3. Parse violations (format: `path:function:line`). For each unique `path:function` pair:
   a. Search for existing open GH issue:
      `mcp__github__search_issues(query="repo:aferna6-cell/agentnexlify is:open label:ai-ready {function}")`
   b. If matching open issue found → log "Step 9L: {path}:{function} already tracked — dedup-skip" and skip.
   c. If none → file via `mcp__github__issue_write`:
      - Title: `fix(billing): {path}:{function} calls Claude without ai_usage_guard`
      - Labels: `["billing", "ai-ready"]`
      - Body: "AI metering sweep (Step 9L, {DATE}): `{function}` in `{path}` (line {line}) calls Claude without an `ai_usage_guard` or reserve/record/release lifecycle guard. Every invocation bypasses billing accounting.\n\nFix pattern: add `_=Depends(ai_usage_guard)` to route function signature (router) or wrap call in `reserve_ai_tokens` / `record_ai_usage` / `release_ai_token_reservation` (service)."
      - Body contains: identifiers only — no prompt content, customer data, or secrets.
   d. Cap at 10 issues filed per nightly run to avoid tracker flood. Log "Step 9L: cap reached (10) — {K} violations deferred to next run" if exceeded.

4. Log to nightly report:
   `Step 9L: {N} functions scanned, {M} violations found, {K} issues filed, {D} dedup-skipped.`
```

Note: the `--diff-only` flag is NOT used here — the sweep is full-scope by design (same as Step 9I). The 10-issue cap per run handles graduated filing.

## What This Replaces

No prior active direction replaced — Step 9L is additive. Step 9K (stale subconscious PR audit) and Step 9I (block_demo_role sweep) continue to operate. Together Steps 9I, 9J, 9K, 9L form a nightly security+billing guard suite.

## Carry-Forward Note

This is the **2nd carry-forward** of the run 115 Step 9L recommendation. Governance mandate fires at **run 118** (3rd carry-forward = autonomous-executable escalation per established precedent: Steps 9F/9G/9I/9J/9K all escalated at 3rd carry-forward). Task prompt for this run ("Do NOT implement. Only recommend.") takes precedence over run 117 mandate. Escalation condition: autonomous-executable if not approved by run 118.

## Confidence

**HIGH** — Evidence is direct: `check_ai_metering.py` runs cleanly and finds 30+ real violations. Mechanism proven: Step 9I is identical (grep-then-file pattern) and has operated 3+ weeks with zero false-positive issues. Dedup guard (search_issues before filing) and 10-issue cap mitigate tracker flood risk. Implementation sketch is complete and carries forward unchanged from run 116.
