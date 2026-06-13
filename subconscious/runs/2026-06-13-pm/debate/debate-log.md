# Debate Log — Run 2026-06-13-pm

Debating top 3 ideas by impact: Idea 1 (Check 10 wire), Idea 4 (AI-to-Human Handoff), Idea 3 (email_sequences split).

---

## Idea 1: Wire check_project_invariants.py to pre-commit as Check 10

### Round 1 — Challenge
**Is the blocked condition actually cleared?** The pre-commit already has CHECK 2 for `from __future__`
(line 49). check_project_invariants.py also checks from __future__. Isn't this just adding overlap
without new protection? Also: why didn't this wire automatically — the nightly SKILL.md was supposed
to handle this after check_project_invariants.py exits 0.

### Round 1 — Defense
Two separate layers, not redundant:
- CHECK 2 is grep-based; check_project_invariants.py uses AST (more reliable, per PR #257
  "anchor __future__ grep" fix). The AST version catches cases grep misses.
- check_project_invariants.py also checks: widget byte-identity (4 paths), retired field names
  (`lead_stage`, `service_interest`), em-dash UI strings, plan name retirement — none of which
  CHECK 2 covers.
- Nightly SKILL.md would execute this automatically, but relies on governance.json
  `pending_autonomous` label. Run 8's item was labeled `subsumed_in_sprint` until run 42 changed it.
  Run 42's label change was correct; nightly just hasn't fired yet because Check 10 wiring
  requires confirming exits 0 first — which just became true today.

### Round 2 — Challenge
**50 days is long. Why now rather than runs 22, 43, 44, 45?** The pattern is: every time this gets
recommended, there's a new blocker (em-dash violation, AUTONOMOUS-EXECUTABLE label missing, Python
script outside autonomous scope). Won't the same happen tonight?

### Round 2 — Defense
Prior blockers:
- Runs 22/23: `subsumed_in_sprint` governance label blocked autonomous path. Fixed by run 42.
- Runs 44/45: AUTONOMOUS-EXECUTABLE label was wrong — Python script edits outside nightly scope.
  But Check 10 is a BASH addition to scripts/hooks/pre-commit, not a Python script edit.
  Same class as Check 11 (061582c) and Check 12 (ca3ce68), both wired autonomously.
- Run 43 (4226ef4): Nightly SKILL.md was extended to cover pre-commit bash additions. This is the
  same class. No new blockers exist.

The 50-day delay was accumulated from governance label confusion + Python-vs-bash distinction.
Those are both resolved. The blocked condition (exits 0) is now confirmed. No remaining blocker.

### Round 3 — Challenge
**What if PR #258 or tonight's commits introduce a new invariant violation, making the
check_project_invariants.py fail again before nightly can wire it?**

### Round 3 — Defense
This is the exact argument FOR wiring Check 10 urgently. If new violations can appear tonight,
having Check 10 in pre-commit PREVENTS them. Not wiring it leaves the system vulnerable.
The launch-readiness sprint (50 commits/7 days) means high commit velocity = high violation risk.
Check 10 should be wired BEFORE the next round of commits, not after.

**Verdict: SURVIVES → WINNER**

Confidence: HIGH. All blockers cleared. Prior autonomous channel for bash additions confirmed
(Checks 11 + 12). check_project_invariants.py exits 0 for first time in 50 days. AUTONOMOUS-EXECUTABLE.

---

## Idea 4: AI-to-Human Handoff v1 via Agent OS

### Round 1 — Challenge
**This has been recommended 10+ times over 60 days without implementation.** The mechanism is
broken — not information. What evidence exists that the 11th recommendation will land differently?

### Round 1 — Defense
New evidence exists:
- os_outbound_mirror.py (PR #188) shipped 2026-05-27, reducing scope from 3 days to 1 day.
- conversation_notify.py shipped (PRs #255/#256) — adjacent functionality, same code area.
- Agent OS full merge (Groups A+B+C+D) provides the dispatch layer.
- Launch-readiness sprint has shipping velocity — 8 PRs in 7 days.

### Round 2 — Challenge
**Launch-readiness sprint argues AGAINST adding new features.** PR #255/#256 was fixing conversation
alerts, and PR #256 was specifically debugging the trigger condition (fire on NEW conversation vs
transcript-on-wrap). The area is actively being stabilized. Adding a new handoff trigger into
widget_chat.py mid-stabilization introduces regression risk.

### Round 2 — Defense
The sprint has both bug fixes AND features (Demo Tour, ROI calculator, activation nudges are all new
features in this sprint). Feature additions continue.

### Round 3 — Challenge
**MEDIUM confidence pattern.** Every run that recommended AI-to-Human Handoff got MEDIUM confidence.
The moratorium is still technically active (pending > max_pending_approvals=2). Adding to pending
worsens moratorium. And conversation_notify.py just had a bug-fix PR (PR #256 "fire on NEW
conversation, not transcript-on-wrap") — the alerting plumbing is still settling.

### Round 3 — Defense
Even accepting all the above: the handoff is the #1 customer gap, 60+ days, Critical rating.
Infrastructure exists. It should be queued.

**Verdict: WEAKENED → Parking Lot**

The evidence for shipping now is not stronger than prior runs. Launch sprint + recent alerting bug
= wrong week. But post-sprint this becomes the #1 priority. Parking lot with explicit "post-sprint
next" label.

---

## Idea 3: email_sequences.py /god-class-splitter

### Round 1 — Challenge
**GH #181 is fixed. Prerequisites are met. But is launch-readiness sprint the right time?**
A god-class split is a ~2h operation touching email_crud, email_enrollment, email_processor. It
will create @patch repointing work (3 prior occurrences). The launch sprint is focused on demo
stability. A complex split mid-sprint introduces merge risk.

### Round 1 — Defense
GH #112/#113 (N+1 queries, 1001 queries per 1000 enrollments) are tracked open issues. Email
automation is a core feature of the product being demoed. High query load during demo could be
visible. The split reduces risk long-term.

### Round 2 — Challenge
**GH #112/#113 N+1 issues have been open since 2026-05-02 (40+ days) without causing a visible
production problem.** If they haven't caused a production incident in 40 days, they won't cause
one in the next 7 days. The risk of the split (regression in email enrollment) outweighs the risk
of the N+1.

### Round 2 — Defense
Agreed on timing. But tooling is fully ready for the first time (god-class-splitter +
post-split-test-repair SKILL.md). The split should happen immediately post-sprint.

### Round 3 — Challenge
**Run 41 winner (email_sequences.py split) is already in active_directions.** Recommending it
again just adds another pending item to the moratorium counter. Better to recommend a different
category win that doesn't worsen pending count.

**Verdict: WEAKENED → Parking Lot**

Correct action, wrong sprint. GH #181 unblock noted. First-post-sprint candidate.

---

## Synthesis

| Idea | Verdict | Notes |
|------|---------|-------|
| Check 10 wire (pre-commit) | **SURVIVES → WINNER** | Blocked condition cleared, AUTONOMOUS-EXECUTABLE |
| AI-to-Human Handoff | **WEAKENED → Parking Lot** | Post-sprint #1 priority |
| email_sequences.py split | **WEAKENED → Parking Lot** | Post-sprint, tooling ready |
| check-widget-sync.sh | Not fully debated → Parking Lot | Valid, deferred to run 59 |
| KB autopopulate fix | Not fully debated → Parking Lot | Lower urgency |
