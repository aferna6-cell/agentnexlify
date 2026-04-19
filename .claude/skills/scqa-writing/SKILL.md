---
name: scqa-writing
description: Structure outbound content (sales outreach, PRD intros, ADR summaries, blog posts) using Situation-Complication-Question-Answer framework. Use when partners draft prospect emails, when writing executive summaries, or when introducing a spec/ADR.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- scqa
- situation complication
- structure this email
- write executive summary
- frame this proposal
effort: low
---

# SCQA Writing — Consulting Narrative Framework

Four-part structure for cold-open persuasive content: Situation → Complication → Question → Answer. Used by McKinsey, Bain, BCG. Works for sales outreach, PRDs, ADRs, exec briefings.

## When to Use
- Partner outbound email to small-biz prospects (warm the lead in 4 beats)
- `specs/<feature>_spec.md` executive summary
- `planning/decisions/YYYY-MM-DD-<title>.md` intro
- PR descriptions that need stakeholder buy-in
- Compressing long research into a 200-word brief
- Slack announcement for a launch

## When NOT to Use
- Technical error replies (lead with fix, not narrative)
- Caveman-mode internal dev chat (framework adds filler)
- Direct commands to Claude (just ask the question)
- Content where the audience already knows the Situation

## Structure

### S — Situation (1-2 sentences)
Shared starting point the reader agrees with. Frame the world as it is today. No spin.
> "Local contractors handle inbound leads through phone tag and missed calls."

### C — Complication (1-2 sentences)
What's broken, changing, or newly urgent. Creates tension. Must be something reader recognizes as real.
> "When 40% of after-hours leads go to voicemail, they call the next three contractors on Google before you wake up."

### Q — Question (1 sentence)
The implicit question the Complication raises. Don't literally write "The question is…" — frame as open problem.
> "Every missed lead costs $400-2000. How do you capture them without hiring a night-shift receptionist?"

### A — Answer (rest of message)
Your specific answer. Concrete, measurable, differentiated. Not a product pitch — a resolution to the Q.
> "AgentNexLiFy's chat widget books after-hours leads directly into your calendar. Average tenant sees 2.4x lead capture in the first 30 days. No call center, no new hires, $249/mo."

## Rules
- Situation + Complication combined ≤ 60 words
- Question never starts with "The question is"
- Answer ≥ 40% of total word count
- Numbers > adjectives ("2.4x" not "significant")
- One CTA max, at the end of Answer
- Match user voice (see `personality.md` when writing for Aidan)

## AgentNexLiFy-Specific Examples

### Sales Outreach (partners)
```
S: You're running a small contractor crew and your reviews on Google are solid.
C: Most of your new leads come in after 6pm — when nobody's manning the phone. They call the next three guys on the map.
Q: [implicit — how do you capture them?]
A: AgentNexLiFy drops a chat widget on your site that books leads into your calendar 24/7. MTOptions saw 2.4x lead capture in month one. $249/mo, 14-day free trial, no contract. Reply "demo" and I'll show you.
```

### PRD Intro
```
S: Tenants currently see 3-5 days of chat history before it's truncated.
C: Long-running conversations now exceed 150k tokens, forcing mid-session compaction that drops context.
Q: [implicit — how do we keep context without blowing cost?]
A: Introduce pgvector-backed conversation summarization that compresses 30+ turn chats into 2k-token semantic summaries. See `plans/conversation-compaction_plan.md` for rollout.
```

### ADR Summary
```
S: Widget JS lives in two locations: `widget/` and `frontend/public/widget/`.
C: Byte-drift between copies broke embeds on 3 tenants this quarter.
Q: [implicit — one source or enforce sync?]
A: Keep two locations, enforce byte-identical via pre-push hook + CI check. Single source requires CDN migration out of scope for Q2.
```

## Anti-patterns
- Never ship an SCQA where Situation and Complication are the same sentence
- Never use SCQA for task descriptions ("build X") — too much framing
- Never SCQA a caveman-mode reply — friction mismatch
- Never let Answer exceed 200 words — compress or split
- Never start Situation with "In today's world" or "With the rise of" — dead-on-arrival opener

## Cross-refs
- `.claude/rules/personality.md` — voice rules for user-facing writing
- `.claude/rules/prompt-formula.md` — ROLE+TASK+CONTEXT+CONSTRAINTS+OUTPUT (complementary)
- `.claude/skills/write-prd/SKILL.md` — use SCQA for PRD intro
- `marketing:draft-content` / `sales:draft-outreach` — downstream consumers
- `PROMPTLIBRARY.md` — add SCQA as reusable Write prompt
