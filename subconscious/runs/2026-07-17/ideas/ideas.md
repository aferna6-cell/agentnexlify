# Run 97 — 5 Candidate Ideas

Generated: 2026-07-17
Evidence base: nightly-commit-review-2026-07-17.md, git log last 24h, GH #399/#403/#413.

---

## Idea 1: Step 9F — KB Autopopulate Staleness Check in Nightly SKILL.md

**Category:** workflow / operational  
**Effort:** XS (5-line SKILL.md block addition)  
**AUTONOMOUS-EXECUTABLE:** YES — proven mechanism (nightly SKILL.md edits)

**Evidence:**
- KB dark 72+ days (last run: 2026-05-05, per governance run_89_corrections)
- GH #403 open tracking KB autopopulate stall — but no daily pressure signal fires on it
- Steps 9B, 9C, 9D, 9E all implemented in 1 nightly cycle each via same SKILL.md-edit channel
- nightly-2026-07-17: 0 bugs fixed, 0 service files created — SKILL.md edits are the viable autonomous path
- knowledge-base/log.md tracks last autopopulate run — checkable deterministically

**Mechanism:**
Add Step 9F to `.claude/skills/nightly-commit-review/SKILL.md`:
1. Read `knowledge-base/log.md` last entry date
2. Calculate `days_stale = today - last_run_date`
3. If `days_stale > 7`: post comment on GH #403 with staleness count + likely cause (token/API key rotation needed)
4. Log result in nightly commit log

**Why now:** KB has been dark 72+ days with no automated daily signal. GH #403 exists but gets zero pressure outside subconscious runs. This closes the alerting gap with a 5-line SKILL.md addition that the nightly can execute autonomously in 1 cycle.

---

## Idea 2: appointment_completion.py Delivery Mechanism Fix

**Category:** customer_value  
**Effort:** XS (file a GH issue with ai-ready label + implementation sketch)  
**AUTONOMOUS-EXECUTABLE:** PARTIAL — issue filing yes, implementation no

**Evidence:**
- appointment_completion.py ABSENT for 2nd consecutive nightly (nightly-2026-07-16: 0 fixes; nightly-2026-07-17: 0 fixes)
- Root cause identified: nightly is a bug-fix system, not a feature-implement system. Cannot create new service files from winning-concept.md
- Correct execution path: issue-to-pr-loop (stalled by GH #399) OR human interactive session
- Implementation sketch fully written in subconscious/runs/2026-07-16-pm/winning-concept.md
- 2 root-cause fixes already landed (6cc3419 booking URL + f143de5 reminder status filter) — appointment_completion.py is the last piece

**Mechanism:**
File GH issue titled "feat(booking): auto-complete past-confirmed appointments — appointment_completion.py" with:
- ai-ready label (so issue-to-pr-loop picks it up when GH #399 unblocks)
- Full implementation sketch from subconscious/runs/2026-07-16-pm/winning-concept.md
- 3 test cases documented
- Note: "Blocked on GH #399 AUTOPILOT_GH_TOKEN rotation"

**Why now:** Every day without appointment_completion.py, every appointment completes in real life but stays `confirmed` forever. Review requests never fire. Aftercare automations never trigger. The issue-filing path can prepare the work so it executes the moment GH #399 is resolved.

**Weakness:** Already filed as GH #454 in run 95. If that issue exists with ai-ready label, this idea is REDUNDANT. Check first.

---

## Idea 3: notify_common.py Failure-Mode Test Coverage

**Category:** code_health  
**Effort:** S (10-15 line test addition to existing test file)  
**AUTONOMOUS-EXECUTABLE:** YES — test file addition, proven nightly channel

**Evidence:**
- nightly-2026-07-17: "notify_common.py extracted shared skeleton (IdempotencyGuard, fetch_owner_alert_config, safe_send_email/sms, dispatch_owner_alert) from 3 copies" — 12 new tests added
- notify_common.py is now SPOF for all owner notification pathways (lead alerts, booking alerts, appointment customer notify)
- 12 tests added specifically for the skeleton but nightly log did not describe failure-mode coverage
- Three upstream callers now share single dispatch path — partial failure (e.g. safe_send_email returns False but dispatch_owner_alert does not propagate the failure signal) could silently drop notifications

**Mechanism:**
Add to `backend/tests/test_notify_common.py`:
- Test: `dispatch_owner_alert` returns error signal when `safe_send_email` fails (not raises, not silently drops)
- Test: `fetch_owner_alert_config` returns None → `dispatch_owner_alert` returns False (not raises)
- Test: `IdempotencyGuard` blocks duplicate dispatch for same event_id within TTL

**Why now:** New SPOF with 12 tests is better than old 3-copy design, but SPOF failure modes need explicit verification. A silent drop in `dispatch_owner_alert` would mean no owner learns about new leads or bookings.

**Weakness:** 12 tests already added in same nightly cycle — may already cover these cases. Requires reading test file before recommending.

---

## Idea 4: loop_health_scan.py Pagination Past 1000 Rows

**Category:** code_health  
**Effort:** S (15-20 line modification to existing service file)  
**AUTONOMOUS-EXECUTABLE:** YES — targeted bug-fix, nightly channel viable

**Evidence:**
- nightly-2026-07-17 explicitly flagged: "at >1000 active-paid-tenant drafts, stale rotting drafts in tail could be missed silently. Not a bug now — noted as scale concern for future."
- scripts/loop_health_scan.py committed as 03a682c, hard limit=1000 rows per REST query
- Agent OS currently serving 3 real tenants — limit=1000 not triggered yet
- Security fix already landed (a0a3457: SUPABASE_SERVICE_KEY no longer leaks in traceback)
- Pattern: paginate with `.range(offset, offset+batch-1)` loop until `len(rows) < batch_size`

**Mechanism:**
Replace single `.limit(1000)` call in loop_health_scan.py with paginated loop:
```python
BATCH = 500
offset = 0
rows = []
while True:
    batch = db.table("opportunity_suggestions")...range(offset, offset+BATCH-1).execute().data
    rows.extend(batch)
    if len(batch) < BATCH:
        break
    offset += BATCH
```

**Why now:** Named as future concern in nightly log. Low risk (additive, no behavior change at current scale). Better to fix before scale than after silent miss is discovered in prod.

**Weakness:** Not urgent. Nightly log explicitly said "not a bug now." May be premature optimization when 3 tenants exist.

---

## Idea 5: Escalation Decay Tracking in Governance

**Category:** workflow / operational (subconscious meta-improvement)  
**Effort:** M (governance.json update + memory.jsonl + SKILL.md edit)  
**AUTONOMOUS-EXECUTABLE:** PARTIAL — requires judgment on suppression thresholds

**Evidence:**
- GH #399: Day 15+, run 96 posted Day-14 escalation. Run 97 would be Day-15+ escalation. Same issue, same framing, diminishing marginal value.
- GH #413: Day 26+, 5 consecutive autonomous comments, 0 human responses. Each comment has lower incremental value than the last.
- Memory.jsonl already tracks "escalation posted" per run but no decay/suppression logic exists.
- Subconscious currently posts escalation comments on every run for unresolved issues — this could be noise if human is aware but blocked externally.

**Mechanism:**
Add to governance.json: `escalation_log: { "gh_399": { "last_comment_run": 96, "comment_count": 3 }, "gh_413": { "last_comment_run": 96, "comment_count": 5 } }`
Add to SKILL.md: "Skip escalation comment if `comment_count >= 5 AND days_since_last_comment < 7`."

**Why now:** 5+ comments on GH #413 with 0 human response suggests notification channel is wrong, not comment frequency. More comments = more noise, not more pressure.

**Weakness:** Suppressing escalation could mean a future run silently drops a critical alert. Threshold is arbitrary. This meta-improvement is lower value than external pressure signals.
