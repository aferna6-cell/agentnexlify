# Debate Log — Run 2026-09-12-pm (Run 122)

**Top 3 ideas debated:** Idea 1 (Step 9E threshold fix), Idea 2 (Step 9J limit=5), Idea 3 (GH issue tool outcome audit)

---

## Idea 1: Step 9E — Threshold Fix + days_remaining Display

**Category:** workflow_efficiency / operational
**Effort:** XS
**Confidence entering debate:** HIGH

### Context from run 121 mandate check
Run 121 mandate item 4 asked: "AUTOPILOT_GH_TOKEN: at ~76d threshold — did Step 9E fire and GH #399 get a comment?" — status unknown. The SKILL.md Step 9E block (line 289) still fires at `days_since_rotation >= 76`, while the issue title on line 294 says "≤14 days" — inconsistent threshold logic. `days_remaining` variable is absent from the block.

### Challenge
> "A previous session (run 121) marked this as PASS in its mandate check. If it's PASS, why is this still a winner? And the GH issue filing and dedup logic was added — doesn't that solve the urgent problem?"

### Defend
The GH issue filing and dedup (lines 290-299) were added — that part works. The remaining gap: (1) the trigger threshold `days_since_rotation >= 76` fires AT 76 days, giving ~14 days of warning before the 90-day rotation interval. The issue title claims "≤14 days" but the trigger logic doesn't compute days_remaining at all. (2) No days_remaining countdown in the log line or comment body. AUTOPILOT_GH_TOKEN is at ~70d as of 2026-09-12, expires 2026-10-02. With the current threshold firing at 76d (~2026-09-18), and expiry at ~2026-10-02, there's only 14 days buffer. If Step 9E fires correctly on 2026-09-18 nightly, that gives 14 days to rotate. The fix makes the title and trigger consistent (`days_remaining = interval - days_since_rotation`, fire when `days_remaining <= 14`) and adds the countdown to GH comments so humans see urgency.

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
| Step 9E threshold + days_remaining | WINS | Run 122 winner — XS fix, closes inconsistency |
| Step 9J limit=5 | PARKING LOT | Run 123 candidate |
| GH issue tool outcome audit | WEAKENED | File opportunistically |
| SSRF redirect audit | Not debated | S effort, MEDIUM-LOW — defer |
| Skill freshness check | Not debated | M effort, LOW urgency — defer |

**Winner: Step 9E threshold fix + days_remaining display**
