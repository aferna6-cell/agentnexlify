# Debate Log — Run 2026-09-17-pm (Run 121)

Top 3 ideas stress-tested with hard objections.

---

## Idea 2 — Fix Step 9G: Replace `gh workflow run` with `mcp__github__actions_run_trigger`

### FOR
- KB has been dark 22 days. Step 9G is the self-healing trigger, but it's been silently broken since ~run 107 (2026-08-19) — confirmed by Step 9G being ABSENT from nightly-2026-09-17 output despite KB being 22d stale.
- gh CLI is definitively unavailable in cloud/CCR sessions. This isn't a transient failure.
- `mcp__github__actions_run_trigger` is confirmed in the deferred tools list for this session type — the fix will actually work.
- Fix pattern: replace one bash block with one MCP call. XS effort. Same autonomous-executable channel as Steps 9F/9G/9I/9J/9K/9L.
- Even if kb-autopopulate Actions job itself still fails (ANTHROPIC_API_KEY missing per GH #403), Step 9G will correctly detect the failure and escalate via GH #403 comment — restoring the feedback loop that's been silent for 30 days.

### AGAINST
**Objection A:** "mcp__github__actions_run_trigger is listed in deferred tools but that doesn't mean it succeeds — it might require permissions we don't have in routine sessions."

**Defense:** Deferred tool availability in the same session type means the schema is accessible. Dispatch permissions would be the same as what creates PRs and comments on issues (already confirmed working in routine sessions via Steps 9J/9K). If it fails due to permissions, the failure will be explicit (not silent like the gh CLI failure) and Step 9G can handle the error and comment on #403.

**Objection B:** "The real problem is ANTHROPIC_API_KEY missing from Actions secrets (GH #403 is already tracking this). Fixing Step 9G just triggers a job that immediately fails — no net improvement."

**Defense:** Two separate problems. GH #403 is the 'why kb-autopopulate fails'. Step 9G is 'why nightly never tries anymore'. Triggering a known-to-fail job is still better than never triggering it — it generates a failure notification, maintains escalation pressure on #403, and restores the feedback loop. When #403 is resolved (ANTHROPIC_API_KEY added), Step 9G will work immediately without another fix.

**Objection C:** "This is the same Step 9G that was listed as implemented in governance.json. Aren't we fixing something already marked fixed?"

**Defense:** governance.json lists `implemented: true` for the Dependabot search query fix (Step 9J was the search_pull_requests fix, not Step 9G). Step 9G KB trigger was never marked fixed — it was marked as "unverified tool availability" for mcp__github__actions_run_trigger. This run confirmed the tool IS available. Different direction from what governance.json tracks.

### VERDICT: SURVIVES → WINNER

---

## Idea 1 — Step 9E 10-Day Early Warning Window (2nd Carry-Forward)

### FOR
- AUTOPILOT_GH_TOKEN at 75 days. Expires 2026-10-02 (15 days). No GH issue filed yet.
- 10-day early warning not implemented. Pattern: 3 consecutive nightlies logged "approaching threshold" with zero human action.
- Expires in 15 days — the window is now urgent regardless of whether the early-warning logic exists.

### AGAINST
**Objection A:** "AUTOPILOT_GH_TOKEN crosses the 76d threshold tomorrow. The existing Step 9E logic fires at ≥76d and WILL comment on GH #399 in nightly-2026-09-18. The early warning window (≤10 days remaining) is less valuable now because existing logic already handles this rotation."

**Defense:** True. The existing threshold logic will fire tomorrow. The 10-day early-warning value-add is marginal for THIS rotation cycle. The improvement pays off for the NEXT rotation cycle (3 months away) but carries no immediate value today.

**Objection B:** "This is the 2nd carry-forward. Run 119 said autonomous-executable on 3rd carry (run 122). Why aren't we declaring it winner here to set up auto-execution?"

**Defense:** The autonomous-executable channel is earned by the improvement remaining unaddressed, not by calendar position. This run has a higher-leverage win available (Step 9G). Step 9E can continue to the 3rd carry where it becomes autonomous-executable at run 122 as originally scheduled.

### VERDICT: WEAKENED → Parking lot (3rd carry-forward at run 122 → autonomous-executable)

---

## Idea 3 — Split os_tool_executions.py God Class (783L)

### FOR
- 783 lines. CLAUDE.md Rule 9: factor god classes at 600+ lines.
- 4th consecutive subconscious run mentioning this. Stability window 14+ days.
- Clean separation available: dispatching, validation, result processing.

### AGAINST
**Objection A:** "M effort refactor requires human approval per subconscious brief guardrails ('No breaking changes without explicit human approval'). The autonomous-executable channel only applies to XS SKILL.md edits."

**Defense:** Correct. M effort = human approval gate. This is not a recommendation the subconscious can make as immediately executable. It should be on the improvement backlog for the owner to schedule.

**Objection B:** "4th consecutive mention with no implementation. Is this improving anything by recommending it again?"

**Defense:** Fair point. The recommendation needs to either escalate to the owner explicitly or be accepted as a recurring parking-lot item. This run will include it in improvement-backlog.md with explicit escalation language.

### VERDICT: DOWNGRADED → improvement-backlog with escalation note (4th consecutive mention)

---

## Final Rankings

| Rank | Idea | Verdict |
|------|------|---------|
| 1 | Fix Step 9G | WINNER |
| 2 | Step 9E early warning | Parking lot (run 122 → autonomous-executable) |
| 3 | Split os_tool_executions.py | Improvement backlog (4th mention — escalate to owner) |
