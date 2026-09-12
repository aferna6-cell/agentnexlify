# Winning Concept — Run 121 (2026-09-12)

**Winner:** Step 9G MCP Migration Evaluation — replace gh CLI only after MCP action verification
**Category:** operational
**Effort:** XS after prerequisite verification
**Confidence:** MEDIUM
**Source:** Run 120 mandate item 6 + KB staleness evidence (17d stale)
**Carry-forward count:** 0 (new winner this run — NOT a carry-forward)

---

## Recommendation

The current Step 9G `gh workflow run` / `gh run list` mechanism is not viable in the cloud-hosted nightly environment. Evaluate `mcp__github__actions_run_trigger` and a corresponding run-list action as the replacement, but **do not edit Step 9G until those actions are verified to exist and work in the actual nightly CCR execution surface**.

---

## Why This, Why Now

Step 9G was implemented in run 101 using `gh workflow run kb-autopopulate.yml`, but the gh CLI is not available in the cloud-hosted CCR environment used by the nightly routine. That leaves the current self-healing trigger path ineffective. Meanwhile `knowledge-base/log.md` shows the KB has been stale beyond its 7-day threshold.

The proposed MCP replacement is plausible and appropriately scoped, but its availability in the **specific nightly CCR session** has not yet been demonstrated end-to-end. A deferred/subconscious tool listing is not sufficient evidence to call the action confirmed or available for nightly execution.

Run 120 mandate item 6 explicitly calls for this evaluation. The correct output of run 121 is therefore a recommendation plus a verification prerequisite, not an implementation claim.

---

## Implementation Sketch

**Only after the MCP actions are verified in the nightly CCR execution surface**, edit `.claude/skills/nightly-commit-review/SKILL.md`, Step 9G block (lines ~318–342).

**Replace:**
```
       Run: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       If command fails (exit non-zero): log "Step 9G: gh workflow run failed — check GH token or workflow name" and continue to step 10.
```

**With the verified trigger action, conceptually:**
```
       Call the verified GitHub Actions workflow-trigger MCP action for:
         owner="aferna6-cell"
         repo="agentnexlify"
         workflow_id="kb-autopopulate.yml"
         ref="main"
       If the trigger call itself fails: log the trigger/tool error and continue to step 10.
```

**Replace:**
```
       Run: `gh run list --workflow=kb-autopopulate.yml -R aferna6-cell/agentnexlify --limit=1 --json conclusion,url`
```

**With the verified run-list action, conceptually:**
```
       Call the verified GitHub Actions run-list MCP action for kb-autopopulate.yml.
       Read the latest run's conclusion and URL using the actual returned schema.
```

Do not hard-code speculative action names or argument schemas into the production skill until they have been observed in the nightly CCR tool surface.

**Dedup guard:** Step 9G should only trigger if Step 9F confirmed staleness > 7 days (this logic is already in the SKILL.md — preserve it).

---

## Prerequisites / Open Blockers

**This is a RECOMMENDATION ONLY.** Per subconscious SKILL.md design: "The subconscious RECOMMENDS but does NOT implement." Human approval and execution in a separate nightly session are required.

Before implementing, two prerequisites must be addressed:

1. **Verify the proposed GitHub Actions MCP trigger and run-list capabilities in nightly CCR sessions.** Confirm the exact action names, argument schemas, and returned fields with a real end-to-end invocation before editing SKILL.md.

2. **GH #403 (ANTHROPIC_API_KEY missing from GitHub Actions secrets) remains a separate KB execution blocker.** Even a successful Step 9G workflow trigger will not restore KB health if the triggered workflow cannot execute its Anthropic-dependent work. Trigger-path remediation and workflow-secret remediation are separate conditions and should be verified independently.

The gh CLI root cause is supported. The MCP replacement remains a candidate pending environment verification. Run 122 should verify the execution surface before any implementation is described as complete.

---

## Verification After Implementation

After the exact MCP actions are verified and Step 9G is actually implemented:

```bash
# Confirm the verified MCP trigger/list mechanism is present in Step 9G.
# Confirm the old gh CLI mechanism is absent from Step 9G.
grep 'gh workflow run' .claude/skills/nightly-commit-review/SKILL.md
# Must return 0 results for the Step 9G block.
```

Then require runtime evidence from the next nightly execution:
- Step 9G invokes the verified trigger action successfully.
- The triggered `kb-autopopulate.yml` run is observable through the verified run-list/read surface.
- If the workflow fails because #403 remains unresolved, report that as a separate workflow prerequisite rather than a Step 9G trigger failure.
- `knowledge-base/log.md` receives a fresh entry only after the workflow itself completes successfully.

---

## What This Replaces

Previous active direction: Step 9E credential expiry escalation (run 119/120 winner — **implemented** as of run 120. Mandate items confirmed complete. No pending escalation needed for that direction.)

---

## Run 122 Mandate

1. Verify whether the proposed GitHub Actions MCP trigger and run-list capabilities are actually present in the nightly CCR execution surface; record the exact action names and schemas.
2. If verified, implement Step 9G with those observed actions and remove the `gh workflow run` path; otherwise leave production SKILL.md unchanged and record the blocker.
3. After implementation, confirm Step 9G fires in a nightly run and separately inspect the triggered workflow result.
4. Confirm whether #403 still blocks `kb-autopopulate.yml`; do not conflate workflow-secret failure with trigger failure.
5. Has `knowledge-base/log.md` received a new entry? This is the final end-to-end KB-health signal.
6. AUTOPILOT_GH_TOKEN: check days_since_rotation and reuse GH #399 for credential-identity escalation if needed.
7. SUPABASE_ACCESS_TOKEN: if the rotation date remains unknown, keep it on the human-action path rather than inventing an expiry date.

---

## Escalation Path

- Run 121 (this run): recommend verification + candidate migration
- Run 122: verify execution surface; implement only if proven
- Later carry-forward/escalation must preserve that verification gate and must not autonomously hard-code unverified tool names or schemas
