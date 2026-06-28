# Idea 03: AI-to-Human Handoff v1

**Category:** Customer Value (Critical)  
**Effort:** ~3–5 days  
**Priority:** CRITICAL (but weakened)

---

## The Opportunity

The most-cited cross-industry customer gap (`docs/dev-knowledge/customer-gaps.md`): when the AI widget can't resolve a query, it should transfer the conversation to a human agent in real time.

Current behavior: AI tries indefinitely, or ends conversation. No escalation path.

GoHighLevel has this. Podium has this. We don't.

---

## Evidence

- `docs/dev-knowledge/customer-gaps.md` — "AI-to-Human Handoff: Critical, cross-industry"
- Run 4 winner (73 days ago) — never implemented
- `backend/services/os_outbound_mirror.py` — scaffolded (PR #188) but not wired to widget
- `customer-gaps.md` — mentioned across salon, dental, plumbing, fitness, legal verticals
- Council sprint did NOT address this gap

---

## Why Weakened This Run

- 8+ subconscious recommendations. 0 implementations. Pattern: recommendation accumulation without execution.
- Post-council-sprint: team bandwidth was fully absorbed by 6 council fixes (Jun 24–27)
- `os_outbound_mirror.py` exists but state is uncertain — may need audit before building on it
- Effort estimate (3–5 days) is the highest of any candidate

---

## Parking Lot Recommendation

Defer to run 72 or 73. Before that run:
1. Human audits `os_outbound_mirror.py` for current state
2. Human confirms this is the implementation week
3. If confirmed, subconscious can write detailed spec

Not the winner this run. Post-council recovery window. SMS Dashboard is faster and unblocks compliance visibility immediately.
