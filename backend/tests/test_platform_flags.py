"""platform_flags (migration 175): DB flag overrides with env fallback.

Contract:

  1. A platform_settings row wins over the env/config fallback - including
     "0" acting as a kill switch through resolve_int_setting.
  2. No row (or DB failure) -> the caller's env fallback is used; flag
     reads never raise.
  3. Under TESTING the DB is never touched, so the whole existing suite
     keeps exercising pure env/config behavior.
  4. reward_enabled() honors a referral_reward_enabled row (GH #413's
     activation no longer requires a Railway env change).
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services import platform_flags
from backend.services.llm_runtime import resolve_int_setting


def _db_with_row(value):
    db = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    result = MagicMock()
    result.data = [{"value": value}] if value is not None else []
    chain.execute.return_value = result
    db.table.return_value = chain
    return db


def _live(db):
    """Patch out the TESTING short-circuit and the DB for one call."""
    return patch.multiple(
        platform_flags,
        _testing=lambda: False,
    ), patch(
        "backend.models.database.get_service_supabase", return_value=db
    )


def _flag_value_live(db, key):
    platform_flags.clear_cache()
    p1, p2 = _live(db)
    with p1, p2:
        return platform_flags.flag_value(key)


def test_db_row_wins():
    assert _flag_value_live(_db_with_row("1"), "some_flag") == "1"


def test_missing_row_returns_none():
    assert _flag_value_live(_db_with_row(None), "some_flag") is None


def test_db_failure_fails_open_to_none():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    assert _flag_value_live(db, "some_flag") is None


def test_flag_enabled_truthiness():
    with patch.object(platform_flags, "flag_value", return_value="true"):
        assert platform_flags.flag_enabled("x", env_default=False) is True
    with patch.object(platform_flags, "flag_value", return_value="0"):
        assert platform_flags.flag_enabled("x", env_default=True) is False
    with patch.object(platform_flags, "flag_value", return_value=None):
        assert platform_flags.flag_enabled("x", env_default=True) is True


def test_testing_mode_never_touches_db():
    platform_flags.clear_cache()
    with patch("backend.models.database.get_service_supabase") as db:
        assert platform_flags.flag_value("anything") is None
        db.assert_not_called()


def test_resolve_int_setting_db_override_wins_and_zero_kills():
    with patch("backend.services.platform_flags.flag_value", return_value="1"):
        assert resolve_int_setting("widget_kb_rerank_enabled", 0) == 1
    # "0" beats an env-enabled setting: DB row is a kill switch.
    with patch("backend.services.platform_flags.flag_value", return_value="0"):
        with patch("backend.services.llm_runtime.settings") as s:
            s.widget_kb_rerank_enabled = 1
            assert resolve_int_setting("widget_kb_rerank_enabled", 0) == 0


def test_resolve_int_setting_garbage_override_falls_back():
    with patch("backend.services.platform_flags.flag_value", return_value="banana"):
        assert resolve_int_setting("widget_kb_rerank_enabled", 7) == 7


def test_reward_enabled_honors_db_flag():
    from backend.services import referral_reward

    with patch(
        "backend.services.platform_flags.flag_value", return_value="1"
    ), patch.dict(os.environ, {"REFERRAL_REWARD_ENABLED": "0"}):
        assert referral_reward.reward_enabled() is True
    with patch(
        "backend.services.platform_flags.flag_value", return_value=None
    ), patch.dict(os.environ, {"REFERRAL_REWARD_ENABLED": "1"}):
        assert referral_reward.reward_enabled() is True
    with patch(
        "backend.services.platform_flags.flag_value", return_value="0"
    ), patch.dict(os.environ, {"REFERRAL_REWARD_ENABLED": "1"}):
        # DB "0" is a kill switch even when env says on.
        assert referral_reward.reward_enabled() is False
