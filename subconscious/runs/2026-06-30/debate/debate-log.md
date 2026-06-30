# Debate Log — Run 73 (2026-06-30)

## Format
Top 3 ideas debated. Each gets a Prosecutor (attack) + Defender (counter) pass. Verdict follows.

---

## Debate 1: Idea 1 vs Idea 2

### Idea 1 — SMS Compliance Dashboard
**Prosecutor:** Backend shipped 10+ days ago. If the frontend weren't complete, why hasn't this shipped already? Maybe there's a reason it's been idle — frontend patterns for compliance tables aren't established, and we'd be creating a one-off UI with no clear placement in the nav. Also, the moratorium technically covers this as a pending item.

**Defender:** The moratorium covers NEW items that add to the human queue. This IS the item — shipping it reduces the queue from 4-6 to 3-5. Backend + migration done is precisely the signal that it's S-effort. The idle time is governance lag, not technical bloat. Standard dark-theme table + Recharts bar chart is the established pattern. Nav: Settings → Compliance tab. Identical to how Email settings are wired.

**Verdict:** IDEA 1 SURVIVES. Prosecutor argument weakened by own logic — moratorium argument inverts. Defender's nav/pattern answer is concrete.

---

### Idea 2 — Plan-Name Guard Check 7
**Prosecutor:** Check 7 prevents a class of billing bug that hasn't occurred since GH #292/#293 fixed 2026-06-23. We fixed the bug; we're now adding a guard for a problem we just solved. Prevention is good, but the cost is a human session for a Python script edit that nightly can't do. Human session time is the scarce resource. Use it on customer value, not guard rails.

**Defender:** The guard prevents FUTURE recurrence. GH #292/#293 found the bug manually. Check 7 makes it impossible to miss. S-effort, follows Check 6 pattern exactly. The pre-commit hook catches it before it ever ships — not session-time-intensive to implement.

**Verdict:** IDEA 2 WEAKENED. Defender correct on effort, but Prosecutor's point on prioritization holds: moratorium context + existing SMS Dashboard in queue means this loses the slot. Parking lot.

---

## Debate 2: Idea 1 vs Idea 3

### Idea 1 — SMS Compliance Dashboard
**Prosecutor:** SMS Dashboard serves compliance tooling for existing tenants. Most tenants aren't sending SMS at volume yet — the opt-out count is likely zero or near-zero for most. The "TCPA liability" framing is real but theoretical until a tenant hits scale.

**Defender:** Theoretical liability is still liability. Stripe and Resend integration means tenants ARE sending. Even one TCPA violation at $1500/msg creates existential risk for a small business. More importantly, this is the OLDEST SHIPPED-BUT-INCOMPLETE backend in the codebase (10+ days). Completing it removes technical debt regardless of current SMS volume.

**Verdict:** IDEA 1 SURVIVES. Completing a half-shipped feature beats adding a new feature start. Rule 8 applies even to multi-PR sequences.

---

### Idea 3 — AI-to-Human Handoff v1
**Prosecutor:** Critical gap, 75 days, all 7 industries, direct GoHighLevel competitive gap. This is the most important thing in `customer-gaps.md`. How many runs do we skip it?

**Defender:** 7 failed recommendations with no new evidence = the pattern is broken. Run 70 memo: "Do not re-recommend without new evidence of readiness." The `os_outbound_mirror.py` scoping is real but still M-effort + migration. Moratorium explicitly covers M-effort new items.

**Verdict:** IDEA 3 WEAKENED. Critical gap is real. But 7 failed recs is a signal: the bottleneck isn't the recommendation, it's the execution pathway. Re-escalating without new evidence is noise in the recommendation channel. Parking lot until: (a) SMS Dashboard shipped, (b) explicit owner readiness signal.

---

## Debate 3: Tiebreak Assessment

### Final ranking
| Rank | Idea | Verdict |
|------|------|---------|
| 1 | SMS Compliance Dashboard | WINNER |
| 2 | Plan-Name Guard Check 7 | Parking lot |
| 3 | AI-to-Human Handoff v1 | Parking lot |
| 4 | KB Verify Cron | Bonus note (not a recommendation) |
| 5 | email_sequences.py split | Parking lot (moratorium) |

### Special notes from debate
- Governance corrections required: runs 71+72 moved from `pending_approval`/`in_progress` → `implemented` (65284cc).
- KB log still at 2026-05-05. Script fixed. Manual trigger needed if cron not wired in container.
- Moratorium true_pending after corrections: ~4 (run 70 SMS, run 41 email split, run 38 AI handoff, run 4 AI handoff). Still over moratorium threshold of 2.
- SMS Dashboard winner does NOT add to pending count — it is the oldest-in-queue item being closed.
