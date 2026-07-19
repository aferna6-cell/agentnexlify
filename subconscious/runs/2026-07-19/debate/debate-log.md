# Debate Log — Run 2026-07-19

## Top 3 entering debate
1. Idea 1: Step 9F — Channel Pivot to Human-Session Direct Edit
2. Idea 2: Wire conversation_enrichment_job.py into scheduled_jobs.py
3. Idea 3: platform_flags ALLOWED_TOGGLE_KEYS Guard

---

## Round 1: Test Each Idea Against Mandate Checks

### Idea 1: Step 9F Channel Pivot
**Run 99 mandate check 1:** "Step 9F block present in SKILL.md? (grep — should PASS now)"
- 3 consecutive cycles, block ABSENT.
- Root cause identified this run: autonomous nightly channel fires on live problems, not pending improvements. KB is healthy — no live trigger. The nightly cannot add a block that has no active alert to spawn the action.
- This idea is a carry-forward with a NEW mechanism insight. Prior runs recommended "autonomous nightly will add it." This run corrects the mechanism: human must paste the block. The idea is STRONGER than prior cycles, not weaker.

**Steelman for Idea 1:**
- The Step 9F bash block already exists verbatim in `subconscious/runs/2026-07-17-pm/winning-concept.md`. Zero design work needed.
- SKILL.md edit is a ~28-line paste operation. Lowest possible execution risk.
- Once added, every nightly log permanently includes "Step 9F: KB autopopulate last run: YYYY-MM-DD (N days ago)". Prevents 72-day silent gap recurrence.
- Mandate check passes the MOMENT a human applies it. No further cycles of waiting.

**Attack on Idea 1:**
- Is Step 9F actually valuable if KB is healthy 99% of the time? Counter: the 72-day gap happened silently. The value is in the 1% — the signal fires exactly when needed and is silent when not. Zero cost when healthy (just a log line).
- Why not let nightly add it when KB goes stale again? Counter: then we wait for KB to go stale (which might be weeks), nightly adds the block, but by then KB is already stale — the block was supposed to PREVENT the gap, not react to it. Self-defeating.

**Verdict:** STRONG. Highest-priority mandate item, exact mechanism now understood, zero ambiguity on implementation.

---

### Idea 2: conversation_enrichment_job.py Scheduling
**Mandate context:** Run 99 item 6 says "investigate batch_runtime.py wiring — how many pending conversations? What's the WHERE clause? File GH issue after GH #399 resolved." Item 6 explicitly deferred to GH issue.

**Steelman for Idea 2:**
- batch_runtime.py is a cost-saving infrastructure investment (50% reduction on offline AI). conversation_enrichment_job.py is its first and only caller. No scheduling = zero ROI.
- The pattern is proven: appointment_jobs.py shipped the exact same way (PR #475, new scheduled/ file, added to scheduled_jobs.py). Effort is demonstrably small.
- This is an operational gap (shipped but unrun) vs a pending feature (not yet designed).

**Attack on Idea 2:**
- Mandate item 6 says "investigate... File GH issue after GH #399 resolved." This implies the nightly-commit-review SKILL.md channel or direct human session, not the subconscious winner for this run.
- Risk: conversation_enrichment_job.py may have its own rate controls, tenant iteration logic, or correctness requirements not yet validated. Scheduling it without reviewing its implementation first could silently process all conversations for all tenants in one batch.
- Correct channel: read the job's implementation first (WHERE clause, rate limits, idempotency), THEN schedule. This is a 2-step task, not 1-step. The subconscious recommends but doesn't implement — the implementation step is non-trivial enough to warrant human review before scheduling.
- Counter-verdict: Idea 2 is a VALID idea but its execution path requires a read-before-schedule gate. As a subconscious recommendation, it becomes: "Implement Step 9F this cycle; file a GH issue to schedule conversation_enrichment_job after reviewing its WHERE clause and rate controls."

**Verdict:** VALID but DEFERRED. Lower-risk as a GH issue than as this run's winner. Mandate item 6 already tracks it. Best treated as a supporting recommendation, not the top winner.

---

### Idea 3: platform_flags ALLOWED_TOGGLE_KEYS Guard
**Nightly trigger:** The 2026-07-19 nightly explicitly flagged this: "Minor concern: if a DB row is accidentally set to 0 for something like `voice_chat_max_tokens`, the Twilio/Claude call would receive `max_tokens=0` and fail."

**Steelman for Idea 3:**
- Nightly reviewer caught a real concern: platform_flags.py is new (PR #476, 2026-07-19), kill-switch semantics are not obvious, and misconfigured rows will cause silent/confusing failures.
- A frozenset of ALLOWED_TOGGLE_KEYS at the module level costs ~10 lines and gives a log warning when an invalid key is fetched. Pure insurance value.
- Future developers adding platform_settings rows can immediately see which keys are valid toggle targets.

**Attack on Idea 3:**
- Platform_flags.py has 0 production rows for non-toggle keys as of today. The risk is future risk, not present risk.
- Nightly labeled it "minor concern... no action required." Subconscious should respect nightly's own severity assessment.
- The guard would need the allowed key list hardcoded — and that list will need to grow as new flags are added. If someone adds a new flag and forgets to update ALLOWED_TOGGLE_KEYS, the guard itself becomes a nuisance (log noise or None returns for valid keys).
- Better mitigation: the comment in platform_flags.py already documents the risk ("only flag names that are feature toggles should be set in platform_settings"). That comment + nightly's observation is the right guardrail for now.
- Counter-verdict: Idea 3 protects against a known-future risk but the risk is not present and the guard has its own maintenance cost. Nightly itself called it "no action required."

**Verdict:** WEAK. Low present risk. Guard has maintenance cost. Nightly said no action required. Parking lot.

---

## Round 2: Head-to-Head

**Idea 1 vs Idea 2:**
- Idea 1 (Step 9F): 3 mandate cycles failed, mechanism now understood, ZERO implementation risk, channel is human-session direct edit — guaranteed to resolve on first human execution.
- Idea 2 (conversation_enrichment scheduling): Valid problem, but requires read-before-schedule gate, has potential correctness risk (tenant iteration, rate controls), and mandate item 6 already deferred it pending GH #399 resolution.
- **Winner: Idea 1.** Mandate pressure strongest, execution path clearest, no preconditions.

**Idea 1 vs Idea 3:**
- Idea 3 (platform_flags guard): Nightly said no action required. Future-risk guard with maintenance cost. Not mandate-tracked.
- **Winner: Idea 1** by default. Idea 3 doesn't contest.

---

## Round 3: Idea 1 Weakness Stress-Test

**"Is the channel-pivot insight actually new, or is this just a 4th carry-forward?"**

Genuinely new insight: Prior winning-concepts (runs 97, 98) said "this will be implemented by nightly-commit-review via SKILL.md-edit channel" — the same claim as Steps 9B-9E. This run's evidence-gathering revealed WHY that claim was wrong: Steps 9B-9E each triggered on a live problem (brain connector DOWN, KB stale at selection time). Step 9F has no live trigger because KB is healthy. The mechanism is categorically different. Prior runs didn't have this diagnosis — they assumed nightly would implement it. This run proves nightly cannot implement it under current conditions.

The channel-pivot from "autonomous nightly will add it" to "human session must paste it" IS the new insight. This is Run 99's contribution.

**"Will the human actually execute this?"**

The winning-concept.md file has the exact block. The implementation is 28 lines. The insertion point is `.claude/skills/nightly-commit-review/SKILL.md` after Step 9E (confirmed at lines 265-288). Human execution is a copy-paste operation with clear instruction. High confidence.

**"What if KB stays healthy for 90 days and the staleness check never fires? Is this wasted?"**

No. "Step 9F: KB autopopulate last run: 2026-07-13 (6 days ago)" appears in every nightly log. Observability is the primary value. The GH comment is secondary and fires only if KB goes stale >7 days. Persistent observability is valuable even when healthy.

---

## Final Verdict

**Winner: Idea 1 — Step 9F KB Autopopulate Staleness Check, Channel Pivot to Human-Session Direct Edit**

**Supporting recommendations (not the winner but included in backlog):**
- Idea 2: File GH issue to schedule conversation_enrichment_job.py after verifying WHERE clause + rate controls. (Tracked in mandate item 6; re-raise as actionable GH issue text)
- Idea 4: kb_hybrid enable for Keys Koffee via platform_flags DB row — human session with Supabase MCP.
- Idea 5: GH #413 final escalation comment — new framing (appointment-completion context now live).

**Parking lot:**
- Idea 3: platform_flags ALLOWED_TOGGLE_KEYS guard — no present risk, nightly said no action required. Revisit if a misconfigured row causes an incident.
