"""Tests for per-tenant intent configuration (migration 112).

Covers:
- _build_intent_block: all field combinations
- _intent_id_to_prose: snake_case → prose conversion
- _build_system_prompt: intent_config param (spec acceptance criteria)
- _get_or_create_conversation: intent_config_snapshot saved on new convs
- get_intent_presets endpoint: returns all 6 presets
- IntentConfig Pydantic model: validation
"""

import os

os.environ["TESTING"] = "1"

from unittest.mock import MagicMock, patch


from backend.routers.widget_chat_helpers import (
    _build_intent_block,
    _build_system_prompt,
    _intent_id_to_prose,
)
from backend.models.schemas import IntentConfig

_TENANT = {
    "business_name": "Test Plumbing",
    "business_type": "plumbing",
    "city": "Miami",
}


# ---------------------------------------------------------------------------
# _intent_id_to_prose
# ---------------------------------------------------------------------------


class TestIntentIdToProse:
    def test_snake_case_converted(self):
        assert _intent_id_to_prose("never_promise_pricing") == "Never promise pricing"

    def test_prose_passthrough(self):
        result = _intent_id_to_prose("Always ask for service address")
        assert result == "Always ask for service address"

    def test_single_word(self):
        assert _intent_id_to_prose("accuracy") == "accuracy"

    def test_empty_string(self):
        assert _intent_id_to_prose("") == ""


# ---------------------------------------------------------------------------
# _build_intent_block
# ---------------------------------------------------------------------------


class TestBuildIntentBlock:
    def test_primary_goal_label_rendered(self):
        block = _build_intent_block({"primary_goal": "book_appointment"})
        assert "<intent_config>" in block
        assert "</intent_config>" in block
        assert "BOOK AN APPOINTMENT" in block

    def test_secondary_goal_rendered_when_set(self):
        block = _build_intent_block(
            {
                "primary_goal": "book_appointment",
                "secondary_goal": "capture_lead",
            }
        )
        assert "CAPTURE LEAD" in block
        assert "secondary goal" in block.lower()

    def test_secondary_goal_omitted_when_not_set(self):
        block = _build_intent_block({"primary_goal": "book_appointment"})
        assert "secondary goal" not in block.lower()

    def test_tone_rendered(self):
        block = _build_intent_block({"tone": "professional_warm"})
        assert "professional and warm" in block

    def test_unknown_tone_uses_raw_value(self):
        block = _build_intent_block({"tone": "custom_tone"})
        assert "custom tone" in block

    def test_trade_off_hierarchy_rendered(self):
        block = _build_intent_block(
            {"trade_off_hierarchy": ["accuracy", "safety", "speed"]}
        )
        assert "accuracy" in block
        assert "safety" in block
        assert "speed" in block

    def test_constraints_rendered(self):
        block = _build_intent_block(
            {"constraints": ["never_promise_pricing", "Always confirm in writing"]}
        )
        assert "Never promise pricing" in block
        assert "Always confirm in writing" in block

    def test_escalation_triggers_rendered(self):
        block = _build_intent_block(
            {
                "escalation_triggers": [
                    "customer_expresses_frustration",
                    "Customer requests human",
                ]
            }
        )
        assert "Customer expresses frustration" in block
        assert "Customer requests human" in block

    def test_empty_dict_produces_minimal_block(self):
        block = _build_intent_block({})
        assert "<intent_config>" in block
        assert "</intent_config>" in block

    def test_all_known_primary_goals(self):
        goals = [
            "book_appointment",
            "capture_lead",
            "qualify_lead",
            "answer_question",
            "generate_quote",
            "general_support",
        ]
        for goal in goals:
            block = _build_intent_block({"primary_goal": goal})
            assert "<intent_config>" in block

    def test_unknown_primary_goal_uppercased(self):
        block = _build_intent_block({"primary_goal": "custom_goal"})
        assert "CUSTOM_GOAL" in block


# ---------------------------------------------------------------------------
# _build_system_prompt with intent_config (spec acceptance criteria)
# ---------------------------------------------------------------------------


class TestBuildSystemPromptIntentConfig:
    def test_intent_config_none_no_block(self):
        """Spec AC: intent_config=None → no <intent_config> block (backward compat)."""
        prompt = _build_system_prompt(_TENANT, [], intent_config=None)
        assert "<intent_config>" not in prompt
        assert "</intent_config>" not in prompt

    def test_intent_config_set_includes_block(self):
        """Spec AC: intent_config set → <intent_config> block present."""
        prompt = _build_system_prompt(
            _TENANT,
            [],
            intent_config={
                "primary_goal": "book_appointment",
                "tone": "professional_warm",
            },
        )
        assert "<intent_config>" in prompt
        assert "BOOK AN APPOINTMENT" in prompt
        assert "</intent_config>" in prompt

    def test_intent_block_before_custom_instructions(self):
        """Intent block placed before custom_instructions in prompt."""
        prompt = _build_system_prompt(
            _TENANT,
            [],
            intent_config={"primary_goal": "capture_lead"},
            custom_instructions="Call us at 555-1234.",
        )
        intent_pos = prompt.index("<intent_config>")
        custom_pos = prompt.index("Call us at 555-1234.")
        assert intent_pos < custom_pos

    def test_intent_block_with_constraints(self):
        prompt = _build_system_prompt(
            _TENANT,
            [],
            intent_config={
                "primary_goal": "generate_quote",
                "constraints": ["always_confirm_scope_in_writing"],
                "escalation_triggers": ["customer_expresses_frustration"],
            },
        )
        assert "Always confirm scope in writing" in prompt
        assert "Customer expresses frustration" in prompt

    def test_backward_compat_identity_line_unchanged(self):
        """NULL intent_config doesn't change identity line."""
        prompt_without = _build_system_prompt(_TENANT, [], intent_config=None)
        prompt_with = _build_system_prompt(
            _TENANT,
            [],
            intent_config={"primary_goal": "capture_lead"},
        )
        assert "You are a friendly AI assistant for Test Plumbing" in prompt_without
        assert "You are a friendly AI assistant for Test Plumbing" in prompt_with

    def test_platform_rules_present_regardless_of_intent(self):
        prompt = _build_system_prompt(
            _TENANT,
            [],
            intent_config={"primary_goal": "book_appointment"},
        )
        assert "Platform-owned rules always override" in prompt


# ---------------------------------------------------------------------------
# _get_or_create_conversation: snapshot saved on new conversation
# ---------------------------------------------------------------------------


class TestGetOrCreateConversationSnapshot:
    def _make_db(self, existing_id=None, upsert_id="new-conv-id"):
        db = MagicMock()
        select_chain = MagicMock()
        if existing_id:
            select_chain.execute.return_value = MagicMock(data=[{"id": existing_id}])
        else:
            select_chain.execute.return_value = MagicMock(data=[])
        select_chain.eq.return_value = select_chain
        select_chain.limit.return_value = select_chain
        db.table.return_value.select.return_value = select_chain

        upsert_chain = MagicMock()
        upsert_chain.execute.return_value = MagicMock(data=[{"id": upsert_id}])
        db.table.return_value.upsert.return_value = upsert_chain
        return db

    @patch("backend.routers.widget_chat_helpers.tenant_select")
    @patch("backend.routers.widget_chat_helpers.tenant_upsert")
    @patch("backend.routers.widget_chat_helpers.get_service_supabase")
    def test_snapshot_passed_to_upsert_on_new_conversation(
        self, mock_db, mock_upsert, mock_select
    ):
        from backend.routers.widget_chat_helpers import _get_or_create_conversation

        mock_db.return_value = MagicMock()
        # No existing conversation
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[])
        mock_select.return_value = select_chain

        upsert_chain = MagicMock()
        upsert_chain.execute.return_value = MagicMock(data=[{"id": "new-uuid"}])
        mock_upsert.return_value = upsert_chain

        snapshot = {"primary_goal": "book_appointment", "schema_version": "1.0"}
        conv_id, is_new = _get_or_create_conversation(
            "tenant-1", "session-abc", intent_config_snapshot=snapshot
        )

        assert is_new is True
        assert conv_id == "new-uuid"
        call_kwargs = mock_upsert.call_args
        payload = call_kwargs[0][3]
        assert payload["intent_config_snapshot"] == snapshot

    @patch("backend.routers.widget_chat_helpers.tenant_select")
    @patch("backend.routers.widget_chat_helpers.get_service_supabase")
    def test_existing_conversation_returns_without_snapshot(self, mock_db, mock_select):
        from backend.routers.widget_chat_helpers import _get_or_create_conversation

        mock_db.return_value = MagicMock()
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[{"id": "existing-uuid"}])
        mock_select.return_value = select_chain

        conv_id, is_new = _get_or_create_conversation(
            "tenant-1",
            "session-abc",
            intent_config_snapshot={"primary_goal": "capture_lead"},
        )

        assert conv_id == "existing-uuid"
        assert is_new is False

    @patch("backend.routers.widget_chat_helpers.tenant_select")
    @patch("backend.routers.widget_chat_helpers.tenant_upsert")
    @patch("backend.routers.widget_chat_helpers.get_service_supabase")
    def test_no_snapshot_when_none(self, mock_db, mock_upsert, mock_select):
        from backend.routers.widget_chat_helpers import _get_or_create_conversation

        mock_db.return_value = MagicMock()
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute.return_value = MagicMock(data=[])
        mock_select.return_value = select_chain

        upsert_chain = MagicMock()
        upsert_chain.execute.return_value = MagicMock(data=[{"id": "new-uuid"}])
        mock_upsert.return_value = upsert_chain

        _get_or_create_conversation(
            "tenant-1", "session-abc", intent_config_snapshot=None
        )

        payload = mock_upsert.call_args[0][3]
        assert "intent_config_snapshot" not in payload


# ---------------------------------------------------------------------------
# GET /config/intent-presets endpoint
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET /config/intent-presets endpoint
# ---------------------------------------------------------------------------


class TestIntentPresetsEndpoint:
    def test_returns_all_six_presets(self):
        from backend.routers.widget_config import _INTENT_PRESETS

        assert set(_INTENT_PRESETS.keys()) == {
            "trades",
            "medical",
            "legal",
            "retail",
            "ecommerce",
            "general",
        }

    def test_each_preset_has_primary_goal(self):
        from backend.routers.widget_config import _INTENT_PRESETS

        for name, preset in _INTENT_PRESETS.items():
            assert "primary_goal" in preset, f"preset '{name}' missing primary_goal"

    def test_trades_preset_goal(self):
        from backend.routers.widget_config import _INTENT_PRESETS

        assert _INTENT_PRESETS["trades"]["primary_goal"] == "book_appointment"

    def test_medical_preset_tone(self):
        from backend.routers.widget_config import _INTENT_PRESETS

        assert _INTENT_PRESETS["medical"]["tone"] == "formal"


# ---------------------------------------------------------------------------
# IntentConfig Pydantic model
# ---------------------------------------------------------------------------


class TestIntentConfigModel:
    def test_defaults(self):
        ic = IntentConfig()
        assert ic.schema_version == "1.0"
        assert ic.primary_goal is None

    def test_all_fields_set(self):
        ic = IntentConfig(
            primary_goal="book_appointment",
            secondary_goal="capture_lead",
            tone="professional_warm",
            trade_off_hierarchy=["accuracy", "speed"],
            constraints=["never_promise_pricing"],
            escalation_triggers=["customer_requests_human"],
            preset="trades",
        )
        assert ic.primary_goal == "book_appointment"
        assert ic.preset == "trades"

    def test_model_dump_serializes_to_dict(self):
        ic = IntentConfig(primary_goal="capture_lead")
        d = ic.model_dump()
        assert isinstance(d, dict)
        assert d["primary_goal"] == "capture_lead"
