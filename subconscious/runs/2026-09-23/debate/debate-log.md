# Debate Log — Run 2026-09-23 (Run 127)

Top 3 ideas debated: Idea 1 (Step 9E P0 tier), Idea 2 (pre-commit AI guard), Idea 3 (Step 9J token budget fix).

---

## Idea 1: Step 9E P0 Tier — 10-Day Credential Expiry Escalation

### Challenge

1. **Evidence strength?** GH #893 was already filed with P0 label and "rotate now" wording by yesterday's nightly. The immediate crisis has a human-visible notification path. Does the systemic fix add meaningful value beyond what's already done?

2. **Highest leverage now?** With only 9 days to expiry, Step 9E P0 tier would fire TONIGHT on the credential — but GH #893 already exists. The human has seen the alert. Re-filing a second GH issue from Step 9E P0 would be noise, not signal.

3. **What could go wrong?** If Step 9E P0 fires AND GH #893 is open, the dedup check would skip filing a second issue — so no duplicate. But if dedup check fails, two P0 issues are filed. Dedup relies on issue title match.

4. **Similar to rejected paths?** No — Step 9E has been carried 6 times precisely because it IS high priority, just blocked by task-prompt constraint. No governance rejection.

5. **Too similar to active direction?** Yes — this is literally the same winning concept as runs 119–125. At run 127, nothing has changed about the recommendation itself. The only change is AUTOPILOT_GH_TOKEN is now 9 days from expiry instead of 80+ days. The urgency is higher but the action is identical.

### Defend

1. **GH #893 covers this instance; Step 9E P0 covers the pattern.** GH #893 will be closed when AUTOPILOT_GH_TOKEN is rotated. Step 9E P0 tier remains for the NEXT credential (SUPABASE_ACCESS_TOKEN, ANTHROPIC_API_KEY, etc.). The systemic fix is not redundant with GH #893 — it addresses a different scope.

2. **Leverage is high precisely because timing is perfect.** The subconscious has been recommending this for 7 runs. The urgency finally matches the severity. A human reviewing this output TODAY will see AUTOPILOT_GH_TOKEN at 9 days and understand immediately why the P0 tier matters.

3. **Dedup check handles the noise risk.** Step 9E P0 would check for existing open GH issue with P0 label before filing. GH #893 is already open. The dedup check would skip filing and log "P0 dedup skip: GH #893 exists." No noise.

4. **Autonomous-executable since run 122.** The mechanism is simple: 3-line addition to SKILL.md. Blast radius zero. Every prior carry has been "recommend only" by task-prompt constraint. That constraint remains; the recommendation remains correct.

### Verdict: **SURVIVES** — carries forward, higher urgency than run 126 (9 days to actual expiry)

---

## Idea 2: Pre-Commit Hook Blocking New Unguarded AI Call Sites

### Challenge

1. **Evidence strong enough?** GH #827 says 45 violations. But what's the rate of NEW violations being added? If zero new violations per week, prevention adds no value now.

2. **Is this the highest-leverage thing?** The 45 existing violations won't be fixed by a pre-commit hook. A hook prevents new ones. But if the existing 45 are unblocked from billing risk, the marginal value of preventing a 46th is lower than fixing the 45.

3. **What could go wrong?** check_ai_metering.py exists but what's its false-positive rate? If it generates false positives, the hook blocks valid commits — friction, developer frustration, pushback. Pre-commit hook path is also unclear: `.claude/settings.json` hooks vs git hooks vs CI check.

4. **Similar to rejected paths?** No prior rejection of this pattern. Additive to Step 9L.

5. **Too similar to active direction?** Related to Step 9L (nightly detection) but complementary, not overlapping.

### Defend

1. **GH #827 references 45 EXISTING violations found in September 2026.** The PRs #792-#799 retroactively metered 6 sites. The remaining 39+ are growing as the codebase grows — check_ai_metering.py's existence in CI and nightly creates visibility but no friction at commit time.

2. **Hook is additive, not blocking for clean code.** If a developer correctly guards their AI call, the hook passes silently. Only unguarded additions are blocked. Net friction: zero for correct code.

3. **Implementation is atomic.** One addition to scripts/install-hooks.sh (already exists: `bash scripts/install-hooks.sh`) + one pre-commit hook file. Blast radius: local dev environment only.

4. **False-positive risk is addressable.** check_ai_metering.py has 325 lines of tests (run 117). If false-positive rate is unknown, the hook can be warning-only first. But "warning-only" pre-commit hooks get ignored — blocking is the right default for billing-risk code.

### Verdict: **WEAKENED** — correct direction, but (a) 45 existing violations make new-prevention less urgent than fixing existing, (b) false-positive rate of check_ai_metering.py in `--staged-only` mode is untested, (c) hook implementation complexity (git hooks vs .claude/settings.json) needs design clarity. Move to parking lot.

---

## Idea 3: Step 9J Token Budget Fix — Dependabot First

### Challenge

1. **Evidence strong enough?** 17/19 skips was observed in run 116 (2026-09-06). Morning digest shows 6 fresh PRs today. But Step 9J was already fixed (Step 9J detection fix in run 114). The skip might be from token budget, not detection.

2. **Is this highest-leverage?** Step 9J already merges Dependabot PRs when it runs. Moving it earlier in the step sequence helps, but today's 6 PRs (#885-#891) will be processed within 24h anyway (next nightly). The CVE window is 1 day, not 3.

3. **What could go wrong?** Moving Step 9J earlier deprioritizes Steps 9F/9G/9H/9I/9K/9L for token budget. If token budget is consumed by Dependabot first, KB staleness check and demo-role sweep might skip. Prioritization tradeoff is unclear.

4. **Similar to rejected paths?** Previous runs noted the 17-skip problem and added rebase trigger (run 112). No prior fix to step ordering.

5. **Too similar to active direction?** Related to Step 9J (already in active_directions as implemented). A step-ordering fix is a distinct action.

### Defend

1. **17/19 skips means 89% of Dependabot PRs aren't processed per nightly.** Six fresh PRs at 2 processed per run = 3 nightlies to clear them. That's 3 days of CVE exposure per batch. At bi-weekly Dependabot batches, we're always 2-3 days behind.

2. **Position-before approach is correct.** Dependabot merges take <1min per PR (CI already green). Steps 9F/9G/9K/9L each take 2-5min for large repos. Running Dependabot merges first uses ~2min of token budget for 5 PRs, then remaining steps run on what's left.

3. **Counter-challenge on tradeoff:** Security/KB steps (9F/9G/9I) are more important per-run than Dependabot merges. But they also complete in a single API call each. The token budget issue is from cumulative nightly overhead, not single-step cost.

### Verdict: **WEAKENED** — step ordering change is risky (deprioritizes security/KB steps for Dependabot), and the 17-skip likely stems from earlier steps consuming context, not a solvable ordering problem without deeper investigation. Parking lot.

---

## Synthesis

- **Idea 1 (Step 9E P0 tier): SURVIVES → WINNER** — 7th carry, autonomous-executable since run 122, perfect timing with AUTOPILOT_GH_TOKEN at 9 days. Dedup guard handles GH #893 overlap.
- **Idea 2 (pre-commit AI guard): WEAKENED → parking lot** — correct direction, but false-positive risk and implementation complexity warrant a design pass before implementation.
- **Idea 3 (Step 9J ordering): WEAKENED → parking lot** — tradeoff unclear, needs investigation first.

**Winner: Step 9E P0 Credential Expiry Escalation Tier**
