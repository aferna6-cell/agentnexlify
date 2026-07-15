# Debate Log — Run 95 (2026-07-15-pm)

Top 3 by impact: Idea 1 (booking URL test gate), Idea 2 (Step 9F staleness check), Idea 3 (Attribution Dashboard issue).

---

## Idea 1: Regression test — booking URL in widget AI prompt

### Challenge Round

**C1: Is the evidence strong enough?**
The booking URL fix just landed (commit 6cc3419, ~hours ago). We don't yet know if it caused first real bookings. Maybe there are more blockers (Keys Koffee still has no hours). The evidence for the bug is strong but the evidence that a test is the highest-ROI response is weaker — couldn't the PR just have included the test at time of fix?

**C2: Is this the right scope?**
The widget AI prompt is assembled from multiple sources (KB, business hours, booking config, tenant settings). A test that asserts "booking URL present in prompt" might be brittle — the URL format could change, the injection path could change. We'd be testing implementation details, not behavior.

**C3: Has something similar been tried and rejected?**
No — booking tests haven't been specifically addressed before. The closest is widget_guard tests added in PR #431.

**C4: Is this too close to the active direction?**
Run 94 winner was widget_guard LRU fix (implemented). Run 95 winner territory is free. No conflict.

**C5: What could go wrong?**
The test might need to mock the booking URL generation or Supabase tenant config. Badly written test → flaky test → pre-commit check randomly fails → developers start ignoring the check. The test author needs to understand how booking URL is injected into the prompt.

### Defend Round

**D1:** The evidence is exactly right. This is not a speculative risk — 6cc3419 shows a real 24-day bug with exact file and line context. A regression test is the canonical response to a specific bug. We're not premature — we're writing the test the PR should have included.

**D2:** The correct test scope is behavioral: "when booking_enabled=True, the AI system prompt passed to Claude includes a URL matching the booking endpoint pattern." That tests the contract (URL injection ON/OFF), not the specific URL format. Mock `widget_configs.booking_url` as a fixture — not brittle.

**D3:** This is the third silent failure in 3 days: auto-send toggle (5 of 7 agents silently wrong, 97a6512), appointment reminders dead (f143de5), booking URL absent (6cc3419). None had tests. The pattern is clear and immediate.

**D5:** Test can be simple: mock `widget_config` with `booking_enabled=True, booking_url="https://book.example.com"`, call the prompt assembly function, assert `"https://book.example.com"` appears in the result. Low brittleness. Same pattern as existing KB injection tests.

### Verdict: **SURVIVES → WINNER CANDIDATE**
Strong evidence, clear scope, directly prevents recurrence of a just-fixed critical bug. Autonomous-executable via nightly code channel.

---

## Idea 2: Step 9F — nightly infra staleness escalation check

### Challenge Round

**C1: Is the evidence strong enough?**
GH #399 and #403 have 4 and 2 comments respectively, all from autonomous systems. 13 days without human response. Adding more automated comments via Step 9F is the same mechanism that's already not working. Why would Day 14 comment work when Day 10 didn't?

**C2: Is this the highest-leverage thing?**
The infra blockers are human-action-required. The humans aren't responding to GH comments. Step 9F adds more comments — mechanism already demonstrated insufficient. The problem isn't that humans don't know. The problem is that humans are choosing not to act right now (perhaps on vacation, perhaps prioritizing other work). More comments ≠ action.

**C3: Is this too similar to active directions?**
Step 9D (run 83, implemented) checks ai-ready issues. Step 9E (run 84, implemented) checks credential expiry proactively. Step 9F is a third monitoring step in a month — risk of nightly SKILL.md bloat.

**C4: What could go wrong?**
Nightly SKILL.md growing unwieldy. 6 steps + new step = long check list. Risk that nightly review starts spending more time on monitoring than on fixing. False positives if a legitimate long-running issue gets labeled escalated unnecessarily.

### Defend Round

**D1:** Comments alone aren't the step — Step 9F's value is the `critical` label escalation at Day 14. That's a different signal in GitHub's issue list. A human doing triage sees `critical` filter differently than `human-action-required`. Marginal mechanism upgrade, not pure repetition.

**D2:** Nightly infrastructure monitoring growing is a system that's working. Steps 9B→9E were all implemented autonomously and provide real operational value (healthz alerts, credential rotation schedule, loop health check, brain connector check). Step 9F is the same class of work.

**D3:** Even if the specific issues (#399/#403) don't respond, Step 9F prevents future infra blockers from going 13+ days without escalation.

### Verdict: **WEAKENED — PARKING LOT**
The core argument stands but the specific application (GH #399/#403 already at Day 13 with no response) reduces marginal value of adding Step 9F right now. Both issues are already well-escalated. Step 9F has more value as a general future-issue guard. Demote to parking lot; promote in a future run after GH #399/#403 resolve.

---

## Idea 3: File Attribution Dashboard GH issue with ai-ready label

### Challenge Round

**C1: Is the evidence strong enough?**
attribution.py from PR #431 is 5 days old. We haven't verified the router endpoint exists and returns the right data structure. If the GH issue is filed with ai-ready and the loop picks it up, it might hit an API that doesn't exist or returns different fields than expected. Filing without verifying endpoint completeness risks a bad AI implementation.

**C2: Is this the highest-leverage thing?**
The loop is blocked by GH #399 and #403. The ai-ready label means nothing until those are fixed. Filing an issue now vs. in 2 weeks when the loop is back makes no meaningful difference to the outcome.

**C3: Has this been tried before?**
Run 85 already filed the Lead Source Analytics GH issue with ai-ready label (active_directions, status pending_autonomous). This idea is a duplicate at a different scope (attribution vs. lead source). Two different-scope issues in the same queue category.

**C4: What's the failure mode?**
Issue gets picked up by the loop, loop implements AttributionPage.jsx referencing endpoints that don't exist → PR opens with broken frontend → review bounce → loop stalls again.

### Defend Round

**D1:** PR #431 commit shows attribution.py and migration 172 in prod. The attribution router is likely complete — we can verify with a quick grep.

**D2:** The XS effort of filing now vs. later is real. Filing now means it's in the queue immediately when GH #403 is fixed. If we don't file, it needs another subconscious run to file.

**D3:** This is distinct from Lead Source Analytics (run 85 issue). Lead source is a specific column; attribution covers the full campaign/source/medium attribution chain. Not a duplicate.

### Verdict: **WEAKENED — BONUS ACTION**
The issue is worth filing but as a bonus action in Phase 6, not as the run's winner. Low risk, low effort, but low bang-per-run-winner slot. Better as a parallel bonus than the primary recommendation.

---

## Final Ranking

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1: Booking URL regression test | **WINNER** | Direct prevention of just-fixed critical bug; nightly autonomous; 0 brittleness risk |
| Idea 2: Step 9F staleness check | WEAKENED → parking lot | Low marginal value at Day 13 for existing issues; better future-state value |
| Idea 3: Attribution Dashboard issue | WEAKENED → bonus action | Worth doing, not worth winner slot; loop blocked anyway |
| Idea 4: BotHealthPage.jsx issue | Not debated — loop blocked | Parking lot; promote when GH #399/#403 resolve |
| Idea 5: KB refresh script | Not debated | Operational; promote in a dedicated operational run |
