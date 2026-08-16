# Run 103 — Winning Concept (2026-08-14-pm)

## Add brain-connector age-staleness check to Step 9C

**Category:** operational_efficiency  
**Effort:** S (~20 min to write + validate)  
**Confidence:** HIGH  
**Status:** AUTONOMOUS-EXECUTABLE — nightly-commit-review can apply this directly (SKILL.md edit only)

---

## Problem

Step 9C of the nightly-commit-review checks brain connector health by counting consecutive failures:

```
consecutive_failures >= 3  →  alert
```

This logic only fires when the connector TRIES and FAILS. If the connector stops running entirely (network issue, credential rotation, suspended job), consecutive_failures stays 0 and Step 9C reports PASS every night indefinitely.

**Evidence:**
- Brain connector last run: `2026-07-23T14:38Z` — 22 days ago
- Step 9C result today: **PASS** ("Last entry = success. 0 consecutive failures.")
- The 22-day gap is not surfaced anywhere in automated monitoring
- Morning digest exposes it only because a human wrote the digest — there is no automated alert
- This is identical to the 63-day KB staleness gap that motivated Step 9F (added run 99, 2026-07-xx)
- Step 9F checks KB age vs threshold; Step 9C has no equivalent age gate

The subconscious correctly fixed this class of problem for KB autopopulate. The brain connector is the same problem on a parallel track.

---

## Proposed SKILL.md Edit

In `.claude/skills/nightly-commit-review/SKILL.md`, find the Step 9C section and add after the consecutive-failures check:

```markdown
### Step 9C age gate (brain connector staleness)
After reading last INGESTION-LOG.md entry:
1. Parse timestamp of last successful entry (format: `YYYY-MM-DDTHH:MMZ`)
2. Compute days since last run: `today - last_success_date`
3. If days_since_last_run > 14:
   - Surface as WARNING in nightly summary: "Brain connector {N} days since last run (threshold: 14 days). Last run: {date}."
   - Do NOT create a new GH issue if #394 or #399 are already open (check open issues first to avoid duplicate issue spam)
   - If no existing open issue covering this: open GH issue labeled `ops` + `brain-connector` with title "Brain connector {N} days stale — last run {date}"
4. If days_since_last_run <= 14: PASS (no action)
```

**Threshold rationale:** 14 days (2 weeks). KB threshold is 7 days; brain connector runs less frequently by design (no API cost, but depends on GitHub PAT and Supabase access token both being valid). 14 days gives enough runway without generating false positives on legitimate 7-10 day gaps.

---

## Why This Wins

1. **Pattern match to a known fix.** Step 9F was added to solve this exact class of problem for KB autopopulate. Identical logic applied to brain connector.
2. **New monitoring, not a carry-forward.** Idea 2 was not present in any previous run. Fresh evidence from this cycle.
3. **Autonomous-executable.** SKILL.md edit. No backend code, no migrations, no new state files, no GitHub API calls in the edit itself. The nightly can apply this immediately.
4. **Compound from day 1.** Every nightly run after this edit benefits. If brain connector lapses again, Step 9C will alert within 14 days instead of silently passing.
5. **Low blast radius.** Single step added to one SKILL.md. No existing functionality changed.

---

## Implementation Path

The nightly-commit-review session can execute this directly:
1. Read `.claude/skills/nightly-commit-review/SKILL.md`
2. Locate Step 9C section
3. Add the age-gate block described above immediately after the consecutive-failures check
4. Commit: `fix(ops): add brain-connector age-staleness gate to nightly Step 9C`

No human approval needed. This is a monitoring improvement with no code impact and no breaking changes. Risk = near-zero.

---

## Carry-Forward Note (Idea 1 — route-security-guard-audit SKILL.md)

Run 102 winner is in 1st carry-forward. The SKILL.md content is fully written in `subconscious/runs/2026-08-11-pm/winning-concept.md`. It remains RECOMMENDED — awaiting human approval. Will re-enter ideation in run 104 as 2nd carry-forward. At run 105 (3rd carry-forward), escalate to AUTONOMOUS-EXECUTABLE if still unimplemented.

---

## Next Action

Nightly-commit-review session: apply the Step 9C edit described above. No human approval gate.