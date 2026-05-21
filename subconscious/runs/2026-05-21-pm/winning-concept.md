# Winning Concept — 2026-05-21-pm (Run 29)

## Recommendation

Write the AI-to-Human Handoff v1 GH Issue — a 5-minute planning document that converts a 35-day stale Critical customer gap into an actively-tracked implementation ticket on the product backlog.

---

## Why This, Why Now

**The /moratorium-sprint recommendation has been made 6 consecutive times without invocation.** The evidence strongly suggests the bottleneck is the 40-minute commitment window, not information or tooling. Run 29 recommending the sprint a 7th time adds no new forcing function. The most useful thing run 29 can do is move a different dimension of the board forward — something that doesn't require 40 min and doesn't depend on the same commitment that hasn't materialized in 6 runs.

**AI-to-Human Handoff is the oldest pending customer value item at 35 days.** It's rated Critical in customer-gaps.md across all 7 verticals. The infrastructure exists (conversations table, webhooks, Twilio, Resend). Run 20 explicitly authorized a parallel customer-value track alongside the moratorium exit sprint. Writing the GH issue is docs work — 5 minutes — and is moratorium-exempt.

**A written GH issue creates leverage beyond the document itself.** The issue-to-pr-loop polls assigned GH issues every 15 minutes. A well-specified issue can unlock autonomous pickup of the LOW-risk scaffolding (e.g., route stub, trigger string constant) while human review handles the Twilio integration. The 5-minute investment now saves a planning session post-moratorium and potentially gets autonomous partial execution.

**Run 21 (May 17) also recommended this and wasn't done.** The difference: run 21 came after 4 consecutive governance failures as an emergency pivot (MEDIUM confidence). Run 29 comes after a governance audit with clean state (HIGH confidence in the recommendation, MEDIUM confidence in invocation due to run 21 precedent).

---

## Implementation Sketch

**Total estimated time: ~5 min**

### Step 1: Create GH Issue via mcp__github__create_issue

```
Title: feat(widget): AI-to-Human Handoff v1 — explicit trigger

Body:
## Problem
Leads ask complex questions the AI can't answer or emotionally escalate.
No handoff path exists — the AI keeps trying to respond, degrading trust.
Critical gap across all 7 verticals (customer-gaps.md).

## Scope (v1 — explicit trigger only)
- Trigger: user types one of ["talk to someone", "speak to a person", 
  "human please", "call me", "connect me with owner"]
- Action: send webhook + Twilio SMS to tenant owner with lead context
- Fallback: send email if Twilio not configured
- Lead status: set to "needs_follow_up" 
- Widget message: "I've let [Business Name] know. Expect a call/text soon."
- NO proactive detection (deferred to v2)
- NO live chat (deferred to v2)

## Files Expected to Change
- backend/routers/widget_helpers.py — add trigger detection + handoff logic
- backend/services/twilio_service.py — add owner-SMS function
- backend/tests/test_ai_to_human_handoff.py — new test file (TDD first)
- widget/agentnexlify-widget.js — render handoff confirmation message
- frontend/public/widget/agentnexlify-widget.js — byte-identical copy

## Acceptance Criteria
- [ ] Typing "talk to someone" in widget chat triggers handoff
- [ ] Owner receives SMS with lead name + last message
- [ ] Fallback to email if no Twilio config
- [ ] Lead status updated to "needs_follow_up"
- [ ] Widget shows handoff confirmation text
- [ ] No regression to existing widget chat flow
- [ ] Test suite: happy path + missing Twilio config + multi-tenant isolation

## Notes
- Infrastructure confirmed: conversations table, webhooks, Twilio, Resend exist
- Multi-tenant: use client_id (not tenant_id) per schema-discipline.md
- Estimated effort: 1.5-2 days
- Original gap filed: 2026-04-16 (subconscious run 4, 35+ days)
- Parallel track authorized: governance.json run 20 backlog

Labels: customer-value, widget, backend, ai-ready
```

### Step 2: Link to subconscious state
After issue created: update governance.json run 4 note to include the GH issue number. This closes the loop between run 4 (original recommendation) and the implementation artifact.

---

## What This Replaces

Run 29 is NOT replacing run 28's winning concept (/moratorium-sprint). That remains the standing highest-priority action and the path to moratorium exit. Run 29 adds a parallel action on a different dimension (customer value, docs-only, 5 min) that can proceed independently of the sprint commitment.

This replaces the pattern of run 29 being the 7th consecutive identical recommendation. It breaks the repetition and provides genuinely new value.

---

## Standing Sprint Direction (unchanged from run 28)

The /moratorium-sprint remains the highest-leverage action:
- Items A+B+D, ~40 min
- Sprint drops pending 5→2 = moratorium exits
- moratorium-sprint SKILL.md ready (7985fbb)
- No new blockers

Invoke at any time: `/moratorium-sprint`

---

## Moratorium Exit Map (current state)

```
True pending (post-run-28 audit + run-29):  5
  - Run 4: AI-to-Human Handoff v1 (35d, pending_approval)
  - Run 20: Governance threshold reduction (pending_approval)
  - Run 21: AI-to-Human Handoff GH Issue (pending_approval)
  - Run 28: /moratorium-sprint (pending_approval)
  - Run 29: this recommendation (pending_approval)

After run 29 winner implemented (GH issue written):
  - Runs 4 + 21 both partially resolved → pending: 5→4

After /moratorium-sprint invoked (Items A+B+D merged):
  - Runs 28 + 29 implemented → pending: 4→2
  - Moratorium exits (exit condition: ≤ 2)
```

---

## Confidence

**MEDIUM** — Evidence is strong (35 days, Critical gap, infrastructure confirmed, parallel track authorized). MEDIUM not HIGH because run 21 recommended the same GH issue and it wasn't invoked. Risk: same 5-minute non-invocation. Mitigation: the effort is genuinely 5 minutes, this is a different kind of task from the sprint, and the subconscious recommending it for the second time adds weight.
