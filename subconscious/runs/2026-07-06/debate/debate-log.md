# Debate Log — Run 80 (2026-07-06)

Top 3 ideas ranked by impact + mandate precedence: Idea 1 (mandate fires), Idea 2 (customer value), Idea 3 (workflow quality).

---

## Idea 1: Step 9C — Brain Connector Health Check in Nightly SKILL.md

### Challenge Round 1
**Attack:** This is yet another meta-fix. The real problem is expired GitHub credentials and a missing env var. Adding more detection layers doesn't fix the root cause. GH #394 already filed (run 79). Why not just wait for the human to act?

**Defend:** The mandate fires unconditionally — run 79 governing rule states "if brain connectors still failing after next run: add Step 9C." Beyond mandate compliance, the issue is structural: brain connector credentials will expire again. GH #394 fixes the current instance. Step 9C prevents future instances from going 4+ days undetected. The monitoring gap (undetected Jul 1–4 before run 79 caught it) is the systemic problem, not just the current credentials.

### Challenge Round 2
**Attack:** The nightly-commit-review already detected this problem on Jul 5 (nightly log confirms). Is Step 9C redundant if nightly already catches connector failures by reading bot commits?

**Defend:** The nightly detection was incidental — the human-written nightly review happened to analyze the brain-refresh bot commit and noticed the ingestion log. Step 9C makes this SYSTEMATIC. The current nightly detection requires: (a) a brain-refresh bot commit occurring, (b) nightly review selecting that commit for review, (c) nightly reviewer connecting the bot commit to INGESTION-LOG.md contents. Step 9C runs unconditionally: read the log, count failures, escalate. It also deduplicates GH issues via the `brain-connector-failure` label check.

### Challenge Round 3
**Attack:** Could Step 9C spam GH issues if credentials are down for an extended period?

**Defend:** Explicit deduplication condition: Step 9C creates a GH issue ONLY IF no open issue with label `brain-connector-failure` exists. On first detection: creates issue. On subsequent nights: finds existing open issue, skips creation, logs "already escalated." No spam risk.

### Verdict: **SURVIVES** → WINNER
Mandate fires. AUTONOMOUS-EXECUTABLE (same class as Step 9B added by run 79). Closes monitoring blind spot. Deduplication prevents spam. Highest-confidence autonomous action this run.

---

## Idea 2: SMS Compliance Dashboard — GH Issue for Issue-to-PR Loop

### Challenge Round 1
**Attack:** Run 74 delivered complete paste-ready code blocks. The issue is not information — the human has everything they need. Creating a GH issue is yet another layer of indirection. Why would a GH issue get executed when 6 days of "here's the code" didn't?

**Defend:** The issue-to-pr-loop is a different execution channel than human manual implementation. It polls GH issues labeled `ai-ready` and executes autonomously. The human seeing "here's code" in a file requires them to open the file, copy-paste, and commit. The issue-to-pr-loop removes ALL human steps — it reads the issue, implements, opens a PR. Different activation energy.

### Challenge Round 2
**Attack:** Moratorium is active. Does creating a GH issue for SMS compliance add to the pending_approvals count?

**Defend:** GH issue for issue-to-pr-loop is NOT a subconscious pending_approval item. Subconscious pending_approvals track subconscious recommendations awaiting human approval. A GH issue in the issue tracker is an autonomous execution queue item — different system. Moratorium tracks the subconscious governance queue, not the GitHub issue queue. Moratorium-safe.

### Challenge Round 3
**Attack:** Has issue-to-pr-loop been confirmed running? Multiple prior runs raised doubts about the loop's operational status.

**Defend:** This is a valid concern. However, creating a well-formed `ai-ready` GH issue has zero downside: if the loop runs, it executes. If the loop doesn't run, the issue still exists for a human developer to pick up. The issue functions as both an autonomous trigger AND a human-readable spec. The risk of creating it is zero.

### Verdict: **SURVIVES** → Parking Lot
Valid execution path. Not chosen as winner because Step 9C mandate takes precedence (mandate-first rule, AUTONOMOUS-EXECUTABLE, same-run execution). SMS GH issue is the top parking lot item for next run if brain connector mandate is resolved.

---

## Idea 3: Add brain/INGESTION-LOG.md to Subconscious Phase 2 Evidence Sources

### Challenge Round 1
**Attack:** Step 9C (nightly detection) already solves the brain data staleness problem. Adding a brain check to subconscious evidence gathering is redundant overhead. When credentials are fixed, this check becomes permanently benign.

**Defend:** The concerns are different. Step 9C detects failures and creates GH issues. The subconscious evidence check is about IDEATION QUALITY — if the brain is stale, the subconscious should know BEFORE proposing ideas that depend on brain data (issues, PRs, schema state). Runs 77 and 78 ideated without knowing the brain was stale. This is a reasoning quality improvement, not a detection tool.

### Challenge Round 2
**Attack:** How many subconscious ideas actually depend on brain data? The evidence gathering phase already reads git log, bug-patterns.md, customer-gaps.md, skill-discovery. Brain data adds incremental value.

**Defend:** Brain data provides open issues (GH 403 blocked), PR state, and schema decisions. Without it, runs 77 and 78 couldn't have detected the Zapier fix as "implemented" (they had to manually verify). With stale brain data, governance corrections take longer. The value is real but marginal vs the mandate-fires Step 9C.

### Challenge Round 3
**Attack:** Editing the subconscious SKILL.md creates complexity in the core skill. Every subconscious run already reads 6+ evidence sources. One more adds context overhead.

**Defend:** The addition is 3 lines in the evidence commands block. Low complexity. But versus Step 9C's mandate + AUTONOMOUS-EXECUTABLE status, this ranks lower.

### Verdict: **WEAKENED** → Parking Lot
Valid workflow improvement but Step 9C wins on mandate precedence + autonomous execution. Promoted to parking lot for run 81.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9C: Brain connector health check in nightly SKILL.md | SURVIVES | **WINNER** |
| SMS Compliance Dashboard → GH issue for issue-to-pr-loop | SURVIVES | Parking lot |
| Brain check in subconscious evidence phase | WEAKENED | Parking lot |
| Morning digest brain freshness (Idea 4) | Not debated | Parking lot |
| check_project_invariants.py brain freshness (Idea 5) | Not debated | Rejected (commit-time invariant wrong layer for operational monitoring) |
