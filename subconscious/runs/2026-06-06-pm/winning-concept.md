# Winning Concept — 2026-06-06-pm (Run 52)

## Recommendation

Append a "Post-Fix Re-scan" step to `nightly-commit-review SKILL.md`: after applying any LOW-risk fix in a nightly cycle, re-run `check_project_invariants.py` and re-check `governance.json` `pending_autonomous` items for newly-unblocked pre-conditions, then execute any that are now unblocked under the same scope rules.

## Why This, Why Now

Nightly 2026-06-05 (8db33df) applied the run 49 em-dash fix AND verified `check_project_invariants.py exits 0` — yet Check 10 (Item A, `pending_autonomous + autonomous_executable: true` since run 22, 20 days) was not applied. Root cause: the nightly scans `pending_autonomous` pre-conditions once, before applying fixes. When the em-dash fix changed the pre-condition mid-cycle, there was no second scan. This is structural, not coincidental — the same gap fires whenever Fix X unblocks Autonomous Item Y. Tonight's fresh nightly cycle will likely apply Item A anyway (pre-condition met from start), but the structural gap remains for future sequences. The fix is a single additive SKILL.md edit — the same class of change that runs 40 (d481799) and 43 (4226ef4) implemented autonomously in 1 cycle.

## Implementation Sketch

**Time: ~5 min nightly execution. Risk: LOW (additive SKILL.md edit, no scope escalation).**

**AUTONOMOUS-EXECUTABLE** — This is a `.claude/skills/nightly-commit-review/SKILL.md` edit. Based on the nightly's established autonomous scope (SKILL.md edits are LOW-risk when `autonomous_executable: true` label is present), this should execute in tonight's 2:37 AM nightly.

### Step 1 — Locate the section in SKILL.md where LOW-risk fixes are applied and verified

Read `.claude/skills/nightly-commit-review/SKILL.md`. Find the step that says something like "after LOW-risk fix applied" or "verification" / "post-fix" section.

### Step 2 — Append the "Post-Fix Re-scan" block

Add the following after the LOW-risk fix application + verification step:

```markdown
### Post-Fix Re-scan: Check Newly-Unblocked Autonomous Items

After applying any LOW-risk fix this cycle:
1. Re-run `python3 scripts/check_project_invariants.py` — confirm exit status
2. Re-check `governance.json` `active_directions` for items with `"status": "pending_autonomous"` and `"autonomous_executable": true`
3. For each such item, evaluate its pre-condition:
   - Item A (Check 10 wire): pre-condition = `check_project_invariants.py exits 0`
   - Item B (widget sync guard): pre-condition = nightly scope includes bash + new file creation
4. If any pre-condition is NOW met that was not met at cycle start: execute the item under the same LOW-risk scope rules
5. Log the second-pass execution in the nightly log

This prevents multi-cycle delays when a fix applied in this cycle is the exact pre-condition another autonomous item was waiting for.
```

### Step 3 — Also confirm run 50 scope extension is present

While editing the SKILL.md, verify that Item B's scope block (from run 50 winner) is present:
- `scripts/check-widget-sync.sh` creation (new bash file, LOW-risk additive)
- Wire into `scripts/hooks/pre-push` (additive bash line)
- Fix `CLAUDE.md` Invariant #4 (`2 copies` → `3 copies`)

If the run 50 scope block is missing, add it in the same edit. Run 50 was `pending_autonomous` as of run 51 and nightly 2026-06-05 did not apply it.

### Expected cascade tonight (2:37 AM)

1. Nightly applies run 52 winner (SKILL.md edit) — post-fix re-scan added
2. During same cycle: nightly scans run 22 Item A — pre-condition `exits 0` met from start
3. Item A fires: Check 10 (3 lines bash) added to `scripts/hooks/pre-commit`
4. If run 50 scope block was added: Item B fires — `check-widget-sync.sh` created, wired into pre-push, CLAUDE.md patched

## What This Replaces

Previous active direction (run 50): "Extend nightly scope + mark Item B AUTONOMOUS-EXECUTABLE" — that SKILL.md scope extension is also pending_autonomous and may or may not have been applied. Run 52 subsumes run 50 if the scope extension is included in Step 3 above.

## Confidence

**HIGH** — Structural root cause confirmed by nightly log (explicit: "exits 0" + "Standing Items: Item A" in same log cycle). AUTONOMOUS-EXECUTABLE via established nightly SKILL.md edit path (runs 40/43 precedents, 4/4 success rate for this class of change). Risk LOW (additive, no scope escalation, existing guardrails apply).

## Bonus Actions (human-required)

**Bonus A — Merge PR #183 (~10 min, highest remaining human impact)**
Run 51 winner. Still pending. Verify diff targets `backend/routers/billing.py`, contains `15000: "autopilot"` + `25000: "professional"`, corrects test assertions. Then `gh pr ready 183 && gh pr merge 183 --squash`. Closes GH #181, silences Check 11, unblocks email_sequences split.

**Bonus B — Tag GH #107 Zapier as ai-ready (~2 min)**
Add `ai-ready` label to GH #107. Add comment: "Fix: add `plan_status IN ('active','trialing')` filter in `backend/services/zapier_auth.py::_get_api_key_client`. Add regression test." Routes to issue-to-pr-loop.
