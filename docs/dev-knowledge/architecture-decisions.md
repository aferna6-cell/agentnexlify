# Architecture Decisions — AgentNexLiFy

Why key technical choices were made. Claude Code reads this to avoid undoing intentional decisions.

---

### Multi-tenant from day one
Every table has tenant_id (or client_id for leads). All queries filter by it. Non-negotiable.

### FastAPI + Supabase (no ORM)
Direct Supabase client, not SQLAlchemy. Raw SQL migrations, not Alembic. Simpler, more explicit.

### React/Vite on Vercel, FastAPI on Railway
Separate hosting. CORS required for cross-origin API calls. Frontend is React/Vite (not Next.js).

### JWT for auth only, API for display data
JWT claims don't refresh when plan changes. Display data (plan name, usage counts) must come from live API calls.

### Widget as embeddable script
Lowest friction for customers. Works on any website via script tag. CORS must allow customer domains. Widget uses data-api-key attribute for tenant identification.

### Widget file sync requirement
widget/agentnexlify-widget.js and frontend/public/widget/agentnexlify-widget.js must be identical. Both serve the widget from different contexts.

### Numbered SQL migrations
Manual numbering in migrations/. Simple, explicit, no tooling dependency. Note: duplicate numbers exist at 005 and 007 (historical).

### chat_messages as canonical store
Migration 006 created chat_messages as the reliable message store. The older conversations table (migration 001) stores messages as JSONB and is considered unreliable.

### 4 Uvicorn workers in production
In-memory counters, caches, and background loops are per-process only. Do not treat them as globally authoritative.

### No setup fees, free tier prominent
Partner feedback: setup fees scare small businesses. Volume strategy.

### Only show built features on website
Trust-building. Don't market features that don't work yet.

### Businesses with no website = key market
Hosted business pages (agentnexlify.com/biz/{slug}) for businesses without websites. Added in migration 009.

### Plan naming
Canonical: free, growth ($199), professional ($399), enterprise ($799). Old names foundation and operations were renamed in migration 013.

### Unlimited conversations
Migration 013 cleared conversation limits. All plans now have unlimited conversations.

---

### Exception handling strategy
**Date:** 2026-03-11
**Decision:** Every `except` block must either (1) log the exception, (2) re-raise it, or (3) have a comment explaining why silence is intentional. Never use `except BaseException:` — always use `except Exception:` to allow `KeyboardInterrupt`, `SystemExit`, and `asyncio.CancelledError` to propagate for clean shutdown.
**Why:** 10 `except BaseException:` blocks in widget.py were preventing graceful Uvicorn shutdown. One was `except BaseException: pass` that silently swallowed lead scoring failures. Silent except blocks in analytics.py hid database errors.
**Enforcement:** Pre-commit hook checks for bare excepts. The QA agent audits for this pattern.

---

### lead_stage_change is an event name, not a column name
**Date:** 2026-03-11
**Decision:** Keep `lead_stage_change` as the automation trigger event name, even though the actual column is `status` (not `lead_stage`). The trigger event is a business concept stored in `automation_sequences.trigger_event` TEXT column.
**Why:** Renaming to `lead_status_change` would break existing data in production. The name is well-understood and only used as a string constant, never as a DB column filter.

---

_Add new decisions when significant architectural choices are made._
