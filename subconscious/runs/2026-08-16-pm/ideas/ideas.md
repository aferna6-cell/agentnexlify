# Run 105 — Candidate Ideas (2026-08-16-pm)

## Evidence Digest (input to ideation)

- Run 104 winner (SUPABASE_ACCESS_TOKEN rotation schedule) IMPLEMENTED by nightly-2026-08-16
- GH #661 filed for scoring_config.py missing block_demo_role (2nd confirmed security gap)
- route-security-guard-audit SKILL.md: 3rd carry-forward → run_105_mandate mandates ESCALATE
- CRITICAL structural finding: 7 commits orphaned in detached HEAD, never pushed to origin
- KB still 24+ days stale; Step 9G triggers but ANTHROPIC_API_KEY missing in GH Actions blocks compile
- 130+ routers in backend/routers/ — most unaudited for block_demo_role
- Confirmed guard coverage: billing.py, billing_usage.py, account_deletion.py, auth_billing.py, phone.py
- Confirmed guard missing: appointment_briefs.py (GH #643, 8d), scoring_config.py (GH #661, 0d)

---

## Idea 1 — Create route-security-guard-audit SKILL.md

**Category:** code_health  
**Effort:** S  
**Confidence:** HIGH  
**Status:** CARRY-FORWARD (3rd cycle) → AUTONOMOUS-EXECUTABLE per run_105_mandate

**Evidence:**
- 2 confirmed routers missing block_demo_role in 2 runs (appointment_briefs.py GH #643, scoring_config.py GH #661)
- 130+ backend/routers/ files, most unaudited
- Pattern is recurring — new routers added without systematic guard check
- Full SKILL.md content written in subconscious/runs/2026-08-11-pm/winning-concept.md
- run_105_mandate: "ESCALATE to AUTONOMOUS-EXECUTABLE if still unimplemented"
- Subconscious precedent: run 99/Step 9F → run 101 direct impl after 3 cycles

**Why it wins:** Direct mandate from governance. Systematic detection vs one-off GH issues. 2 data points confirm the pattern. Implementation content ready.

---

## Idea 2 — Add Step 9J: Orphaned-Commits Detector to Nightly SKILL.md

**Category:** operational_efficiency  
**Effort:** XS  
**Confidence:** HIGH  
**Status:** RECOMMENDED

**Evidence:**
- Today's nightly-2026-08-16 found 7 commits in detached HEAD, never pushed to origin
- Manual detection only — no automated alerting existed
- 7 commits span 3 days (2026-08-13 to 2026-08-16), all orphaned
- git log origin/main..HEAD shows gap; detection is a single bash command
- Without alerting, future runs could accumulate orphaned commits silently

**Implementation:**
```bash
# Step 9J: Orphaned commits check
orphan_count=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
if [ "$orphan_count" -gt "0" ]; then
  # Log + file GH issue if persistent (>2 nights)
fi
```

---

## Idea 3 — Implement appointment_briefs.py block_demo_role Fix

**Category:** security  
**Effort:** XS  
**Confidence:** HIGH  
**Status:** PENDING-APPROVAL (security code, requires human review)

**Evidence:**
- GH #643 open 8+ days; demo tenants can call appointment brief endpoints
- block_demo_role pattern confirmed: billing.py:33, billing_usage.py:54
- Implementation mechanical: import + Depends() on 4 endpoints
- GH #661 (scoring_config.py) filed same day — 2 unguarded routers now open

**Why it doesn't win:** Security code → requires human review. GH issue already filed. Nightly cannot apply this autonomously. route-security-guard-audit SKILL.md is higher leverage (prevents future gaps).

---

## Idea 4 — Wire PR #653 Draft → Ready-for-Review

**Category:** operational_efficiency  
**Effort:** XS  
**Confidence:** HIGH  
**Status:** BONUS-ACTION

**Evidence:**
- PR #653 draft 8+ days (backlog item #5 from run 104)
- Title: "subconscious: runs 102-106 — route-security-guard-audit SKILL.md + appointment_briefs.py fix"
- This run implements the SKILL.md portion (completing first item in PR title)
- Marking ready signals to human: SKILL.md shipped, appointment_briefs.py fix still needs approval

**Note:** Only appropriate after this run's SKILL.md implementation is pushed to the branch.

---

## Idea 5 — Add Step 9K: Draft PR Staleness Alerter

**Category:** operational_efficiency  
**Effort:** XS  
**Confidence:** MEDIUM  
**Status:** RECOMMENDED

**Evidence:**
- Multiple subconscious PRs stale: #606 (19d+), #611 (14d+), #613 (11d+), #626 (12d+)
- PR #653 now 8+ days draft
- No automated alerting for aged draft PRs
- Pattern: human doesn't know PRs need attention until subconscious mentions it

**Threshold:** Draft PR > 14 days → nightly logs warning + optional GH comment
**Note:** Step 9K would complement the existing Steps 9C/9E/9F series.
