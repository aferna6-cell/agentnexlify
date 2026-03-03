# Dead Code Cleanup Report

**Date:** 2026-03-03

---

## Files Archived (moved to `_archive/`)

### Backend Routers — Old Single-Tenant Code
| File | Reason |
|------|--------|
| `backend/routers/chat.py` | Queries non-existent `clients` table. Replaced by `widget.py` |
| `backend/routers/clients.py` | CRUD on non-existent `clients` table |
| `backend/routers/signup.py` | Inserts into non-existent `clients` table. Replaced by `auth.py` register |
| `backend/routers/webhooks.py` | Old Twilio SMS webhook using `clients` table. Replaced by `automations.py` |

### Backend Services — Only Imported by Dead Code
| File | Imported By | Reason |
|------|-------------|--------|
| `backend/services/claude_agent.py` | `chat.py`, `webhooks.py` (both dead) | Old AI agent with tool-use loop. Widget.py has its own inline AI handler |
| `backend/services/sms.py` | `webhooks.py` (dead) | Duplicate of `twilio_service.py` (which is actively used by `automations.py`) |
| `backend/services/notifications.py` | `tool_handlers.py` (dead) | Email/SMS alerts using `ClientRow`. Entire call chain dead |
| `backend/services/calendar.py` | Nothing | Zero imports anywhere in the codebase |
| `backend/services/lead_scoring.py` | Nothing | Zero imports anywhere in the codebase |

### Backend Tools — Only Imported by Dead `claude_agent.py`
| File | Reason |
|------|--------|
| `backend/tools/tool_handlers.py` | Tool dispatch for old AI agent. Only imported by dead `claude_agent.py` |
| `backend/tools/tool_definitions.py` | Claude tool schemas for old AI agent. Only imported by dead `claude_agent.py` |

### Backend Models — Old Schema
| File | Reason |
|------|--------|
| `backend/models/tables.sql` | Old schema defining `clients`, `messages`, `conversations` (with `client_id`, `status`, `channel`). Superseded by `migrations/001_initial_schema.sql` + `002` |

### Scripts — Reference Old Schema
| File | Reason |
|------|--------|
| `scripts/setup_supabase.py` | References `tables.sql` and queries `clients` table |
| `scripts/seed_demo_client.py` | Inserts into non-existent `clients` table |
| `scripts/test_conversation.py` | Calls dead `/api/chat/message` and `/api/chat/config` endpoints |

---

## Dead Imports/Routes Removed

All dead router imports and registrations were removed from `backend/main.py` in the prior commit (8051466):
- `from backend.routers import chat, clients, signup, webhooks` — removed
- `app.include_router(chat.router)` — removed
- `app.include_router(clients.router)` — removed
- `app.include_router(signup.router)` — removed
- `app.include_router(webhooks.router)` — removed
- `from backend.routers.chat import limiter` — replaced with direct `Limiter()` creation

---

## Dead Dependencies Found

| Package | In requirements.txt? | Used By | Status |
|---------|----------------------|---------|--------|
| `twilio==9.4.0` | Yes | Nothing | **DEAD** — all SMS is done via raw `httpx` calls to Twilio REST API. Package never imported. |

**Note:** Not removing from requirements.txt yet — flagging for awareness.

---

## Dead Frontend Code Found (Not Archived — Flagged for Separate Fix)

### Dead API Functions (`frontend/src/utils/api.js`)
| Function | Endpoint | Status |
|----------|----------|--------|
| `fetchActivity()` | `/api/v1/activity/{tenantId}` | Endpoint doesn't exist. Called by Dashboard but always gets empty data |
| `fetchWidgetConfig()` | `/api/v1/widget-config/{tenantId}` | Endpoint doesn't exist. Never called |
| `fetchUsage()` | `/api/v1/usage/{tenantId}` | Endpoint doesn't exist. Never called |

### Dead Lead Fields (old schema references)
| Component | Dead Fields |
|-----------|-------------|
| `LeadDetailDrawer.jsx` | `lead_temperature`, `lead_type`, `areas_of_interest`, `must_haves`, `pre_approved`, `conversation_summary`, `next_steps`, `appointment_date`, `status` |
| `LeadPipeline.jsx` | `lead_type`, `areas_of_interest`, `lead_temperature` |

### Debug Console.log Statements
| File | Line(s) |
|------|---------|
| `LoginPage.jsx` | 18-19 |
| `SignupPage.jsx` | 20, 48 |

---

## Files Kept (Not Dead)

| File | Reason |
|------|--------|
| `backend/services/conversation.py` | Rewritten to correct multi-tenant schema. No active consumers yet but ready for reuse |
| `backend/services/twilio_service.py` | Actively imported by `automations.py` |
| `backend/services/stripe_service.py` | Actively imported by `billing.py` |
| `backend/models/schemas.py` | Contains `ClientRow` (old) but also all active Pydantic models. `ClientRow` left in place |
| `backend/tools/__init__.py` | Empty, harmless |

---

## Verification

**Import check:** All 6 active routers (auth, automations, billing, leads, stripe_webhooks, widget) import successfully. The only missing module is `jose` (python-jose) which is in requirements.txt but not installed locally — works on Railway.

**Active route map after cleanup:**
| Router | Prefix | Endpoints |
|--------|--------|-----------|
| auth | `/api/v1/auth` | register, login, me, dashboard, widget-config |
| automations | `/api/v1` | twilio/missed-call, twilio/sms-reply, automations CRUD |
| billing | `/api/v1/billing` | create-checkout, webhook, portal |
| leads | `/api/v1/leads` | get_leads, get_lead_summary |
| stripe_webhooks | `/api/v1/webhooks` | stripe |
| widget | `/api/v1/widget` | chat, config, lead |
| (health) | `/api` | health |
