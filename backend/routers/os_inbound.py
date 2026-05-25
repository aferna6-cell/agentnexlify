"""Agent OS inbound bridges — owner-gated toggle + config-read endpoints.

Lets a tenant owner flip widget / email / SMS / Facebook bridges on or off
and read the current merged config. Backed by
``backend.services.os_inbound_bridge`` toggle helpers, which persist to
``tenant_integrations`` under ``provider='os_inbound_bridges'``.

Spec: ``specs/agent-os-connectors-inbound_spec.md``
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 3
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services import os_inbound_bridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os/inbound", tags=["agent-os"])


BridgeSource = Literal["widget", "email", "sms", "facebook"]


class BridgeToggleRequest(BaseModel):
    source: BridgeSource
    enabled: bool


@router.get("/bridge-config")
async def get_bridge_config(
    claims: dict = Depends(_get_current_tenant),
) -> dict[str, Any]:
    """Return current merged bridge config for the caller's tenant.

    Read access is open to any authenticated tenant user so the settings
    UI can render the toggle row regardless of role.
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return os_inbound_bridge.get_bridge_config(db, client_id)


@router.post("/bridge-toggle")
async def set_bridge_toggle(
    req: BridgeToggleRequest,
    claims: dict = Depends(require_role("owner")),
) -> dict[str, Any]:
    """Flip a per-source bridge on or off. Owner-only.

    Bridges fan-in customer messages from external channels into the OS
    inbox — flipping one on starts persisting (and routing) inbound
    widget/email/sms/facebook traffic, so we gate this to the owner role
    the same way other consequential channel switches are gated.
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return os_inbound_bridge.set_bridge_toggle(db, client_id, req.source, req.enabled)
