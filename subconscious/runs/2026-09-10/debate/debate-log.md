# Debate Log — Run 118 (2026-09-10)

Top 3 ideas ranked by impact: Idea 2 (CI gate), Idea 1 (god class split), Idea 3 (Step 9J reorder).

---

## Idea 2: CI Gate for Unmetered AI Calls

### Challenge Round 1
**Q:** This was explicitly KILLED in run 117 for a concrete reason: "30+ existing violations would fail CI immediately without a suppression baseline." Has that actually changed, or is this the same dead idea?

**A:** It has changed. PR #834 (committed 2026-09-10, hours before this run) ships exactly the mechanism that was missing: `check_backend_future_annotations.py` starts with `KNOWN_VIOLATIONS = {"test_website_connect.py", "test_local_seo_handlers.py", "test_os_invoice_e2e.py"}` — 3 files in the baseline — and CI passes because known violations are allowlisted. New violations fail CI. The same pattern applies directly: `check_ai_metering.py` already exists and outputs `path:function:line` triples; adding a `KNOWN_VIOLATIONS` set of all 30 current violations makes CI green on day 1 and blocks any new violation at PR time. The "no allowlist mechanism" objection is closed by empirical precedent, not theory.

### Challenge Round 2
**Q:** Step 9L is already being implemented (nightly detection + issue filing). Does a CI gate add marginal value, or is this redundancy for its own sake?

**A:** CI gate and nightly detection are complementary layers: CI catches at PR time (before merge), Step 9L catches after merge (on next nightly). A developer who adds a new unguarded AI endpoint sees the CI failure within minutes and fixes it before it merges — no GH issue needed, no human triage. Step 9L handles drift from the 30 existing violations being cleared over time. Together they give defense-in-depth. The future-annotations CI guard + nightly review are the analogous pair for `__future__` violations; the same two-layer model is already established.

### Challenge Round 3
**Q:** Is the risk calibration right? 30 violations as allowlist means the CI passes even if someone adds 10 new violations — they'd only need to keep them out of the file CI watches, which is trivially easy. Isn't this a false sense of security?

**A:** This is a real concern. The allowlist is named violations (path:function pairs), not a count floor. Adding a new function not in the allowlist fails CI regardless of how many are already there. The allowlist only excuses EXISTING known-bad entries, identical to the future-annotations pattern. The risk is someone adding to the allowlist without fixing the violation — but that's true of any allowlist mechanism and is a PR review concern, not a structural flaw.

**Verdict: SURVIVES** — PR #834 precedent resolves the core objection from run 117. Strong preventive value. S effort.

---

## Idea 1: os_tool_executions.py God Class Split

### Challenge Round 1
**Q:** The governance mandate binding ("run 118 winner if Step 9L confirmed") — is this actually binding, or is it governance self-suggestion that can be overridden with new evidence?

**A:** Governance mandates are binding in the subconscious system — they exist precisely to prevent the system from generating the same evidence loop indefinitely. Run 116 named this as the winner for run 118; run 117 confirmed it. Step 9L IS confirmed (grep=2). The mandate is satisfied. Overriding a governance mandate requires a concrete reason why the mandated winner is WRONG, not merely that another idea scores higher.

### Challenge Round 2
**Q:** M effort in a scheduled headless session is higher risk than S effort. os_tool_executions.py is a 783L service that runs the OS agent's tool execution pipeline. What happens if the split breaks an import path or the approval flow?

**A:** This is a legitimate concern. The recommendation is read-only — human implements after approval. The split itself is low-risk because: (1) the file is stable for 10d, (2) the three concerns (store/executor/approval) are clearly separated in the current code structure, (3) the OS tool execution pipeline has tests (os_workflows tests exist and pass). The risk of breaking something is real but manageable by a developer reading the split plan carefully.

### Challenge Round 3
**Q:** Is 783L actually causing bugs? The file hasn't had a commit in 10d. Maybe the god class rule is correct in principle but this specific file is fine.

**A:** The 10d stability is precisely why now is the right time — no active churn means the split can be done cleanly. The bug argument for god class splits isn't "this file has bugs NOW" but "as the file grows, bugs become harder to isolate and reviews become harder." At 783L, code review requires reading 783 lines of mixed concerns to verify a change in the approval flow. Rule 9 exists as a preventive threshold, not a post-bug measure.

**Verdict: SURVIVES** — Governance mandate binding, file stable enough for a clean split. Weakened by M effort in headless context (human-required implementation).

---

## Idea 3: Step 9J Token Budget Fix

### Challenge Round 1
**Q:** Reordering Step 9J earlier in the nightly changes the execution context for all later steps. What's the blast radius?

**A:** Step 9J only reads and potentially merges Dependabot PRs — it doesn't affect the commit list, bug detection, or issue-filing decisions in Steps 9C-9K. The nightly review of today's commits is completely independent of whether Dependabot PRs were merged earlier in the same session. The only interaction risk is if Step 9J merge triggers a CI run that affects something Steps 9C-9K would check — but Steps 9C-9K work against the commit history, not CI status.

### Challenge Round 2
**Q:** Is token budget actually the problem? Maybe 17/19 PRs skip because of CI status or labels, not budget.

**A:** run_112_mandate_executed explicitly confirms: "ROOT CAUSE: list_pull_requests creator filter unreliable in headless sessions." And run_113_mandate_executed confirms: "Step 9J skipped entirely ('No Dependabot PRs detected')." The 17/19 skip problem is distinct — it's about the processing budget after finding 19 PRs, where 17 hit the loop limit before being fully evaluated. The detection fix (search_pull_requests) was applied. The skip rate is about evaluation budget within the found set.

**Verdict: SURVIVES** — Clear mechanism, S effort, immediate security value. Lower impact than Ideas 1+2 because it only affects Dependabot PR throughput, not new violation prevention.

---

## Synthesis

| Idea | Verdict | Notes |
|------|---------|-------|
| CI gate for AI metering | SURVIVES → parking lot | Strong, S effort, new evidence. Not chosen because governance mandate binds Idea 1. Run 119 candidate. |
| os_tool_executions.py split | SURVIVES → **WINNER** | Governance mandate binding (run 116/117 both name this). Step 9L confirmed. M effort — human implementation. |
| Step 9J reorder | SURVIVES → parking lot | S effort. Run 119 candidate if Step 9J still skipping. |
| Step 9G cloud trigger fix | Not debated (bottom 2) | Strong parking lot candidate — operational impact is real. |
| AI-to-human handoff | Not debated (bottom 2) | Parking lot — customer value confirmed but insufficient implementation path. |
