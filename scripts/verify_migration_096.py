"""Smoke-test migration 096 hardening primitives against a staging database.

Required env vars:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY
  STAGING_TENANT_ID
"""

from __future__ import annotations

import os
import sys
import uuid

from supabase import create_client


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> int:
    supabase_url = _required_env("SUPABASE_URL")
    service_key = _required_env("SUPABASE_SERVICE_KEY")
    tenant_id = _required_env("STAGING_TENANT_ID")

    client = create_client(supabase_url, service_key)

    tenant = client.table("tenants").select("id").eq("id", tenant_id).limit(1).execute()
    if not tenant.data:
        raise RuntimeError(f"STAGING_TENANT_ID was not found: {tenant_id}")

    lock_name = f"migration-096-smoke-{uuid.uuid4().hex}"
    owner = f"smoke-{uuid.uuid4().hex}"
    acquired = client.rpc(
        "try_acquire_automation_lock",
        {"p_name": lock_name, "p_owner": owner, "p_ttl_seconds": 30},
    ).execute()
    if acquired.data is not True:
        raise RuntimeError("try_acquire_automation_lock did not return true")

    client.rpc("release_automation_lock", {"p_name": lock_name, "p_owner": owner}).execute()

    quota = client.rpc(
        "reserve_email_send_quota",
        {"p_tenant_id": tenant_id, "p_daily_limit": 1_000_000},
    ).execute()
    if quota.data is not True:
        raise RuntimeError("reserve_email_send_quota did not return true")

    oauth_row = {
        "provider": "migration_096_smoke",
        "nonce": uuid.uuid4().hex,
        "tenant_id": tenant_id,
        "expires_at": "2099-01-01T00:00:00Z",
    }
    inserted = client.table("oauth_states").insert(oauth_row).execute()
    if not inserted.data:
        raise RuntimeError("oauth_states insert returned no data")
    client.table("oauth_states").delete().eq("provider", oauth_row["provider"]).eq(
        "nonce", oauth_row["nonce"]
    ).execute()

    print("migration 096 smoke test passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"migration 096 smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
