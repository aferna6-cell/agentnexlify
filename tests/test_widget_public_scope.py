"""The public widget chat may only reach customer-facing code.

POST /api/v1/widget/chat is anonymous. It answers business questions from the
tenant's own grounding and may capture leads, book, order, and hand off to a
human. Owner/dashboard tools (content repurpose, campaigns, social posting,
settings, analytics, the Agent OS orchestrator) must stay behind authenticated
dashboard routes. In 2026-11 the widget ran Content Repurpose for an anonymous
visitor; this allowlist makes a new owner-tool import in the widget pipeline
fail CI instead of shipping.

Adding a module here is a product decision: confirm it is customer-facing.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGET_PIPELINE = sorted((ROOT / "backend" / "routers").glob("widget_chat*.py"))

ALLOWED_BACKEND_IMPORTS = {
    "backend.config",
    "backend.limiter",
    "backend.middleware.rate_limit",
    "backend.models.database",
    "backend.models.schemas",
    # Widget pipeline siblings and customer-facing widget flows.
    "backend.routers.widget_booking",
    "backend.routers.widget_chat_booking_action",
    "backend.routers.widget_chat_context",
    "backend.routers.widget_chat_effects",
    "backend.routers.widget_chat_fallback",
    "backend.routers.widget_chat_guards",
    "backend.routers.widget_chat_helpers",
    "backend.routers.widget_lead_helpers",
    # Grounding, guards, metering, logging.
    "backend.services.activity",
    "backend.services.ai_usage_guard",
    "backend.services.booking",
    "backend.services.booking_prompt",
    "backend.services.conversation_memory",
    "backend.services.customer_memory",
    "backend.services.embeddings",
    "backend.services.industry_packs",
    "backend.services.kb_hybrid_retrieval",
    "backend.services.kb_provenance",
    "backend.services.kb_reranker",
    "backend.services.llm_runtime",
    "backend.services.support_intent",
    "backend.services.tenant_scope",
    "backend.services.webhook_dispatcher",
    "backend.services.website_crawler",
    "backend.services.widget_guard",
    # Support-only second-tier answerer (tenant KB, no owner tools).
    "backend.services.agent_sdk_client",
    "backend.services.managed_agents_registry",
    "backend.services.support_agent",
    # Handoff/escalation: notify the owner, open an escalation.
    "backend.services.conversation_notify",
    "backend.services.email_sender",
    "backend.services.escalations",
    "backend.services.twilio_service",
    # Observe-only for source="widget" (never runs the orchestrator).
    "backend.services.os_inbound_bridge",
}


def _backend_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            if not node.module.startswith("backend"):
                continue
            if node.module in ("backend", "backend.routers", "backend.services"):
                found.update(f"{node.module}.{a.name}" for a in node.names)
            else:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("backend"))
    return found


def test_widget_pipeline_imports_only_customer_facing_modules():
    assert WIDGET_PIPELINE, "widget_chat*.py not found"
    offenders = {
        f"{path.name}: {mod}"
        for path in WIDGET_PIPELINE
        for mod in _backend_imports(path) - ALLOWED_BACKEND_IMPORTS
    }
    assert not offenders, (
        "Public widget chat imports a module outside the customer-facing "
        f"allowlist: {sorted(offenders)}"
    )


def test_widget_pipeline_never_imports_content_repurposer():
    for path in WIDGET_PIPELINE:
        assert "content_repurposer" not in path.read_text(encoding="utf-8"), path.name


def test_widget_request_has_no_content_mode_switch():
    from backend.models.schemas import WidgetChatRequest

    assert "content_mode" not in WidgetChatRequest.model_fields
    req = WidgetChatRequest(
        api_key="k", session_id="s", message="m", content_mode=True
    )
    assert not hasattr(req, "content_mode")


def test_dashboard_repurpose_route_still_mounted_behind_auth():
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    # Owner repurpose keeps working on the dashboard (full behavior is in
    # tests/test_content_repurpose_api.py); it is mounted and needs a login.
    resp = client.post(
        "/api/v1/repurpose/t1",
        json={"source_type": "text", "source_input": "hello"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code in (401, 403), resp.text
