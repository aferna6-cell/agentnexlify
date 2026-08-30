#!/usr/bin/env python3
"""Controlled M8 Calendar/CRM smoke — stops at auth boundary when unset.

Requires explicit env authorization:

  M8_SMOKE_AUTHORIZED=1
  M8_SMOKE_CLIENT_ID=<staging tenant uuid>
  CALENDAR_ACTIONS_ENABLED=1
  CRM_ACTIONS_ENABLED=1

Plus working Supabase service credentials and (for Calendar) Google OAuth on
that tenant. Without M8_SMOKE_AUTHORIZED=1 this script exits 2 and prints the
boundary — it never mutates production.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("M8_SMOKE_AUTHORIZED", "").strip() != "1":
        print("M8 SMOKE STOPPED AT AUTH BOUNDARY")
        print("Set M8_SMOKE_AUTHORIZED=1 and M8_SMOKE_CLIENT_ID to a staging")
        print("tenant with a harmless calendar / test lead before running.")
        print("Checklist (manual once authorized):")
        print("  Calendar: availability, create once, GET verify, cancel,")
        print("            invite parks, approve once, redrive no-dup,")
        print("            wrong-tenant fails, audit complete")
        print("  CRM: tenant search, ambiguous clarify, partial update,")
        print("       read-back, duplicate create blocked, stage validate,")
        print("       cross-tenant refuse, audit complete")
        return 2

    client_id = os.environ.get("M8_SMOKE_CLIENT_ID", "").strip()
    if not client_id:
        print("M8_SMOKE_CLIENT_ID required when authorized")
        return 2

    # Live path is owner-operated against staging APIs; this entrypoint only
    # confirms flags + wiring imports when authorized.
    os.environ.setdefault("CALENDAR_ACTIONS_ENABLED", "1")
    os.environ.setdefault("CRM_ACTIONS_ENABLED", "1")
    from backend.services import os_calendar_crm
    from backend.services.m8_action_flags import (
        calendar_actions_enabled,
        crm_actions_enabled,
    )

    assert calendar_actions_enabled() and crm_actions_enabled()
    assert os_calendar_crm.refuse_calendar_tool() is None
    assert os_calendar_crm.refuse_crm_tool() is None
    print(f"M8 smoke authorized for client_id={client_id}")
    print("Run staging API checklist from docs/milestone-8-calendar-crm.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
