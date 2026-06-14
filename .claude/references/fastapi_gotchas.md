# FastAPI Gotchas — Reference Pack

Load before editing `backend/main.py`, any file in `backend/routers/`, or any Pydantic model.

## Deferred Annotations — HARD BAN

**Forbidden:**
```python
from __future__ import annotations  # BANS PER CLAUDE.md INVARIANT #5
```

**Why:** PEP 563 makes Pydantic resolve bodies as strings. Every request 422s silently. Shipped this bug multiple times.

**Enforcement:** pre-commit hook blocks commits containing this import.

**Fix if already present:** remove the import, run `pytest backend/tests/` to confirm no regressions.

## Route Registration Order

Static routes MUST register BEFORE parameterized routes.

**Wrong:**
```python
@router.get("/leads/{lead_id}")
def get_lead(lead_id: str): ...

@router.get("/leads/export")  # UNREACHABLE — matches /{lead_id}
def export_leads(): ...
```

**Right:**
```python
@router.get("/leads/export")
def export_leads(): ...

@router.get("/leads/{lead_id}")
def get_lead(lead_id: str): ...
```

**Why:** FastAPI matches first-registered. `/leads/export` gets eaten by `/leads/{lead_id}` with `lead_id="export"`.

## Main.py Router Registration

New router → register in `backend/main.py` lines ~746-813.

**Required:**
- Import router at top of main.py
- `app.include_router(router, prefix="/api/...", tags=[...])` in the registration block
- Tag names match sidebar entries when feasible

## Pydantic v2 Patterns

**Required:**
- Use `model_validate()` not `parse_obj()` (v1 removed)
- Use `model_dump()` not `dict()` (v1 removed)
- `ConfigDict` not nested `class Config`
- Field validators use `@field_validator('x')` not `@validator('x')`

## Bare Except — HARD BAN

**Forbidden:**
```python
try:
    thing()
except:  # BLOCKED BY PRE-COMMIT
    pass

try:
    thing()
except Exception:  # BLOCKED WHEN PAIRED WITH pass AND NO LOGGING
    pass
```

**Required:**
- Catch specific exceptions by type
- Log before swallowing (never swallow silently)
- Re-raise or return explicit error

## Async Discipline

**Required:**
- `async def` routes → all I/O awaited, no `requests.get`, use `httpx.AsyncClient`
- No sync DB calls in async routes — use async Supabase client or run in threadpool
- Background tasks via `BackgroundTasks`, not fire-and-forget `asyncio.create_task` without retention

**Forbidden:**
- Mixing `requests` + `async def` — blocks the event loop
- `time.sleep()` in async routes — use `asyncio.sleep()`
- Unawaited coroutines (check with `pytest-asyncio` mode strict)

## Dependency Injection

Auth + tenant scoping go through FastAPI `Depends()`.

**Pattern:**
```python
@router.get("/leads")
async def list_leads(
    client: Client = Depends(get_current_client),
    supabase: SupabaseClient = Depends(get_supabase),
):
    return await leads_service.list_for(client.id, supabase)
```

Never hand-roll tenant resolution inside the route body — see `tenant_isolation.md`.

## Request/Response Models

**Required:**
- Every route declares `response_model=...` — FastAPI validates outbound
- Request body uses explicit Pydantic model, never `dict`
- OpenAPI schema stays clean for frontend type-gen

## Error Shape

Standardized error:
```python
{"detail": "human readable", "code": "MACHINE_READABLE", "trace_id": "..."}
```

Frontend parses `code` for UX decisions. Never leak stack traces to tenant-facing responses.

## Anti-patterns

- Never add `from __future__ import annotations` — pre-commit blocks it but don't even try
- Never register a param route before its static siblings
- Never `except:` or `except Exception: pass` without logging
- Never block the event loop with sync I/O in async handlers
- Never hand-roll tenant scoping — use `Depends`

## Cross-refs

- `CLAUDE.md` — Critical invariant #5 (no `__future__`)
- `.claude/rules/python-fastapi.md`
- `.claude/rules/api-conventions.md`
- `backend/CONTEXT.md`
- `tenant_isolation.md` sibling pack
