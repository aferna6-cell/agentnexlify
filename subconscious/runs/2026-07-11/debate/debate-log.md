# Debate Log — Run 88 (2026-07-11)

Top 3 ideas by evidence strength and impact: Idea 1, Idea 2, Idea 4.

---

## Idea 1: File "Booking Funnel Diagnostic" GH Issue

### Challenge
1. The nightly log at `ops/routines/logs/nightly-commit-review-2026-07-11.md` already contains the SQL query. Does yet another GH issue add signal the human hasn't seen?
2. Is 0 bookings really a technical issue? Real tenants might not have been directed to use the booking widget at all — the problem could be UX/onboarding, not a broken flag.
3. Two prior runs (87 + nightly 88 mandate check) already recommended this. Third recommendation without new evidence is a smell.

### Defend
1. The nightly log is a markdown file in a repo that the human accesses via Claude Code sessions — not via GitHub dashboard. A GH issue is visible on github.com where the human reviews tasks. The SQL being buried in a commit log file ≠ actionable. A GH issue with `revenue + human-action-required` labels cuts through.
2. Hypothesis testing IS the point. "Might be UX" is exactly why we need to run the diagnostic — to rule out the technical cause first. If booking_enabled is already true for all tenants, the issue body explicitly says "investigate widget UI booking flow next." The diagnostic closes the technical hypothesis efficiently.
3. This is NOT a repeated recommendation — prior runs recommended autonomous Supabase query (blocked by MCP gap). This run proposes a different mechanism: human-executed diagnostic package via GitHub issue. Mechanism change is evidence-based, not circular.

### Additional evidence for defense
- GitHub MCP IS available in this session (mcp__github__* tools in deferred list). Can file this issue NOW.
- Run 88 mandate explicitly includes tenant_availability as secondary hypothesis — this idea packages BOTH, not just booking_enabled.
- Impact is asymmetric: if booking_enabled=false on any real tenant, the first real booking happens the day of the UPDATE. Revenue ∝ days blocked.

**VERDICT: SURVIVES → WINNER**
Strongest evidence. Clearest ROI. Mechanism change from prior blocked attempts. Packages both hypotheses. GitHub MCP available for execution.

---

## Idea 2: P0 Pipeline Escalation — Dual-Blocker Day 7

### Challenge
1. GH #399 (AUTOPILOT_GH_TOKEN) has existed for 7 days with daily Step 9D comments. The human has seen it. A new escalation issue or comment doesn't change the priority for someone who's already seen it and hasn't acted.
2. GH #403 (ANTHROPIC_API_KEY) — is this actually a separate issue or just referenced in the nightly log? Needs verification before filing a new issue to avoid duplicating existing tracking.
3. The issue-to-pr-loop being stalled is operational debt, but it's not blocking any CURRENT production feature — the platform is live, widgets work, chat works. The urgency is "40 features in queue" not "production down."

### Defend
1. Day 7 is qualitatively different from Day 1. GH #399 was filed on Day 1 with normal priority. A P0 escalation comment with Day 7 language and 40-issue queue count is genuinely new signal. Day × queue-size is the urgency metric.
2. The ANTHROPIC_API_KEY issue IS new — nightly-2026-07-11 is the first mention. Whether it's captured in #403 or needs a new issue, filing/confirming it is clearly warranted.
3. The 40 queued issues include the Lead Source Analytics feature (GH #409) which is a run 85 winner still pending. The pipeline being stalled has direct product-roadmap consequences.

### Verdict calibration
This is a VALID idea but lower leverage than Idea 1 because:
- Step 9D is already doing daily comments on the stall (automated channel exists)
- Filing a new GH issue when #399 already exists creates noise
- The ANTHROPIC_API_KEY blocker is worth verifying/filing, but that's a Bonus Action — not the primary winner
- The fix is human-only regardless; a subconscious recommendation doesn't accelerate it beyond what Step 9D already provides

**VERDICT: WEAKENED → PARKING LOT**
Step 9D covers daily automation-pipeline monitoring. Subconscious doesn't add significant leverage here. Better as Bonus Action: add Day 7 escalation comment to #399, verify #403 exists.

---

## Idea 4: Add Step 9F to nightly SKILL.md — Tenant Availability Check

### Challenge
1. Steps 9A-9E all use Supabase MCP queries. If Supabase MCP is unavailable in the nightly headless session (confirmed by nightly-2026-07-11), Step 9F will also fail silently.
2. Is this premature? We don't know if booking_enabled=true for any real tenant. Adding a step for hypothesis B before hypothesis A is confirmed is inverted sequencing.
3. The tenant_availability table structure is unconfirmed. Step 9F might need to check widget_configs.booking_hours or a completely different table. Writing the step without schema verification risks a wrong-table query.

### Defend
1. The Supabase MCP gap may be fixable (Idea 3 targets this directly). Adding Step 9F now means it runs automatically when the MCP gap is resolved — otherwise we lose another cycle. However, if Step 9F is confirmed to fail silently, it's worse than useless — it gives false assurance.
2. The sequencing objection is valid but not decisive. Both hypotheses need to be tested. Even if hypothesis A (booking_enabled=false) is confirmed and fixed, we still need hypothesis B (tenant_availability hours) checked, because the problem might be compound. Adding Step 9F now vs next run is a 24h difference in investigation speed.
3. Schema uncertainty is a real risk. The SKILL.md step needs a `-- verify table name` comment and a fallback. Alternatively, the GH issue (Idea 1) can include tenant_availability SQL AS IS, letting the human verify/adapt. This is not a reason to add Step 9F prematurely with wrong schema.

### Verdict calibration
Step 9F is the right idea for AFTER:
- Idea 1 GH issue answers hypothesis A
- Human confirms booking_enabled=true for all tenants
- Supabase MCP availability in nightly sessions is confirmed

Premature now because MCP gap blocks it + schema unverified + hypothesis A unanswered.

**VERDICT: WEAKENED → PARKING LOT (run 89 candidate if human reports booking_enabled=true)**

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: Booking Funnel Diagnostic GH Issue | SURVIVES | WINNER |
| Idea 2: P0 Pipeline Escalation | WEAKENED | Parking lot + Bonus Action |
| Idea 3: Supabase MCP Gap Diagnosis | Not formally debated | Parking lot (run 89 candidate) |
| Idea 4: Step 9F Tenant Availability | WEAKENED | Parking lot (run 89 if booking_enabled=true confirmed) |
| Idea 5: Referral Reward Diagnostic | Not formally debated | Parking lot (carry-forward from run 87) |

**Winner: Idea 1.**

Rationale: Most direct path to answering the 0-bookings question. AUTONOMOUS-EXECUTABLE via GitHub MCP. Converts blocked autonomous audit (2 failed attempts) into human-executable diagnostic package. Packages both hypotheses. Asymmetric revenue upside.
