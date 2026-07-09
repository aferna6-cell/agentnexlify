# Idea 3 — email_sequences.py God-Class Split

**Category:** code_health  
**Effort:** M  
**Type:** HUMAN-REQUIRED (architectural decision)  
**Score:** 6/10

## Problem

`backend/services/email_sequences.py` has been flagged in improve-architecture audit output as a god class candidate. Run 41 identified this file (31+ days ago). No action taken.

Rule 9 (user-rules.md): "If a file is already >600 lines and I'm about to add more, stop. Factor the existing code into modules first."

## Current State

File not verified in this run (would require `wc -l`). Expected: email template generation, sequence scheduling, send logic, and tracking all in one file.

## Proposal

Split into:
- `email_sequence_scheduler.py` — scheduling + trigger logic
- `email_template_renderer.py` — Jinja2 / template generation
- `email_sender.py` — Resend API calls + delivery tracking
- `email_sequences.py` — thin orchestrator (imports + coordinates the above)

## Why Not Top Pick This Run

- M effort — nightly-commit-review would need to implement, but it's a refactor (MEDIUM risk, human review preferred)
- Moratorium active — pending_approvals ~4, refactor doesn't carry security override
- No new incident: class grew but no new crash/bug reported in 31+ days
- Zapier mandate is higher priority and AUTONOMOUS-EXECUTABLE
- Next best window: after SMS Dashboard lands and clears one pending slot
