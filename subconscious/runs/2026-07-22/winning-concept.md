# Winning Concept — Run 100

**Date:** 2026-07-22  
**Run:** 100 (milestone)  
**Category:** code_health / security  
**Effort:** M  
**Status:** RECOMMENDATION — awaiting human approval

---

## Title
Fix Agent OS plan gate coverage gap: 10 ungated `os_*` routers

## Problem
Architecture audit `audits/audit-architecture-2026-07-22.md` finding H1:

21 `os_*` routers registered in FastAPI. Only 11 have `dependencies=[Depends(require_agent_os_access)]`. 10 routers are ungated:

```
os_agent_runs    os_backlog   os_files    os_graph    os_insights
os_memory        os_run_trace os_sync     os_usage    os_usage_breakdown
```

A `chatbot`-plan tenant ($19.99/mo) calling any of these endpoints gets the response that should be `agent_os`-only ($99.99/mo). The plan gate is silent — no 402, no error, just full access.

## Why this matters
- **Revenue leak**: $80/mo delta per tenant that exploits this. Plan integrity is a billing invariant.
- **Tier trustworthiness**: `agent_os` features are the product's premium value proposition. Leaking them undercuts the upgrade path.
- **CLAUDE.md mandate**: "New gates → add to `backend/tests/test_plan_gating_new_plans.py`". Existing gating pattern is established; these routers missed it.

## Recommended fix (DO NOT IMPLEMENT — human approves first)

### 1. File GitHub issue
Title: `fix: require_agent_os_access missing from 10 os_* routers (H1 architecture audit)`

Body should include:
- Link to `audits/audit-architecture-2026-07-22.md` §H1
- List of 10 ungated routers with file paths
- Fix: add `dependencies=[Depends(require_agent_os_access)]` in each router constructor call in `backend/main.py` registration block (lines 746–813)
- Test requirement: add 10 test cases to `backend/tests/test_plan_gating_new_plans.py` — one per router, asserting 402 for `chatbot` plan
- Label: `backend`, `security`, `ai-ready`

### 2. Implementation shape (for the assigned PR)
In `backend/main.py`, for each of the 10 ungated routers:
```python
# Before (ungated):
app.include_router(os_memory.router, prefix="/api", tags=["os"])

# After (gated):
app.include_router(
    os_memory.router,
    prefix="/api",
    tags=["os"],
    dependencies=[Depends(require_agent_os_access)],
)
```

### 3. Test shape
```python
def test_os_memory_requires_agent_os_plan(chatbot_client):
    response = chatbot_client.get("/api/os/memory")
    assert response.status_code == 402
```

## What this does NOT do
- Does not change any router logic
- Does not change any schema
- Does not affect `agent_os` tenants (they still get full access)
- Does not break existing passing tests

## Success criteria
- All 10 routers return 402 for `chatbot`-plan test client
- All 10 return 200 for `agent_os`-plan test client
- `test_plan_gating_new_plans.py` has 10 new test cases passing
- Architecture audit re-run shows H1 resolved
