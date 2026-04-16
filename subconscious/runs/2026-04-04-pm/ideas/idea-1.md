# Idea 1: AI-to-Human Handoff in Widget

**Category:** growth / ux
**Effort:** medium (3–4 days)
**Impact:** Critical — rated highest customer gap across ALL 7 simulated industries

---

## Hypothesis

When the widget AI can't resolve a query (complexity threshold, repeated question, explicit request), it gracefully offers to connect the visitor with a live team member. The conversation transfers seamlessly to the dashboard inbox with full chat history and a priority flag. This closes the #1 open customer gap and directly increases retention for complex-query industries (legal, real estate, medical).

---

## Evidence

1. `docs/dev-knowledge/customer-gaps.md` line 29: "AI-to-human handoff — Critical for complex queries" — rated first in the Open Gaps cross-industry table, present in ALL 7 simulated industries.
2. `docs/dev-knowledge/simulation-lawyer.md`, `simulation-dental-office.md`, `simulation-real-estate.md` — all flag handoff as a missing piece where the AI hit its limits in testing.
3. Competitive landscape (CLAUDE.md): GoHighLevel AI Employee has this feature. Phonely and Toma tout it as a key differentiator. We are behind.
4. Product-market fit table: Lawyer (7/10) and Real Estate (6/10) — both would jump 1+ point if handoff existed.
5. Infrastructure already present: `conversations` table, `team_members` table, dashboard inbox (conversations page) — the plumbing is there, just no trigger mechanism.

---

## Implementation Sketch (no code)

1. **Detection logic in widget_helpers.py** — Three triggers:
   - User types "talk to a human" / "speak to someone" / "connect me"
   - AI response confidence below threshold (repeated "I don't have that information")
   - Conversation length > N turns without resolution
2. **Widget UI** — Show "Would you like to speak with someone from our team?" with Accept/Decline buttons
3. **Backend endpoint** — `/api/widget/request-handoff` sets `conversations.status = 'handoff_requested'`, fires a webhook + optional SMS to team
4. **Dashboard** — Conversations with `handoff_requested` status show a distinct badge + sort to top of inbox
5. **Migration** — Add `handoff_requested_at` timestamp to conversations table (new nullable column, no RLS change needed)

---

## Success Metric

- Handoff requests successfully captured in conversations table: ≥ 95% success rate
- Dashboard shows handoff badge within 2s of request
- No regression in existing chat flow (test with widget smoke tests)
