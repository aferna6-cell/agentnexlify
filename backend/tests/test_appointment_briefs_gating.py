"""Guard-stack tests for appointment_briefs (GH #643).

Contract: both endpoints sit behind block_demo_role + require_agent_os_access
at the router, and _check_ai_budget raises 429 once the tenant's monthly AI
hard limit is reached — failing open on lookup errors so a DB blip never
blocks a paying owner.

Run: pytest backend/tests/test_appointment_briefs_gating.py --noconftest -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import appointment_briefs as ab


def test_router_dependencies_include_demo_block_and_plan_gate():
    from backend.dependencies import block_demo_role
    from backend.services.agent_os_gate import require_agent_os_access

    deps = [d.dependency for d in ab.router.dependencies]
    assert block_demo_role in deps
    assert require_agent_os_access in deps


def test_check_ai_budget_blocks_when_hard_limit_reached():
    with patch.object(
        ab, "get_ai_usage_status", return_value={"hard_limit_reached": True}
    ):
        with pytest.raises(HTTPException) as exc:
            ab._check_ai_budget(MagicMock(), "t-1")
    assert exc.value.status_code == 429


def test_check_ai_budget_allows_under_limit():
    with patch.object(
        ab, "get_ai_usage_status", return_value={"hard_limit_reached": False}
    ):
        ab._check_ai_budget(MagicMock(), "t-1")  # no raise


def test_check_ai_budget_fails_open_on_lookup_error():
    with patch.object(
        ab, "get_ai_usage_status", side_effect=RuntimeError("db down")
    ):
        ab._check_ai_budget(MagicMock(), "t-1")  # no raise


def test_agent_os_plan_set_excludes_chatbot_and_free():
    from backend.services.agent_os_gate import AGENT_OS_PLANS

    assert "chatbot" not in AGENT_OS_PLANS
    assert "free" not in AGENT_OS_PLANS
    assert "agent_os" in AGENT_OS_PLANS
