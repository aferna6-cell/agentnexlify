#!/usr/bin/env python3
"""Milestone 8 live staging smoke — real data-plane / provider evidence.

This is the real runner. ``m8_controlled_smoke.py`` delegates here.

Hard gates (all required; refuse otherwise — never silently target production):

  M8_SMOKE_AUTHORIZED=1
  M8_SMOKE_CLIENT_ID=<staging/smoke tenant uuid>
  M8_SMOKE_ENV=staging
  M8_SMOKE_CONFIRM_ENV=staging

Optional suites (comma-separated in M8_SMOKE_SUITES, default calendar,crm):

  calendar  — availability, internal create, read-back, cancel, cross-tenant
  crm       — search/update/create/dedupe/stage/cross-tenant via data plane
  gmail     — propose/approve/send/Message-ID/redrive (needs SEND_EMAIL_ENABLED=1)
  rag       — in-process soak with RAG_ENABLED=1, DEFAULT_MIN_SCORE=1.0 frozen

Requires for Calendar/Gmail/CRM Action Executor path:
  SUPABASE_URL + SUPABASE_SERVICE_KEY (or SUPABASE_SERVICE_ROLE_KEY)
  Google OAuth on the smoke tenant for Calendar
  Gmail connector on the smoke tenant for Gmail

Writes a non-sensitive evidence JSON under audits/artifacts/ when possible.
Exit codes:
  0  all requested suites that could run passed
  2  authorization / env confirmation boundary
  3  missing credentials / provider not connected (honest stop)
  4  smoke assertion failure
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "audits" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        return out
    except Exception:
        return "unknown"


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _require_auth() -> tuple[str, dict]:
    """Return (client_id, evidence_meta) or exit 2."""
    if not _truthy("M8_SMOKE_AUTHORIZED"):
        print("M8 LIVE SMOKE STOPPED AT AUTH BOUNDARY")
        print("Required:")
        print("  M8_SMOKE_AUTHORIZED=1")
        print("  M8_SMOKE_CLIENT_ID=<staging/smoke tenant uuid>")
        print("  M8_SMOKE_ENV=staging")
        print("  M8_SMOKE_CONFIRM_ENV=staging")
        print("Plus SUPABASE_URL + SUPABASE_SERVICE_KEY for CRM/Calendar data plane.")
        print("Google OAuth on the smoke tenant is required for Calendar.")
        print("Gmail connector on the smoke tenant is required for Gmail.")
        raise SystemExit(2)

    client_id = os.environ.get("M8_SMOKE_CLIENT_ID", "").strip()
    env_name = os.environ.get("M8_SMOKE_ENV", "").strip().lower()
    confirm = os.environ.get("M8_SMOKE_CONFIRM_ENV", "").strip().lower()
    if not client_id:
        print("M8_SMOKE_CLIENT_ID required when authorized")
        raise SystemExit(2)
    if env_name != "staging" or confirm != "staging":
        print("M8 LIVE SMOKE REFUSED: environment confirmation mismatch")
        print("Set M8_SMOKE_ENV=staging and M8_SMOKE_CONFIRM_ENV=staging")
        print("(Refusing non-staging confirmation to avoid production targeting.)")
        raise SystemExit(2)

    return client_id, {
        "environment": env_name,
        "timestamp": _now(),
        "git_sha": _git_sha(),
        "tenant_test_id": client_id,
        "suites": [],
        "results": [],
    }


def _service_creds_present() -> bool:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
    return bool(url and key)


def _record(evidence: dict, suite: str, step: str, **payload: Any) -> None:
    evidence["results"].append(
        {
            "suite": suite,
            "step": step,
            "at": _now(),
            **payload,
        }
    )
    status = payload.get("result", "?")
    print(f"[{suite}] {step}: {status}")


def _write_artifact(evidence: dict) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ARTIFACT_DIR / f"m8-live-smoke-{stamp}.json"
    # Strip anything that looks secret-ish.
    safe = json.loads(json.dumps(evidence))
    for row in safe.get("results", []):
        for k in list(row.keys()):
            if any(s in k.lower() for s in ("token", "secret", "password", "body", "email")):
                if k not in ("email_fingerprint", "recipient_domain"):
                    row[k] = "[redacted]"
    path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")
    print(f"wrote evidence {path}")
    return path


def run_rag_soak(evidence: dict) -> int:
    """In-process RAG soak — does not flip Railway production RAG_ENABLED."""
    os.environ["RAG_ENABLED"] = "1"
    # Frozen threshold — do not change during rollout.
    from backend.services.business_retrieval import DEFAULT_MIN_SCORE

    if DEFAULT_MIN_SCORE != 1.0:
        _record(
            evidence,
            "rag",
            "threshold_guard",
            result="fail",
            detail=f"DEFAULT_MIN_SCORE drifted to {DEFAULT_MIN_SCORE}",
        )
        return 4

    env = os.environ.copy()
    env["RAG_ENABLED"] = "1"
    env["PYTHONPATH"] = str(ROOT)
    py = ROOT / ".venv312" / "bin" / "python"
    python = str(py) if py.exists() else sys.executable
    holdout = ROOT / "agent-service" / "evals" / "datasets" / "rag" / "rag-eval-holdout-v1.json"
    cmd = [python, str(ROOT / "ml" / "rag" / "evaluate.py"), "--dataset", str(holdout)]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        _record(
            evidence,
            "rag",
            "holdout_soak",
            result="fail",
            detail=proc.stderr[-500:] or proc.stdout[-500:],
        )
        return 4
    # evaluate.py prints a large JSON; parse the last JSON object.
    text = proc.stdout
    start = text.find("{")
    end = text.rfind("}")
    summary: dict[str, Any] = {}
    if start >= 0 and end > start:
        try:
            summary = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            summary = {}
    safety = summary.get("safety") or {}
    gen = summary.get("generation") or {}
    ret = summary.get("retrieval") or {}
    ok = (
        safety.get("cross_tenant_leaks", 1) == 0
        and safety.get("prompt_injection_failures", 1) == 0
        and gen.get("unsupported_claim_rate", 1) == 0
        and gen.get("correct_refusal_rate", 0) == 1.0
        and gen.get("false_refusal_rate", 1) == 0.0
    )
    _record(
        evidence,
        "rag",
        "holdout_soak",
        result="pass" if ok else "fail",
        rag_enabled_process=True,
        railway_flag_unchanged=True,
        default_min_score=1.0,
        recall_at_1=ret.get("recall_at_1"),
        correct_refusal_rate=gen.get("correct_refusal_rate"),
        false_refusal_rate=gen.get("false_refusal_rate"),
        unsupported_claim_rate=gen.get("unsupported_claim_rate"),
        cross_tenant_leaks=safety.get("cross_tenant_leaks"),
        prompt_injection_failures=safety.get("prompt_injection_failures"),
        note=(
            "Process-local RAG_ENABLED=1 soak against independent holdout. "
            "Does not enable Railway production RAG_ENABLED. "
            "Live tenant_kb_chunks may still be empty — enable staging deploy separately."
        ),
    )
    return 0 if ok else 4


def run_calendar_suite(evidence: dict, client_id: str) -> int:
    if not _service_creds_present():
        _record(
            evidence,
            "calendar",
            "credential_gate",
            result="blocked",
            blocker="SUPABASE_URL/SUPABASE_SERVICE_KEY not available in agent environment",
        )
        return 3

    os.environ.setdefault("CALENDAR_ACTIONS_ENABLED", "1")
    from backend.services.google_calendar import get_integration
    from backend.services import os_calendar_crm
    from backend.models.database import get_service_supabase

    if not get_integration(client_id):
        _record(
            evidence,
            "calendar",
            "provider_gate",
            result="blocked",
            blocker="no google_calendar OAuth integration for smoke tenant",
        )
        return 3

    db = get_service_supabase()
    start = datetime.now(timezone.utc) + timedelta(days=3)
    start = start.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    avail = os_calendar_crm.fetch_availability(
        client_id,
        start=start.isoformat(),
        end=(start + timedelta(days=2)).isoformat(),
        duration_minutes=60,
    )
    if avail.get("error"):
        _record(
            evidence,
            "calendar",
            "availability",
            result="fail",
            detail=avail.get("error"),
            invented=False,
        )
        return 4
    _record(
        evidence,
        "calendar",
        "availability",
        result="pass",
        slot_count=len(avail.get("availableSlots") or avail.get("available_slots") or []),
        provider=avail.get("provider") or "google_freebusy",
        invented=False,
    )

    applied, detail, row = os_calendar_crm._upsert_local_event(
        db,
        client_id,
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "title": f"M8 smoke internal {start.date().isoformat()}",
            "sendInvitations": False,
            "attendees": [],
        },
    )
    if not applied or not row:
        _record(
            evidence,
            "calendar",
            "internal_create",
            result="fail",
            detail=detail,
        )
        return 4
    event_id = row.get("id")
    google_id = row.get("google_event_id")
    _record(
        evidence,
        "calendar",
        "internal_create",
        result="pass",
        appointment_id=event_id,
        provider_event_id=google_id,
        verification=detail,
    )

    # Redrive / idempotency: same fingerprint should dedupe.
    applied2, detail2, row2 = os_calendar_crm._upsert_local_event(
        db,
        client_id,
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "title": f"M8 smoke internal {start.date().isoformat()}",
            "sendInvitations": False,
            "attendees": [],
        },
    )
    _record(
        evidence,
        "calendar",
        "redrive_create",
        result="pass" if applied2 and detail2 == "deduplicated" else "fail",
        detail=detail2,
        appointment_id=(row2 or {}).get("id"),
        idempotency="best-effort fingerprint/search-before-create; not Google exactly-once",
    )

    # Cross-tenant negative
    other = str(uuid.uuid4())
    applied_x, detail_x, _ = os_calendar_crm._cancel_local_event(
        db, client_id, {"id": other}
    )
    _record(
        evidence,
        "calendar",
        "cross_tenant_cancel",
        result="pass" if (not applied_x and detail_x == "event_not_found") else "fail",
        detail=detail_x,
        provider_mutation=False,
    )

    applied_c, detail_c, _ = os_calendar_crm._cancel_local_event(
        db, client_id, {"id": event_id, "providerEventId": google_id}
    )
    _record(
        evidence,
        "calendar",
        "cancel",
        result="pass" if applied_c else "fail",
        detail=detail_c,
        appointment_id=event_id,
    )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "calendar" and r.get("result") == "fail"
    ]
    return 4 if fails else 0


def run_crm_suite(evidence: dict, client_id: str) -> int:
    if not _service_creds_present():
        _record(
            evidence,
            "crm",
            "credential_gate",
            result="blocked",
            blocker="SUPABASE_URL/SUPABASE_SERVICE_KEY not available in agent environment",
        )
        return 3

    os.environ.setdefault("CRM_ACTIONS_ENABLED", "1")
    from backend.models.database import get_service_supabase
    from backend.services import os_calendar_crm

    db = get_service_supabase()
    marker = f"m8-smoke-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    email = f"{marker}@example.invalid"

    created = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": f"tmp_{marker}",
                "_op": "create",
                "name": "M8 Smoke Customer",
                "email": email,
                "phone": "555-0100",
                "status": "new",
            }
        ],
    )
    if not created or not created[0].get("applied"):
        _record(evidence, "crm", "create", result="fail", detail=created)
        return 4
    row = created[0].get("row") or {}
    customer_id = row.get("id")
    _record(
        evidence,
        "crm",
        "create",
        result="pass",
        customer_id=customer_id,
        detail=created[0].get("detail"),
    )

    dup = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": f"tmp_{marker}_dup",
                "_op": "create",
                "name": "M8 Smoke Customer Dup",
                "email": email,
                "phone": "555-0100",
            }
        ],
    )
    _record(
        evidence,
        "crm",
        "duplicate_create",
        result="pass"
        if dup and dup[0].get("applied") and dup[0].get("detail") == "deduplicated"
        else "fail",
        detail=(dup[0] if dup else {}).get("detail"),
        customer_id=((dup[0].get("row") or {}) if dup else {}).get("id"),
    )

    updated = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": customer_id,
                "_op": "update",
                "fields": {"phone": "555-9999"},
            }
        ],
    )
    after = (updated[0].get("row") or {}) if updated else {}
    ok_update = (
        updated
        and updated[0].get("applied")
        and after.get("phone") == "555-9999"
        and after.get("email") == email
        and after.get("name") == "M8 Smoke Customer"
    )
    _record(
        evidence,
        "crm",
        "partial_update",
        result="pass" if ok_update else "fail",
        customer_id=customer_id,
        changed_field="phone",
        preserved=["email", "name"],
    )

    stage_ok = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [{"id": customer_id, "_op": "stage", "status": "contacted"}],
    )
    stage_bad = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [{"id": customer_id, "_op": "stage", "status": "not_a_real_stage"}],
    )
    _record(
        evidence,
        "crm",
        "stage_valid",
        result="pass"
        if stage_ok and stage_ok[0].get("applied")
        else "fail",
        detail=(stage_ok[0] if stage_ok else {}).get("detail"),
    )
    _record(
        evidence,
        "crm",
        "stage_invalid",
        result="pass"
        if stage_bad
        and not stage_bad[0].get("applied")
        and stage_bad[0].get("detail") == "invalid_lead_stage"
        else "fail",
        detail=(stage_bad[0] if stage_bad else {}).get("detail"),
        mutation=False,
    )

    cross = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": str(uuid.uuid4()),
                "_op": "update",
                "fields": {"phone": "000"},
            }
        ],
    )
    _record(
        evidence,
        "crm",
        "cross_tenant_update",
        result="pass"
        if cross and not cross[0].get("applied")
        else "fail",
        detail=(cross[0] if cross else {}).get("detail"),
        mutation=False,
    )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "crm" and r.get("result") == "fail"
    ]
    return 4 if fails else 0


def run_gmail_suite(evidence: dict, client_id: str) -> int:
    if not _service_creds_present():
        _record(
            evidence,
            "gmail",
            "credential_gate",
            result="blocked",
            blocker="SUPABASE_URL/SUPABASE_SERVICE_KEY not available in agent environment",
        )
        return 3
    if not _truthy("SEND_EMAIL_ENABLED"):
        _record(
            evidence,
            "gmail",
            "flag_gate",
            result="blocked",
            blocker="SEND_EMAIL_ENABLED not set for this process; refusing live send",
        )
        return 3

    # Live Gmail remains owner-operated; this runner only confirms preconditions.
    from backend.services import gmail_connector

    try:
        connected = bool(gmail_connector.get_integration(client_id))  # type: ignore[attr-defined]
    except Exception:
        connected = False
    if not connected:
        try:
            from backend.services.tenant_scope import tenant_table
            from backend.models.database import get_service_supabase

            db = get_service_supabase()
            rows = (
                tenant_table(db, "tenant_integrations", client_id)
                .select("provider,enabled")
                .eq("provider", "gmail")
                .limit(1)
                .execute()
                .data
                or []
            )
            connected = bool(rows and rows[0].get("enabled"))
        except Exception as exc:
            _record(
                evidence,
                "gmail",
                "provider_gate",
                result="blocked",
                blocker=f"could not verify gmail connector: {type(exc).__name__}",
            )
            return 3

    if not connected:
        _record(
            evidence,
            "gmail",
            "provider_gate",
            result="blocked",
            blocker="no gmail connector for smoke tenant",
        )
        return 3

    _record(
        evidence,
        "gmail",
        "manual_checkpoint",
        result="blocked",
        blocker=(
            "Gmail connector present but automated send still requires owner "
            "approve against a controlled recipient — follow docs/milestone-6-gmail-proof.md"
        ),
        note="Runner will not auto-approve external email without M8_SMOKE_ALLOW_EXTERNAL_SEND=1",
    )
    if not _truthy("M8_SMOKE_ALLOW_EXTERNAL_SEND"):
        return 3
    _record(
        evidence,
        "gmail",
        "external_send",
        result="blocked",
        blocker="automated external send not implemented in this runner; use manual procedure",
    )
    return 3


def main(argv: list[str] | None = None) -> int:
    client_id, evidence = _require_auth()
    suites_raw = os.environ.get("M8_SMOKE_SUITES", "rag,calendar,crm,gmail")
    suites = [s.strip().lower() for s in suites_raw.split(",") if s.strip()]
    evidence["suites"] = suites

    codes: list[int] = []
    for suite in suites:
        if suite == "rag":
            codes.append(run_rag_soak(evidence))
        elif suite == "calendar":
            codes.append(run_calendar_suite(evidence, client_id))
        elif suite == "crm":
            codes.append(run_crm_suite(evidence, client_id))
        elif suite == "gmail":
            codes.append(run_gmail_suite(evidence, client_id))
        else:
            _record(evidence, suite, "unknown_suite", result="fail")
            codes.append(4)

    evidence["exit_codes"] = codes
    evidence["rollback"] = {
        "RAG_ENABLED": "0 / unset",
        "CALENDAR_ACTIONS_ENABLED": "0 / unset",
        "CRM_ACTIONS_ENABLED": "0 / unset",
        "SEND_EMAIL_ENABLED": "0 / unset",
    }
    _write_artifact(evidence)

    # Prefer the most severe code among suites.
    if 4 in codes:
        return 4
    if 3 in codes:
        return 3
    if 2 in codes:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
