# LLM Runtime Operations

## Purpose
This document explains how AgentNexLiFy's centralized LLM runtime should be operated and debugged.

Primary runtime file:
- `backend/services/llm_runtime.py`

## What is centralized
All app-level Claude calls should route through the shared runtime helpers:
- `call_claude_messages(...)`
- `call_claude_messages_sync(...)`

The runtime wrapper is responsible for:
- provider invocation
- timeout handling
- structured logging
- correlation ids
- usage/token capture
- safer metadata logging

## Log Events
The runtime emits three main log lines:

### 1. `llm.call.start`
Includes:
- call id
- operation name
- model
- max tokens
- temperature
- message count
- role counts
- system prompt size (chars)
- message size (chars)
- safe metadata

### 2. `llm.call.finish`
Includes:
- same call id
- operation name
- model
- duration in ms
- input tokens
- output tokens
- cache token stats
- response length
- stop reason
- safe metadata

### 3. `llm.call.error`
Includes:
- same call id
- operation name
- model
- duration in ms
- message count
- role counts
- prompt size summary
- error type
- truncated error text
- safe metadata

## Correlation ID
Every runtime call gets a short correlation id.
Use it to connect:
- start log
- finish log
- error log

This is the fastest way to trace a single failing or slow AI operation through production logs.

## Safe Metadata Rules
The runtime intentionally avoids logging sensitive payload-style metadata.

### Dropped metadata keys (by name pattern)
Anything containing:
- `message`
- `content`
- `text`
- `body`
- `api_key`
- `token`
- `secret`
- `password`
- `cookie`
- `authorization`

### Preserved metadata
Operational metadata is preserved when useful, such as:
- tenant ids
- lead ids
- operation flags
- business type
- counts
- boolean switches
- small identifiers
- shape summaries for lists/dicts

## How to add a new LLM call safely
When adding a new AI feature:
1. route it through `call_claude_messages(...)` or `call_claude_messages_sync(...)`
2. give it a stable `operation` string
3. include only safe metadata
4. do not pass prompt or body content in metadata
5. prefer deterministic parsing/validation around model outputs

## Operation Naming Guidance
Use stable, searchable operation names like:
- `onboarding.auto_populate_kb`
- `seo.run_audit`
- `automation.generate_ai_email`
- `twilio.sms_reply`
- `reviews.generate_draft`

Avoid vague names like:
- `generate`
- `call_ai`
- `ask_model`

## Debugging a bad AI path
When investigating an issue:
1. search logs for the `operation` name
2. use `id=` to connect start/finish/error lines
3. compare duration, token usage, and metadata across good/bad calls
4. inspect the downstream parser/validator for that operation
5. if the path is model-driven and causes side effects, confirm validation logs as well

## Current expectations
- app-level Claude usage should live behind the centralized runtime
- prompt content should not be logged directly by runtime metadata
- failures should remain diagnosable via operation + id + safe metadata

## Retry policy
Retries should be **selective**, not universal.

### Good retry candidates
Use a single bounded retry (`max_retries=1`) for:
- long-running content generation
- intelligence/analysis jobs
- non-interactive summarization
- background or operator-triggered tasks where a short retry is acceptable

Examples:
- content repurposing
- weekly intelligence briefs
- local SEO analysis / GEO scoring / competitor analysis
- AI email drafting for automations

### Bad retry candidates
Avoid retries by default for:
- live widget chat
- SMS reply flows
- tight latency-sensitive request/response interactions
- user-facing chat turns where a retry would worsen UX or create duplicate-feeling behavior

### Why
Retries help with transient provider issues, but they also increase:
- tail latency
- perceived sluggishness
- ambiguity in real-time chat UX

The runtime now supports bounded retries, but callers should opt in only where the product behavior can tolerate them.

## Recommended future improvements
- add percentile latency tracking per operation
- add provider/model dashboards by operation
- add error-rate counters by operation
- add optional request sampling for deeper debugging in non-production environments
