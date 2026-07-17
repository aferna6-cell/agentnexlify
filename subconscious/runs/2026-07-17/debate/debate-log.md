# Run 97 Debate Log — Top 3 Ideas

Date: 2026-07-17
Debating: Idea 1 (Step 9F), Idea 2 (appointment_completion mechanism fix), Idea 3 (notify_common.py tests)

---

## Idea 1: Step 9F — KB Autopopulate Staleness Check

### Round 1: Challenge

**Objection A — GH #403 already tracks this. Why add a nightly check?**
GH #403 is open and human-visible. The KB staleness is already known. Adding another automated comment on #403 is noise on an issue the human hasn't actioned. The subconscious has been posting escalation comments on stalled issues (GH #399, #413) for weeks with 0 human response. Why would a Step 9F alert on #403 be different?

**Objection B — KB dark 72+ days could mean kb-autopopulate.yml is broken at CI level, not a stale-data problem. SKILL.md check can only verify staleness, not cause.**
If the underlying issue is a missing ANTHROPIC_API_KEY secret or expired SUPABASE_ACCESS_TOKEN, a staleness comment on #403 just repeats what's already known without diagnosing root cause.

**Objection C — Step 9F is infra monitoring, not product improvement. No customer-facing value.**
The subconscious brief prioritizes customer_value > code_health > workflow. A nightly KB check is workflow/operational infrastructure — it doesn't move a booking funnel metric.

### Round 1: Defense

**Against A:** GH #403 gets zero daily pressure. The difference between subconscious-posted escalation comments (GH #399, #413) and Step 9F is that Step 9F fires on the nightly SKILL.md channel — EVERY night that KB is stale, the nightly log will contain a staleness entry. This creates a daily pressure signal in the nightly log that human sees passively when reviewing commits, vs a one-shot GH comment easy to ignore. More importantly: SKILL.md checks cost 0 tokens to run and generate machine-readable output in the nightly log. The GH comment is optional — Step 9F can fire a log entry even without a GH comment.

**Against B:** The SKILL.md block can note the likely cause (token rotation) without diagnosing it. The signal value is "KB is dark, here's the staleness count" — not root cause analysis. Same as Steps 9D/9E (loop stall detection, credential rotation schedule) which signal state without diagnosing internals. The human decides what to do.

**Against C:** KB feeds the AI chat system directly. Dark KB = AI responses degrade. This IS customer value — just one layer removed (dark KB → stale AI answers → lower lead qualification quality). Also the brief says "workflow" is a valid category. Step 9F is workflow/operational and directly supports agent_performance.

### Round 1 Verdict: SURVIVES — objections answered cleanly.

---

### Round 2: Challenge

**Objection D — Steps 9B/9C/9D/9E set a precedent but only work because nightly can EDIT SKILL.md files. The actual staleness CHECK requires reading knowledge-base/log.md and comparing dates. Does nightly actually do date arithmetic?**
The nightly reviews commits and runs tests. It doesn't read arbitrary files like knowledge-base/log.md. The SKILL.md block might not be executable by the nightly as written — the nightly would need to add a bash step that reads the log.

**Objection E — 72 days stale is extreme. If human hasn't fixed KB in 72 days, a staleness alert in the nightly log won't change behavior. This is 6th consecutive alert that gets ignored.**

### Round 2: Defense

**Against D:** Steps 9D and 9E both include bash steps in the SKILL.md block that read files and check conditions. Step 9D reads ops/credential-rotation-schedule.md. The pattern is: SKILL.md block contains bash logic that the nightly executes as part of its Step 9 checks. A bash one-liner like `tail -1 knowledge-base/log.md | awk '{print $1}'` reads the last timestamp. Date arithmetic is standard bash. The nightly executes bash. This is the same mechanism.

**Against E:** The question is not "will human fix it immediately" but "will the nightly log contain a signal that shows KB is dark?" Human reviewing the nightly commit sees the step-by-step log. "Step 9F: KB 72 days stale" is different from nothing, because: (a) it's machine-readable and could feed future dashboards, (b) it appears daily alongside other health checks creating pattern visibility, (c) the GH #403 optional comment surfaces it in the issue tracker for future reference. The issue is not that human ignores alerts — the issue is that no daily automated signal fires on KB staleness. This creates one.

### Round 2 Verdict: SURVIVES — mechanism is valid, value argument holds even if human response rate is low.

---

### Round 3: Challenge

**Objection F — Is there any risk of false positives? knowledge-base/log.md might have a format change or missing timestamp that causes the bash check to fail silently or emit wrong staleness count.**

### Round 3: Defense

**Against F:** The SKILL.md block should include a guard: `if [[ -f knowledge-base/log.md ]]; then ...`. If file missing or parse fails: log "KB log not found — cannot assess staleness" and skip GH comment. Zero risk of false positive comment if the guard is included. Nightly already handles partial failures gracefully (see Step 9E credential check — wraps in conditional).

### Round 3 Verdict: SURVIVES — 3 rounds, 0 fatal hits.

**STEP 9F RESULT: STRONG SURVIVOR.**

---

## Idea 2: appointment_completion.py Delivery Mechanism Fix (File GH Issue)

### Round 1: Challenge

**Objection A — GH #454 already filed in run 95. This idea is REDUNDANT if #454 has ai-ready label.**
The summary notes this weakness explicitly. If GH #454 was filed in run 95 with ai-ready label and implementation sketch, filing another issue would duplicate it.

### Round 1: Defense

**Against A:** Need to verify GH #454 status before determining if this idea has value. If #454 exists with ai-ready label and full sketch: IDEA IS DEAD — no action needed. If #454 is missing or lacks implementation detail: file it properly.

### Round 1 Check Required: Verify GH #454. If confirmed with ai-ready label → IDEA KILLED.

**Status check from evidence:** governance.json run_96_mandate_executed states "GH #454 open (filed run 95)." Run 95 mandate: "Parking lot candidates: BotHealthPage.jsx" — run 95 winner was appointment_completion.py itself. GH #454 was described as "open" but source of filing is unclear. Memory.jsonl run 95 (line 93) describes appointment_completion.py as the winner but does not confirm #454 filing.

**Conservative ruling:** Even if #454 exists, its status (ai-ready label, implementation sketch quality) is unverified. The idea's value depends on that check. Under constraint that this is an autonomous run without Supabase/GH interactive access in the way subconscious normally operates, defer to the evidence at hand.

**Evidence tilt:** governance.json explicitly says "GH #454 open (filed run 95)" — if filed in run 95, the issue exists. Two consecutive subconscious runs (95, 96) have recommended appointment_completion.py without filing a new issue. The issue is already filed. This idea's incremental value = ZERO if #454 has ai-ready label.

**Round 1 Verdict: WEAKENED — likely redundant with GH #454.**

### Round 2: Challenge

**Objection B — Even if #454 is properly filed, issue-to-pr-loop is dead (GH #399 blocks all 30 ai-ready issues). Filing or updating #454 produces zero autonomous execution until GH #399 is resolved.**

### Round 2: Defense

**Against B:** True. But filing correctly means the work is queued the moment GH #399 is resolved. The value is asymmetric: low effort to verify/update #454, high payoff when loop resumes.

**Round 2 Verdict: WEAKENED FURTHER — valid but lower-confidence value vs Step 9F.**

**IDEA 2 RESULT: WEAKENED — do not advance as winner. If GH #454 verified with ai-ready label and full sketch → execution-ready pending GH #399 resolution. Carry-forward in backlog.**

---

## Idea 3: notify_common.py Failure-Mode Test Coverage

### Round 1: Challenge

**Objection A — 12 tests already added in nightly-2026-07-17 for notify_common.py. We don't know if failure-mode tests are included without reading the test file. Recommending more tests might duplicate.**
nightly-2026-07-17 added 12 tests for "the skeleton" (IdempotencyGuard, fetch_owner_alert_config, safe_send_email/sms, dispatch_owner_alert). The new tests likely cover happy paths. Failure modes may or may not be covered.

**Objection B — notify_common.py is new but extracted from 3 copies that were presumably tested. The 89 existing tests passing validates the extracted behavior. SPOF risk is architectural, not testability gap.**
The three original callers (lead_alerts, booking_alerts, appointment_customer_notify) had their own tests. Extracting to shared code means those tests still cover the behavior through their callers. The SPOF concern is valid but testing dispatch_owner_alert in isolation may duplicate what caller tests already verify.

### Round 1: Defense

**Against A:** Unknown without reading test file. The 12 tests could be comprehensive or superficial. The fact that the nightly added 12 tests in the same commit that extracted the code suggests they were scoped to match extraction — likely happy-path verification of the extraction, not adversarial failure-mode testing.

**Against B:** Caller tests verify caller behavior, not shared skeleton failure semantics. If `dispatch_owner_alert` silently returns True on a partial failure (e.g. email sent but SMS failed), the caller test might not detect it because the caller only checks the return value, not that both channels succeeded. SPOF failure modes need isolation testing.

### Round 1 Verdict: SURVIVES but WEAKENED — valid concern but uncertain value without reading test file.

### Round 2: Challenge

**Objection C — notify_common.py SPOF is lower priority than Step 9F KB staleness alerting. Both are code_health/operational. Step 9F has HIGHER confidence (proven SKILL.md edit mechanism, 72 days of evidence, GH #403 context). notify_common.py has LOWER confidence (12 tests may already cover it, requires file read to verify gap).**

### Round 2: Defense

**Against C:** True. Cannot dispute priority ordering. This is a valid sub-winner that would be run 98 or later candidate.

**Round 2 Verdict: WEAKENED to runner-up.**

**IDEA 3 RESULT: WEAKENED — valid but lower priority than Step 9F. Runner-up. Promote to parking lot.**

---

## Synthesis

| Rank | Idea | Result | Reason |
|------|------|--------|--------|
| 1 | Step 9F — KB staleness check | **WINNER** | 3 rounds survived, proven mechanism, 72-day gap, zero risk |
| 2 | notify_common.py tests | Runner-up | Valid but may duplicate 12 new tests; parking lot |
| 3 | appointment_completion.py GH issue | Weakened | GH #454 already filed; incremental value unclear |

**WINNER: Step 9F**
