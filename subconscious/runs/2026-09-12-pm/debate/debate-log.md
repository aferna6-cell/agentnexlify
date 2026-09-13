# Debate Log — Run 2026-09-12-pm (Run 122)

**Top 3 ideas debated:** Idea 1 (Step 9E countdown display + credential-identity dedup), Idea 2 (Step 9J limit=5), Idea 3 (GH issue tool outcome audit)

---

## Idea 1: Step 9E — Countdown Display + Credential-Identity Dedup

**Category:** workflow_efficiency / operational
**Effort:** XS
**Confidence entering debate:** HIGH

### Context from run 121 mandate check
Run 121 mandate item 4 asked: "AUTOPILOT_GH_TOKEN: at ~76d threshold — did Step 9E fire and GH #399 get a comment?" — status unknown. The SKILL.md Step 9E block (line 289) fires at `days_since_rotation >= 76`, which IS already the 14-day warning equivalent for a 90-day interval (76 = 90 − 14). Two gaps remain: (1) `days_remaining` variable is absent — humans reading the log see the rotation-day count, not how many days are left; (2) existing-issue dedup searches globally by the `credential-rotation` label, not by credential identity, so it can update/suppress the wrong tracker when multiple credentials are near rotation.

### Challenge
> "A previous session (run 121) marked this as PASS in its mandate check. If it's PASS, why is this still a winner? And the GH issue filing and dedup logic was added — doesn't that solve the urgent problem?"

### Defend
The GH issue filing was added — that part works. Two gaps remain. First, no `days_remaining` countdown: the existing `days_since_rotation >= 76` check is the correct 14-day warning (76 = 90 − 14), but humans reading the log line and GH comment see the rotation-day count, not a clear "14 days left" number. Computing `days_remaining = interval_days - days_since_rotation` and surfacing it as the display metric (`days_remaining <= 14`) is equivalent at the same firing point, but immediately legible. Second, dedup searches by `credential-rotation` label globally — if AUTOPILOT_GH_TOKEN and SUPABASE_KEY both hit the warning threshold in the same window, the dedup can match and update the wrong issue. Fix: search for an open issue whose title contains the specific token name (e.g., "AUTOPILOT_GH_TOKEN") to ensure each tracker is credential-specific. AUTOPILOT_GH_TOKEN is at ~70d as of 2026-09-12, expires 2026-10-02 — 20-day window to rotate once Step 9E fires on ~2026-09-18.

### Verdict: **SURVIVES** — Winner

Partial implementation exists; the remaining XS fix closes the inconsistency and adds the countdown visibility. Urgency is real (20 days to expiry). Directly addresses run 121 mandate item 4.

---

## Idea 2: Step 9J — Cap search_pull_requests to limit=5

**Category:** workflow_efficiency
**Effort:** XS
**Confidence entering debate:** HIGH

### Challenge
> "Same evidence as previous runs. If 19 PRs were found and 17 skipped, why isn't this the winner? Token budget exhaustion is a systemic issue — does limit=5 actually solve it, or just paper over it?"

### Defend
Evidence remains strong (runs 115-117 confirmed pattern). limit=5 is pragmatic — it doesn't solve the systemic token budget issue but ensures 5 oldest PRs get fully processed vs 2/19 currently. Security patches matter. Not the winner this run because Step 9E has higher urgency (credential expiry is time-bounded; Dependabot PRs are less time-critical). Parking lot is not rejection.

### Verdict: **PARKING LOT** — Promote to winner at run 123

---

## Idea 3: File GH Issue — Tool Outcome Coverage Audit

**Category:** code_health
**Effort:** XS (issue filing only)
**Confidence entering debate:** MEDIUM

### Challenge
> "Two email PRs in one day. Calendar/SMS/invoice/contact tools may not have the same gaps. Weak evidence for a class problem."

### Defend
Evidence from #841 + #844 is a signal but not proof. Filing the issue is XS and feeds issue-to-pr-loop with `ai-ready` label. But compared to Step 9E's time-bounded urgency, this is deferrable.

### Verdict: **WEAKENED** — Backlog suggestion only

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9E countdown display + credential-identity dedup | WINS | Run 122 winner — XS fix, adds clarity + closes dedup gap |
| Step 9J limit=5 | PARKING LOT | Run 123 candidate |
| GH issue tool outcome audit | WEAKENED | File opportunistically |
| SSRF redirect audit | Not debated | S effort, MEDIUM-LOW — defer |
| Skill freshness check | Not debated | M effort, LOW urgency — defer |

**Winner: Step 9E countdown display + credential-identity dedup**
