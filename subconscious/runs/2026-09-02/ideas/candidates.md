# Candidate Ideas — Run 117 (2026-09-02)

## Evidence Digest (≤200 words)
- **M8/Agent OS high-velocity sprint**: 26+ commits 2026-09-02 alone. Sales exact-email agent took 4 PRs (#741–#744) in 3 days to fix the same root cause: quote pairing when owner body contains apostrophes. Each PR added a test for one edge case but missed adjacent combinations.
- **Step 9K working**: nightly-2026-09-01 fired with 3 stale subconscious PRs (30–35d, below comment threshold). 2026-09-02: 4 stale PRs. Under threshold (need ≥5 or ≥1 critical >60d).
- **ai-ready loop still stalled**: nightly-2026-09-02 Step 9D: 4 issues total, 3 stale >24h (#669, #660, #643). AUTOPILOT_GH_TOKEN at 60d (valid — Step 9E: below 76d alert threshold). Loop not producing PRs despite valid token.
- **Step 9J**: Triggered @dependabot rebase on PR #721 + #722 on 2026-09-01. Skipped on 2026-09-02 (0 Dependabot PRs detected — likely resolved).
- **Brain connector 40d stale**: persistent, no human action on GH #684.
- **AUTOPILOT_GH_TOKEN at 60d**: Step 9E alert fires at 76d — 16 days away.
- **os_tool_executions.py 772L**: 5 commits in last 4 days — NOT stable. God class split deferred.
- **Branch context**: Branch already has runs 115 (2026-09-01) and 116 (2026-09-01-pm). This is run 117.

---

### Idea 1: Step 9L — ai-ready loop stall diagnostic block in nightly SKILL.md
**Evidence:** nightly-2026-09-02 Step 9D: 3 stale ai-ready issues (#669, #660, #643). AUTOPILOT_GH_TOKEN valid (60d). Step 9D surfaces stale issues but does NOT diagnose WHY the loop is stalled — no check on loop PR output, GH Action run history, or last successful loop cycle. Loop has been stalled despite valid token; root cause unknown. (Note: branch run 116 targeted connector auth scan; this is complementary — focuses on loop output rather than connector code.)
**Action:** Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9K. Block: (1) list PRs opened in last 14 days from issue-to-pr-loop (head.ref filter OR label filter); (2) if 0 loop PRs in 14 days: flag "LOOP STALLED" + comment on oldest stale ai-ready issue with diagnostic (token age, issue count, suggested GH Action check); (3) if loop PRs exist but issues stall: log "LOOP ACTIVE but N stale — possible label/claim filter issue"; (4) summary line: "Step 9L: loop {active|stalled} (N PRs in 14d), {stale_count} stale ai-ready".
**Impact:** Surface root cause of loop stall. Unblock 4 queued ai-ready issues. Each represents ~4–8h of queued Cursor/loop engineering time.
**Category:** workflow_efficiency

---

### Idea 2: Exhaustive quote-pair test matrix for sales_exact_email.ts
**Evidence:** 4 PRs (#741–#744) in 3 days, all fixing the same root cause in `agent-service/src/agent-os/agents/sales_exact_email.ts`. Each PR added a test for one edge case (single-quoted outer + apostrophe in content, double-quoted + apostrophe, etc.) but did not cover the full combination matrix. The result: 4 sequential regression cycles instead of 1.
**Action:** Add `test.each` parameterized suite to `sales_exact_email.test.ts` covering all 8 combinations: outer_quote ∈ {single, double, none} × inner_has_apostrophe ∈ {true, false} × send_type ∈ {exact, fallback}. Each case asserts no truncation and full body preservation.
**Impact:** Prevent next 3-PR regression cycle. Each cycle cost ~3h engineering time. Matrix test catches all combinations in one run.
**Category:** code_health

---

### Idea 3: Extract OAuth 401 refresh-once retry to shared backend utility
**Evidence:** commit 8a60a59 added 401 refresh-once retry pattern to `backend/services/gmail_connector.py`. M8 Calendar sprint is active and Calendar OAuth will face the same 401 scenario. Without extraction, two independent retry implementations will diverge.
**Action:** Create `backend/services/oauth_retry.py` with `def with_oauth_retry(fn, refresh_fn)`. Wire into `gmail_connector.py` immediately. Calendar connector adopts when M8 lands.
**Impact:** DRY principle on auth retry. Reduces future Calendar auth bugs. Consistent error handling across Gmail + Calendar.
**Category:** code_health

---

### Idea 4: Step 9E 60-day AUTOPILOT_GH_TOKEN advisory (supplement 76d alert)
**Evidence:** nightly-2026-09-02 Step 9E: "AUTOPILOT_GH_TOKEN ~60d, below 76 threshold". Alert fires at 76d (16 days away). Historically, expired token caused loop stalls for weeks (GH #399, ~55d stall). Adding a 60-day advisory (log-only, no comment) provides 30d lead time vs 14d.
**Action:** Edit Step 9E in nightly SKILL.md: add advisory log when token_age >= 60 AND < 76. Log: "⚠ ADVISORY: AUTOPILOT_GH_TOKEN at {age}d — alert threshold 76d. Schedule rotation within 14d."
**Impact:** 2-week earlier warning. Avoids repeat of GH #399 scenario where expired token blocked loop for 55+ days.
**Category:** operational

---

### Idea 5: "Hot file" tracker in nightly — multi-PR regression cycle detection
**Evidence:** sales_exact_email.ts received 4 fix PRs in 3 days. This pattern (3+ fix PRs on same file in 7 days) indicates a test coverage gap before it compounds. No current nightly step detects this.
**Action:** Add to nightly SKILL.md (after Step 9K): list PRs merged in last 7 days. Group by changed file. Flag files with 3+ fix PRs as "hot". Log: "Step 9L candidate: {file} touched {N} times by fix PRs in 7d — consider test hardening."
**Impact:** Proactive TDD gap detection. Catches brittleness before 5th or 6th PR.
**Category:** code_health
