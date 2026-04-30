---
title: OpenAI realtime-voice-component — pattern note for AgentNexLiFy
captured: 2026-04-29
source: OpenAI open-source realtime-voice-component for gpt-realtime-1.5
type: pattern-extraction
status: backlog (not building yet)
---

# What it is

React reference impl. Floating button + Zod-defined narrow tools. Voice -> tool call (NOT voice -> text -> command). Model sees current UI state. Tools fully owned by app -> model can only call predefined narrow actions. Secure white-box vs Computer Use black-box.

Demo: "switch to dark mode", "move knight to F3", form auto-fill from speech, progress bar live update.

# Why interesting for AgentNexLiFy

Pattern matches existing tool-call architecture (widget chat already uses tools). Open-source = no lock-in to copy the UX pattern even if we use Anthropic.

# Best fit slice — operator dashboard voice control

NOT the customer-facing widget. The slice that matters: **solo small-biz owner using AgentNexLiFy dashboard on mobile while working** (driving truck, hands dirty, on a roof).

Persona: 914 Exterior, plumber, cleaner, power-washer. Hands-busy. Wants:

- "Show leads from last week"
- "Mark lead John Smith as won"
- "Send follow-up SMS to today's no-shows"
- "Book Tuesday 2pm for the Williams quote"
- "What's my missed-call count today"
- "Read me the last message from the Henderson lead"

Maps to existing dashboard pages (Leads, Appointments, Activity feed from project_automation_vs_crm_pivot).

# Concrete tool surface (sketch)

| Tool | Args | Backed by |
|---|---|---|
| `list_leads` | `{since, status?, limit}` | GET /api/leads |
| `update_lead_status` | `{lead_id, status}` | PATCH /api/leads/:id |
| `send_sms` | `{lead_id, message}` | POST /api/messages (Twilio) |
| `book_appointment` | `{lead_id, datetime, service?}` | POST /api/appointments |
| `read_message` | `{lead_id, latest?}` | GET /api/conversations |
| `today_metrics` | `{}` | GET /api/dashboard/today |
| `find_lead` | `{name}` | GET /api/leads?search= |

Narrow actions only. No raw SQL, no free-form DB writes. Tenant-scoped via JWT (existing `client_id` discipline preserved).

# Why NOT use it on the widget

Widget = cold-traffic lead capture. Lead has hands free + phone. Voice = nice-to-have. Latency + audio storage + privacy compliance = added load with thin upside. Skip.

# Stack-fit considerations

- Pattern = stack-agnostic (React + Zod tool defs). Backend can be Anthropic.
- gpt-realtime-1.5 = OpenAI dependency. If used, opens a 2nd LLM vendor key per-deploy (not per-tenant). Adds billing surface.
- Anthropic equivalent: realtime API not yet at parity. Watch.
- Twilio Media Streams already on stack (voice/SMS). Could route mic -> Twilio Media Streams -> server -> tool calls without OpenAI realtime. More work, no new vendor.

# When to revisit (triggers)

1. Operator-side mobile usage hits >40% (analytics needed)
2. Tester request explicitly: "I wish I could just tell it"
3. Anthropic ships realtime tool-call layer (ETA unknown)
4. Onboarding-v2 ships and self-maint loop closes -> next P1 slot opens
5. Enterprise tier prospect demands hands-free ops

# Backlog ticket draft

```
Title: Spike — operator dashboard voice control (mobile, hands-busy)
Labels: spike, frontend, mobile, ai-feature
Body:
- Persona: solo small-biz owner on mobile, hands busy
- Goal: 7 narrow voice tools (see openai-realtime-voice-component-2026-04-29.md)
- Scope: 1 dashboard page (Activity feed) + 3 tools (list_leads, today_metrics, send_sms)
- Stack choice: spike both paths in parallel worktrees
  (a) OpenAI realtime-voice-component (fast, vendor-add)
  (b) Twilio Media Streams + Anthropic tool-calls (slow, stack-pure)
- Acceptance: voice command -> tool call -> dashboard update <2s end-to-end
- Out of scope: widget integration, multi-tenant key mgmt, audio retention policy
Blocked by: onboarding-v2 P1 ship
```

# Anti-patterns to avoid

- Never expose raw DB tools to voice layer
- Never add OpenAI dep just to copy the UX pattern (the pattern is the value, not the model)
- Never store voice audio without compliance review (PII, BAA-equivalent)
- Never ship voice UI before tool surface is auth-tested

# Cross-refs

- `project_automation_vs_crm_pivot` memory — 4 ops automations + activity feed
- `project_value_prop_framework` memory — hours-saved framing fits voice
- `.claude/rules/widget-rules.md` — why widget stays text
- `migrations/111_missed_call_text_back.sql` — operator-side surface this would augment
