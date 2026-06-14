# Debate Log — 2026-04-30-pm (Run 11)

Top 3 by impact: Idea 1 (moratorium mandate + fresh recurrence evidence), Idea 2 (new eval harness, sprint risk), Idea 3 (run 8 unblock, naming discipline).

---

## Idea 1: JS Silent Catch Pre-commit Guard (Check 9) + AdminAnalyticsPage Fix

### Challenge Round 1
**Q: Is the evidence strong enough? Original violations are FIXED — maybe the problem is solved?**

Original violations at MarketingDashboardPage.jsx and LocalSEOPage.jsx were fixed by `e68677a` ~7 days ago. If the violations are gone, what problem are we guarding against?

### Defend
The fix is exactly the evidence FOR the guard, not against it. The violations were fixed manually — and within the same window, 6 NEW violations appeared in AdminAnalyticsPage.jsx:117-122. This is the classic "whack-a-mole" pattern. One-off patches don't hold because the pattern recurs in new files. The pre-commit guard is the system fix that breaks this cycle. The recurrence strengthens the case, not weakens it.

### Challenge Round 2
**Q: AdminAnalyticsPage is admin-only. Lower business impact than customer-facing widget. Why prioritize this?**

Admin analytics failures (overview, plan distribution, revenue trends) affect operator visibility. If these silently return null, the admin sees zeros or stale data — and may make wrong decisions about billing or tenant status.

### Defend
The pre-commit guard isn't just for AdminAnalyticsPage — it's for the NEXT file. The sprint with 21 issues is about to add more JS/JSX files. Some of those will touch customer-facing flows. Installing the guard before the sprint is the right timing.

### Challenge Round 3
**Q: This is the 4th consecutive run recommending the same thing (runs 8, 9, 10, 11). Is the signal degrading?**

### Defend
The moratorium exists precisely to create pressure for implementation. Each re-recommendation intensifies the signal. The governance correction (original violations fixed) gives the human a cleaner implementation path: fix AdminAnalyticsPage.jsx first (one file, 6 lines), then add the pre-commit guard with fresh context. The recommendation is actually EASIER to implement now than when first made.

### Verdict: SURVIVES → WINNER
Moratorium mandate holds. Fresh recurrence evidence in AdminAnalyticsPage. 21-issue sprint timing is urgent. S-effort.

---

## Idea 2: Wire golden eval harness to weekly CI schedule

### Challenge Round 1
**Q: Requires API keys + LEAD_QUALIFIER_AGENT_ID in GH Secrets. Setup overhead. Cost justified?**

### Defend
One-time setup. Weekly cost < $1. The eval is already env-var gated. Without CI, it will never run.

### Challenge Round 2
**Q: No lead qualifier regression in recent history. Is there actual risk?**

### Defend
Onboarding-v2 sprint (21 issues) may touch `managed_agents_registry.py` or `lead_qualification.py`. Without CI eval, regressions go undetected until tenant complaint.

### Challenge Round 3
**Q: Moratorium is active. Recommending this overrides the moratorium protocol.**

### Defend
The moratorium applies to code_health category backlog. Eval CI is agent_performance — different concern. However, overriding based on category distinction is a judgment call for the human, not the subconscious. Moratorium protocol is explicit in governance.json.

### Verdict: WEAKENED → Parking Lot
Moratorium protocol is explicit. Promote to run 12 winner once moratorium lifts.

---

## Idea 3: Fix em-dash + wire check_project_invariants.py

### Challenge Round 1
**Q: What exactly causes check_project_invariants.py to fail on WizardStepAutoKB.jsx? Is it a script bug or real violation?**

### Defend
Three locations: lines 140/172/254. Could be in JSX text content (valid em-dash) vs JavaScript identifiers (invalid). The fix path diverges depending on which: replace with hyphen/underscore OR update the invariants check to ignore JSX text. Either is S-effort but needs investigation first.

### Challenge Round 2
**Q: Moratorium priority: run 3 is older than run 8. Should run 8 wait for run 3?**

Yes — moratorium mandate is oldest-first. Run 3 (Apr 11) is older than run 8 (Apr 25).

### Verdict: WEAKENED → Parking Lot
Second priority after run 3. Promote to run 12 candidate once run 3 is implemented.

---

## Synthesis

- Idea 1: SURVIVES → WINNER
- Idea 2: WEAKENED → Parking lot (ROI 2.5, first post-moratorium candidate)
- Idea 3: WEAKENED → Parking lot (run 12 candidate)
