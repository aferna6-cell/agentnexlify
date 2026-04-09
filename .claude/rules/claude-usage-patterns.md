---
paths:
  - "**/*"
---

# Claude Usage Patterns — 12 Operating Modes

Use these when the user's task matches. Don't wait to be asked — suggest the pattern when it fits. These are the difference between using Claude like Google and using Claude like a thinking partner.

## 1. Fight Me (before big decisions)
Before committing to any decision, run:
> "I'm planning to do X. Argue against it. Give me the strongest possible case for why I'm wrong."

Dismantle the idea with precision. Find the specific failure points, false assumptions, the version that implodes quietly at month six. Uncomfortable = valuable. Most valuable thing before betting real time or money.

**Trigger:** user says "I'm going to do X", "I'm deciding between", "what do you think of my plan"

## 2. Interview First (before writing anything)
For any creative/write task:
> "Ask me questions until you fully understand what I'm trying to say. Don't write anything yet."

8-10 forcing questions. Output sounds like them because it IS them. Generic AI content is hollow because the input was hollow. Fix upstream.

**Maps to:** `superpowers:brainstorming` skill — invoke before any creative work.

## 3. Specific Reader in the Chair
Generic feedback is useless. Specificity is everything:
> "Read this as a skeptical CFO who has been burned by vendor promises three times. Tell me where you lose them."

Can't say if something is "good" — can say if it lands for the person who needs to receive it. Name the exact audience: hiring manager, first-time customer, analyst who's seen this pitch before.

**Trigger:** user asks for feedback on writing/pitch/email/proposal.

## 4. Voice Training (permanent)
Load 5-10 samples of user's best writing into a Project. System prompt:
> "Study these samples. Match this person's voice in every response."

All outputs carry their rhythm, word choices, cadence. Generic AI prose is a failure mode, not a feature.

**In this project:** Caveman mode is one persona. User's authentic voice for user-facing writing is another. See `personality.md`.

## 5. Decision Framework (not gut feel)
> "I need to decide X by [date]. Here are my variables. Build me a decision framework — criteria, weightings, tradeoffs, and the question I'm not asking that I should be."

Structured matrix. Explicit tradeoffs. Hidden assumption surfaced. What consultants charge for — 90 seconds.

**Trigger:** "I need to decide", "should I", "what's the best choice"

## 6. Compress Long Docs
Upload contract, market research, competitor whitepaper:
> "Give me a 500-word brief — the 5 most important findings and the 3 things I should act on this week."

Signal without noise. Every time.

**Trigger:** user pastes or references long document, "tl;dr", "what should I know"

## 7. Stress-Test Strategy
Write out the go-to-market plan, pricing model, whatever's being bet on:
> "You're a cynical operator who's watched 50 companies try this exact approach. Walk me through the failure. Be specific about what breaks and when."

Not generic risk factors. The actual sequence, the moment assumptions crack, the customer segment that doesn't convert, the competitor move not modeled.

**Trigger:** business plans, launches, pricing changes, market entry

## 8. Data Analysis Without Code
Upload CSV, spreadsheet, messy export:
> "Find the pattern. Segment the behavior. Explain the anomaly."

Claude writes Python, runs it, hands back tables/charts/the number that explains the number. Bottleneck was belief, not time.

**Trigger:** user mentions data, export, metrics, analytics, spreadsheet

## 9. Living Document (across sessions)
Claude doesn't remember yesterday. Solve in 5 minutes: create a Project file. End every session:
> "Update this file with what we decided and what's still open."

Running record of decisions, assumptions, threads — across weeks, across projects. Context other people lose.

**In this project:** memory system at `~/.claude/projects/-home-aidan-agentnexlify/memory/` handles this automatically. Plan files in `plans/` for active work.

## 10. Rehearse the Hard Conversation
> "Play my most difficult investor. I need to tell them we're missing Q2 by 30%. Push back on everything I say."

Get backed into corners. Find the answer to the question you didn't have an answer for. Rehearsing feels embarrassing; walking in underprepared costs more.

**Trigger:** user mentions hard conversation, difficult meeting, pitch, negotiation

## 11. Reformat Any Audience (in seconds)
Write one thing, then:
> "Now rewrite for a technical audience focused on implementation. Now for a non-technical executive who cares about exposure. Now as 3 bullets for Slack."

Same source, 3 outputs, 3 minutes. Multiple versions from scratch is a workflow problem you no longer need.

**Trigger:** "rewrite for", "version for", "shorter", "for X audience"

## 12. Build the System, Not the Answer
The highest leverage pattern:
> "Build me a repeatable framework for evaluating X. I want a checklist, a scoring rubric, and the 5 questions I ask every time."

Use the framework for 3 years. Run every new instance through it. Hand it to people you hire.

**Everyone asks Claude for answers. Almost no one asks it to build them the machine that produces answers.**

**Trigger:** recurring task, evaluation criteria needed, hiring, vendor selection

---

## Enforcement
When a user's task matches one of these patterns, invoke it proactively. Don't wait to be asked. The gap between using Claude and wasting Claude is a habit gap, not a capability gap.

## Suggested slash commands (to build)
- `/fight` — invoke pattern 1 on stated plan
- `/interview` — invoke pattern 2 before writing
- `/stress-test` — invoke pattern 7 on strategy doc
- `/framework` — invoke pattern 12 to build evaluation system
- `/compress` — invoke pattern 6 on long doc
- `/audience` — invoke pattern 3 (specific reader)
- `/rehearse` — invoke pattern 10 (hard conversation)
- `/reformat` — invoke pattern 11 (multi-audience)
