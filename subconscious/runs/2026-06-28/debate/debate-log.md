# Debate Log — Run 70 (2026-06-28)

Top 3 ideas debated: SMS Compliance Dashboard (01), Zapier plan_status (02), AI-to-Human Handoff (03).

---

## Round 1: SMS Compliance Dashboard

### Challenge
The backend enforcement just landed yesterday. Is this too fast? Does rushing a frontend onto day-1 backend risk shipping a half-baked feature?

Also: the council sprint is just wrapping up. Tenants haven't even discovered fix #1 yet. Are we building a dashboard for a problem no one has complained about yet?

### Defense
"Too fast" is backwards framing. The backend enforcement is the hard part — it's done. The frontend is 1 new page + 1 new route + 1 Recharts chart + 1 stat row. This is not a complex build.

On "no one complained yet" — TCPA penalties don't wait for complaints. The first audit notice is the complaint. Tenants need visibility BEFORE the first fine, not after. GoHighLevel already ships this. We're behind.

Evidence: `9ddfd0e` is on main. `leads.sms_opted_out` is populated. Recharts is installed. No migration needed. The data is there. The chart is not. This is a 1-day visibility gap, not a strategic question.

### Verdict: SURVIVES
Backend unblocked. Clear effort bound (~1 day). Compliance visibility has real penalty-avoidance value. GoHighLevel competitive gap. Recharts ready.

---

## Round 2: Zapier plan_status Enforcement (GH #107)

### Challenge
This is a 60-day-old bug. If it were urgent, someone would have filed it as critical. API keys without plan checks — tenants who cancel don't actively abuse it. They just stop using the product. The blast radius is essentially zero in practice.

Also: this is 2 hours of work. Why does it need a subconscious nomination? Shouldn't this just be on the backlog?

### Defense
Security correctness isn't about observed abuse. Expired credentials should not grant access — this is an invariant, not a nice-to-have. A terminated tenant with a valid API key can automate data extraction for months. That's a data boundary violation.

The 60-day age is damning — it shows this keeps falling off the priority list. Subconscious nomination forces it onto the approval queue.

### Verdict: WEAKENED — Bonus A
Not the winner. But the Zapier fix is small enough to bundle as a bonus action alongside the SMS Dashboard. Human should green-light both: spend the 2 hours on #107 this week.

---

## Round 3: AI-to-Human Handoff

### Challenge
This is the most-cited gap, run 4 winner, 73 days with no implementation. If the subconscious picks it again and it still doesn't get implemented, what does that accomplish?

Pattern: 8+ recommendations, 0 implementations. Is the subconscious just re-recommending things that can't get done?

### Defense
It's not that it can't get done — it's that the council sprint absorbed all bandwidth for 2 weeks. Post-sprint is the right time to resurface big features. `os_outbound_mirror.py` exists. The scaffolding is there.

### Counter-challenge
Yes, but the scaffolding state is unknown. PR #188 was months ago. Auditing that before building is a precondition, not a given. If we nominate this and the human needs to audit first, that's a 2-step process with no clear owner.

SMS Dashboard has no preconditions. It's ready to build now.

### Verdict: WEAKENED — Parking Lot
Defer to run 72+. Pre-condition: human audits `os_outbound_mirror.py` current state. If confirmed ready, run 72 nominates it with full spec.

---

## Winner: SMS Compliance Dashboard

**Rationale:** Backend enforcement done (yesterday). Frontend visibility missing. 1-day effort. No migration. Recharts ready. TCPA penalties real. GoHighLevel competitive gap. Unambiguous scope. No blockers.

**Bonus A (bundle this week):** Zapier #107 plan_status enforcement — 2 hours, `zapier_auth.py`, 1 test.
