"""Guard: demo_seed's widget_configs payload only uses real columns.

The seeder silently failed for every vertical (non-fatal log) because its
payload carried collect_name/collect_email/collect_phone - columns that never
existed - and omitted the NOT NULL api_key. Found 2026-07-14: salon +
financial demo tenants had no widget at all. This test pins the payload to
the actual schema so the next phantom column fails CI instead of prod.
"""

import ast
from pathlib import Path

# Column allow-list mirrors prod widget_configs (information_schema check
# 2026-07-14). Update alongside migrations that touch widget_configs.
WIDGET_CONFIG_COLUMNS = {
    "id", "tenant_id", "api_key", "bot_name", "primary_color",
    "greeting_message", "position", "show_watermark", "allowed_domains",
    "booking_enabled", "branding", "is_online", "offline_message",
    "teaser_message", "custom_instructions", "teaser_delay_seconds",
    "teaser_enabled", "knowledge_base", "pre_chat_form",
    "enable_ai_fallback", "enable_structured_lead_parser",
    "onboarding_version", "ready_to_launch", "readiness_criteria",
}

_SEED_PATH = Path(__file__).resolve().parents[1] / "services" / "demo_seed.py"


def _widget_insert_keys() -> set:
    """Extract the key set of the dict passed to table("widget_configs").insert."""
    tree = ast.parse(_SEED_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "insert"):
            continue
        table_call = getattr(func.value, "func", None)
        if not (
            isinstance(table_call, ast.Attribute) and table_call.attr == "table"
        ):
            continue
        table_args = func.value.args
        if not (
            table_args
            and isinstance(table_args[0], ast.Constant)
            and table_args[0].value == "widget_configs"
        ):
            continue
        payload = node.args[0]
        if isinstance(payload, ast.Dict):
            return {
                k.value for k in payload.keys if isinstance(k, ast.Constant)
            }
    raise AssertionError("widget_configs insert not found in demo_seed.py")


def test_seed_payload_uses_only_real_columns():
    keys = _widget_insert_keys()
    phantom = keys - WIDGET_CONFIG_COLUMNS
    assert not phantom, f"demo_seed inserts nonexistent widget_configs columns: {phantom}"


def test_seed_payload_satisfies_not_null_api_key():
    assert "api_key" in _widget_insert_keys()
