# Winning Concept — 2026-06-09-pm (Run 53)

## Recommendation
Create `backend/tests/test_os_action_dispatch.py` — 5 mock-based tests covering `queue_action_for_run()` — labeled AUTONOMOUS-EXECUTABLE for tonight's nightly.

## Why This, Why Now
Agent OS Phase 4 (369b3c8) introduced `os_action_dispatch.py` (85L) as the shared idempotency guard for ALL approved agent actions: human click-to-approve (os_deliverables.py) and auto-send from the inbound bridge (agent_os_bridge.py). No test file exists — confirmed. With Agent OS shipping 2-3 PRs/day and PRs #211+#212 currently in review adding Act hardening and a research worker on top of this layer, each new PR extends untested code. The 2287f6b incident (widget_enabled default True, 2026-06-07) is a direct analogy: a one-line default in a bridge service caused all public chat widgets to route through Agent OS — caught only by a production bug report, not a test. `queue_action_for_run()` has five distinct execution paths, all mockable with `unittest.mock` in under 100 lines. The AUTONOMOUS-EXECUTABLE channel is confirmed working for backend/tests/ additions (precedent: nightly scope confirmed via 4226ef4).

## Implementation Sketch

1. **Verify slot is free:**
   ```bash
   ls backend/tests/test_os_action_dispatch.py 2>/dev/null || echo "MISSING — slot free"
   ```

2. **Create `backend/tests/test_os_action_dispatch.py`:**
   ```python
   """Tests for os_action_dispatch.queue_action_for_run()."""
   from unittest.mock import AsyncMock, MagicMock, patch
   import pytest
   from backend.services.os_action_dispatch import queue_action_for_run


   def _make_db(existing_succeeded=None, created_id="action-run-1"):
       db = MagicMock()
       tbl = MagicMock()
       db.return_value = tbl  # tenant_table returns tbl
       select_chain = MagicMock()
       select_chain.execute.return_value = MagicMock(
           data=[{"id": existing_succeeded}] if existing_succeeded else []
       )
       tbl.select.return_value = select_chain
       select_chain.eq.return_value = select_chain
       select_chain.limit.return_value = select_chain
       insert_chain = MagicMock()
       insert_chain.execute.return_value = MagicMock(data=[{"id": created_id}])
       tbl.insert.return_value = insert_chain
       return db


   @pytest.mark.asyncio
   async def test_no_action_type_returns_none():
       """run dict without action_type → None, no DB calls."""
       db = _make_db()
       result = await queue_action_for_run(db, "client-1", {}, None)
       assert result is None


   @pytest.mark.asyncio
   async def test_unknown_action_type_returns_none():
       """action_type not registered → None (warning logged)."""
       db = _make_db()
       with patch("backend.services.os_action_dispatch.get_action", return_value=None):
           result = await queue_action_for_run(
               db, "client-1", {"id": "run-1", "action_type": "unknown_type"}, None
           )
       assert result is None


   @pytest.mark.asyncio
   async def test_idempotent_returns_existing_succeeded():
       """Existing succeeded row → return its id without re-queuing."""
       db = _make_db(existing_succeeded="existing-action-run")
       with patch("backend.services.os_action_dispatch.get_action", return_value=AsyncMock()):
           with patch("backend.services.os_action_dispatch.tenant_table") as mock_tt:
               succeeded_resp = MagicMock()
               succeeded_resp.data = [{"id": "existing-action-run"}]
               chain = MagicMock()
               chain.select.return_value = chain
               chain.eq.return_value = chain
               chain.limit.return_value = chain
               chain.execute.return_value = succeeded_resp
               mock_tt.return_value = chain
               result = await queue_action_for_run(
                   db, "client-1", {"id": "run-1", "action_type": "booking"}, None
               )
       assert result == "existing-action-run"


   @pytest.mark.asyncio
   async def test_queues_background_task_when_provided():
       """BackgroundTasks provided → add_task called, action_run_id returned."""
       background = MagicMock()
       with patch("backend.services.os_action_dispatch.get_action", return_value=AsyncMock()):
           with patch("backend.services.os_action_dispatch.tenant_table") as mock_tt:
               no_succeeded = MagicMock()
               no_succeeded.data = []
               created = MagicMock()
               created.data = [{"id": "new-run"}]
               chain = MagicMock()
               chain.select.return_value = chain
               chain.eq.return_value = chain
               chain.limit.return_value = chain
               chain.execute.side_effect = [no_succeeded, created]
               chain.insert.return_value = chain
               mock_tt.return_value = chain
               result = await queue_action_for_run(
                   None, "client-1", {"id": "run-1", "action_type": "booking"}, background
               )
       assert result == "new-run"
       background.add_task.assert_called_once()


   @pytest.mark.asyncio
   async def test_runs_inline_without_background():
       """background=None → run_action awaited directly."""
       with patch("backend.services.os_action_dispatch.get_action", return_value=AsyncMock()):
           with patch("backend.services.os_action_dispatch.run_action", new_callable=AsyncMock) as mock_run:
               with patch("backend.services.os_action_dispatch.tenant_table") as mock_tt:
                   no_succeeded = MagicMock()
                   no_succeeded.data = []
                   created = MagicMock()
                   created.data = [{"id": "inline-run"}]
                   chain = MagicMock()
                   chain.select.return_value = chain
                   chain.eq.return_value = chain
                   chain.limit.return_value = chain
                   chain.execute.side_effect = [no_succeeded, created]
                   chain.insert.return_value = chain
                   mock_tt.return_value = chain
                   result = await queue_action_for_run(
                       None, "client-1", {"id": "run-1", "action_type": "booking"}, None
                   )
           assert result == "inline-run"
           mock_run.assert_awaited_once()
   ```

3. **Label in governance.json:** Set `status: "pending_autonomous"`, `autonomous_executable: true` on run 53 active_direction entry.

4. **Nightly executes:** Tonight's nightly (2:37 AM) reads AUTONOMOUS-EXECUTABLE label → creates `backend/tests/test_os_action_dispatch.py` with the above content.

5. **Verify (post-nightly):** `python3 -m pytest backend/tests/test_os_action_dispatch.py -q` — confirm 5 tests PASS. Grep confirms file exists.

## Bonus Actions (human, today)
- **Bonus A (5 min):** Merge PR #209 → closes GH #206 timing attack (Check 12 now WARNING on new patterns)
- **Bonus B (5 min):** Merge PR #200 → enables Items A+B autonomous execution (Check 10 + widget sync guard)
- **Bonus C (10 min):** Merge PR #183 → closes GH #181 billing fix (AMOUNT_TO_PLAN 15000/25000), unblocks email_sequences.py split

## What This Replaces
Run 52 active direction (Check 12) is fully implemented (ca3ce68). Run 53 opens a new code_health direction targeting Agent OS test coverage.

## Confidence
**HIGH** — Evidence: 0 tests confirmed via `ls` (not an estimate). Implementation: all 5 test cases are standard mock-based patterns with no Supabase fixture dependency. Autonomous channel: confirmed for backend/tests/ additions. Timing: PRs #211/#212 currently in review — tests land before or concurrent with new features.
