# Debate Log — Run 58 (2026-06-14-pm)

Top 3 ideas ranked by impact: Idea 1, Idea 2, Idea 5.

---

## Idea 1: Wire check_project_invariants.py as Check 10 (AUTONOMOUS-EXECUTABLE)

### Round 1 Challenge
Check 2 already guards `from __future__ import annotations` in FastAPI router files.
Does Check 10 add enough incremental value to justify adding another 6 seconds to
every commit? Pre-commit already has 9 checks — developer friction compounds.
Also: `check_project_invariants.py` itself was just modified by `3234597` to fix
its own logic. Is it stable enough to be a gate?

### Round 1 Defend
Check 10 guards 4 things NOT covered by any existing check:
- **Widget sync across 3 copies** — Check 2 doesn't touch widgets. PR #254 just
  caused drift that required a manual fix (run 57 winner). Without Check 10, the
  next multilateral widget PR drifts silently.
- **Banned column names** (`tenant_id` not `client_id`, `lead_stage` not `status`,
  `service_interest` not `areas_of_interest`) — ZERO other guards exist. CLAUDE.md
  says "we've shipped production bugs from this 3+ times."
- **Retired plan names** (`foundation`, `operations`) — no other check.
- **LLM calls via runtime wrapper** — no other check.
Check 2 handles from __future__ but only in backend/ routers. Check 10 catches it
project-wide. Script stability: `3234597` updated it to work correctly — it now
exits 0 cleanly, confirmed live this run. 6 seconds is justified for preventing
the class of bugs that dominated 58 runs.

### Round 2 Challenge
Is this really AUTONOMOUS-EXECUTABLE? The nightly review channel broke twice on
Idea 40 (nightly couldn't edit Python scripts). Bash hook additions succeeded
(Check 11, Check 12). This is a bash addition to pre-commit — correct class. But
what if check_project_invariants.py is slow? Long-running scripts in pre-commit
degrade developer experience severely.

### Round 2 Defend
Execution time measured (not directly, but inferred): script does 6 grep/find
operations on the codebase. Typically <2 seconds. Check 11 (22 lines bash) and
Check 12 (20 lines bash) were both autonomously added and have caused zero
developer experience complaints. The class is correct: bash file addition to
pre-commit = AUTONOMOUS-EXECUTABLE per 4226ef4 precedent. Python script edits
≠ this; bash file edits = this.

### Round 3 Challenge
Idea 3 (check-widget-sync.sh) covers the widget sync concern independently. If
both are recommended, do we need both? Does Check 10 render Idea 3 redundant?

### Round 3 Defend
Yes — Check 10 largely supersedes the widget sync portion of Idea 3. But Check 10
runs at pre-commit; check-widget-sync.sh was designed for pre-push. Different timing.
However, Check 10 at pre-commit is STRONGER (catches drift before commit, not just
before push). So Idea 3 becomes a secondary reinforcement, not primary. Idea 1 wins
this comparison.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: Verify integration encryption backfill for existing tenants

### Round 1 Challenge
We don't know if production has any tenant integrations yet. The platform is
pre-launch or just launching. If zero tenants have connected Google/Meta/Twilio
OAuth integrations, there are zero rows to backfill and the urgency is purely
theoretical. Is this chasing a security problem that doesn't exist in practice?

### Round 1 Defend
Commit 9f9203d references "GH #129, #131, #264" — these are numbered issues that
have been open for a while. GH #264 was filed BEFORE the fix, suggesting this was
observed behavior, not preemptive. `managed_agents/preflight.py` was updated in
the same commit — this file runs before agent tasks, implying agent tasks that USE
integrations (channel connectors: Instagram, etc.). `channels_instagram.py` (PR #232)
connects OAuth tokens. If Instagram integration exists for even one tenant, their
token is plaintext in the database until the backfill runs.

### Round 2 Challenge
The backfill script already has `--dry-run` and is designed to be run at any time.
This is the correct implementation of Rule 8 (no half-migrations — sunset migration
comes later). The subconscious job is to recommend improvements, not to manage
deployment operations. Is "run the backfill" a subconscious recommendation or an
ops task that belongs in the deployment runbook?

### Round 2 Defend
Valid point. The subconscious should recommend adding a CI VALIDATION (not running
the backfill itself). The check would be: in the test suite or a CI step, verify
`SELECT COUNT(*) FROM integrations WHERE access_token IS NOT NULL AND access_token_enc IS NULL`
returns 0 (or warns if not). This converts an ops responsibility into an automated
gate. That's a genuine improvement.

### Round 3 Challenge
Adding a live database query to CI requires production DB access from CI, which is
a security anti-pattern. Alternatively, it requires a separate testing DB that may
not have representative data. The schema-sync-check.yml already does column
existence checks — extending it to data validation is a different class of problem.
Is the complexity justified?

### Round 3 Defend
The complexity argument is sound. Checking data values in CI is substantially
harder than checking schema. The simpler path is adding a note to `schema-log.md`
migration 148 entry documenting that `backfill_integration_encryption.py` must be
run before the sunset migration, AND optionally a `scripts/managed_agents/preflight.py`
warning if encryption isn't configured. But this doesn't rise to subconscious winner
level — it's ops documentation. The stronger systemic fix is Check 10 (Idea 1).

**Verdict: WEAKENED → Parking Lot (valid, ops-docs level, not highest-leverage right now)**

---

## Idea 5: AI-to-Human Handoff v1

### Round 1 Challenge
This has been recommended as winner or parking-lot in 15+ runs without implementation.
The rejected_paths note says "mechanism: 3x recs without action → demoted to parking lot"
for the GH issue mechanism. Is there genuinely new evidence that makes this
implementable NOW versus any prior run?

### Round 1 Defend
Two pieces of new evidence: (1) PRs #252/#254 shipped "approve-by-text" and "SMS
approval alerts" using `os_outbound_mirror.py` — this is production-tested delivery
infrastructure for exactly the notification needed. (2) The moratorium appears to
be exiting after governance corrections this run (runs 55/57/51/34 all IMPLEMENTED).
Post-moratorium, customer_value winners are the natural next direction. 58-day gap
makes this the #1 customer value item by far.

### Round 2 Challenge
"Appears to be exiting" is not "has exited." Governance.json still shows
`moratorium_active: true`. Prior runs 21/29/38 all tried AI-to-Human Handoff
during moratorium with MEDIUM confidence and zero implementation. Pattern: human
reviews, considers the ~1 day scope, deprioritizes in favor of shorter tasks. Has
the scope actually shrunk to make it plausible?

### Round 2 Defend
Scope shrunk meaningfully: before Agent OS (PR #188), you'd build Twilio plumbing
from scratch (~3 days). After PR #188, you call `os_outbound_mirror.send_sms()`.
After PR #254 "approve-by-text" confirmed that exact call pattern works in production.
Scope is now: (a) add trigger detection to widget_chat.py (~50 lines), (b) update
lead status (~5 lines), (c) call existing `os_outbound_mirror` function. ~1 day
total, most of which is the trigger phrase list + testing.

### Round 3 Challenge
Even at 1 day scope, this has never been implemented despite multiple recommendation
cycles as MEDIUM-confidence. The pattern suggests the bottleneck is not information
or scope clarity — it's priority allocation. Recommending it again, even with new
evidence, risks the same outcome. Is Idea 1 (6 lines bash, AUTONOMOUS-EXECUTABLE,
zero human intervention needed) a stronger winner choice precisely because it
bypasses the human prioritization bottleneck?

### Round 3 Defend
Yes — Idea 1 bypasses the bottleneck entirely. Idea 5 (AI-to-Human Handoff)
requires 1 day of human implementation. Idea 1 executes autonomously tonight.
The self-sealing invariant system also has downstream value: it protects the
AI-to-Human Handoff code once implemented. Idea 5 is parking lot — correct
prioritization.

**Verdict: WEAKENED → Parking Lot (customer_value priority post-moratorium, but
loses to Idea 1 on implementability and blocking-vs-enabling logic)**

---

## Summary

| Idea | Verdict | Notes |
|------|---------|-------|
| Idea 1: Check 10 wire | SURVIVES → WINNER | AUTONOMOUS-EXECUTABLE, seals invariant system, 55d overdue |
| Idea 2: Encryption backfill | WEAKENED → Parking Lot | Ops-docs level, not systemic enough for winner slot |
| Idea 5: AI-to-Human Handoff | WEAKENED → Parking Lot | Valid customer_value, blocked by prioritization pattern |
