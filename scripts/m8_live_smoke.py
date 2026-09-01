#!/usr/bin/env python3
"""Milestone 8 live staging smoke — real data-plane / provider evidence.

This is the real runner. ``m8_controlled_smoke.py`` delegates here.

Hard gates (all required; refuse otherwise — never silently target production):

  M8_SMOKE_AUTHORIZED=1
  M8_SMOKE_CLIENT_ID=<staging/smoke tenant uuid>
  M8_SMOKE_ENV=staging
  M8_SMOKE_CONFIRM_ENV=staging

Optional suites (comma-separated in M8_SMOKE_SUITES, default calendar,crm):

  calendar     — availability, internal create, read-back, cancel, cross-tenant
  crm          — search/update/create/dedupe/stage/cross-tenant via data plane
  gmail        — OS ask → pending_approval → approve/send (send-only proof) → redrive
                 (needs SEND_EMAIL_ENABLED=1 on staging backend **and** agent-service,
                  M8_SMOKE_ALLOW_EXTERNAL_SEND=1, M8_SMOKE_GMAIL_RECIPIENT, owner login)
  rag          — in-process soak with RAG_ENABLED=1, DEFAULT_MIN_SCORE=1.0 frozen
  isolation    — staging RLS: anon denied; service_role scoped reads; CRM isolation
  agent_os_e2e — staging HTTP login → OS thread/message → tool_executions chain

Requires for Calendar/Gmail/CRM Action Executor path:
  SUPABASE_URL + SUPABASE_SERVICE_KEY (legacy service_role JWT or sb_secret_ server key)
  Google OAuth on the smoke tenant for Calendar
  Gmail connector on the smoke tenant for Gmail

Agent OS E2E additionally needs:
  M8_SMOKE_API_BASE + M8_SMOKE_LOGIN_EMAIL/PASSWORD (or M8_SMOKE_OWNER_JWT)
  Staging Railway SUPABASE_SERVICE_KEY = real server credential so /auth/login works

Gmail live send additionally needs:
  M8_SMOKE_ALLOW_EXTERNAL_SEND=1
  M8_SMOKE_GMAIL_RECIPIENT=<controlled inbox>
  optional M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST=comma-separated allowlist
  optional M8_SMOKE_GMAIL_RECIPIENT_VERIFY_URL=<recipient-side delivery checker>

  Send-only OAuth (gmail.send) cannot read the sender mailbox. Proof uses the
  approved execution payload + provider messages.send acknowledgement recorded
  on the row — not messages.list/get on the product connector.

  SEND_EMAIL_ENABLED must be ON on staging Railway backend **and** agent-service
  (proposal gate in TS, execution gate in Python). Local export alone is not enough.

Calendar external-attendee approval additionally needs:
  M8_SMOKE_EXTERNAL_ATTENDEE=<controlled external email>
  owner login/API base (approve path exercises Action Executor)

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
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import m8_staging_credentials as _m8creds


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


def _service_key() -> str:
    return (
        os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("STAGING_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def _service_creds_present() -> bool:
    url = os.environ.get("SUPABASE_URL", "").strip()
    return bool(url and _service_key())


def _jwt_claims(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature (smoke diagnostics only)."""
    return _m8creds.jwt_claims(token)


def _require_service_role_key(evidence: dict, suite: str) -> bool:
    """Fail closed unless SUPABASE_* server credential is trusted (JWT or sb_secret_)."""
    key = _service_key()
    if not key:
        _record(
            evidence,
            suite,
            "service_role_gate",
            result="blocked",
            blocker="SUPABASE_SERVICE_KEY / SUPABASE_SERVICE_ROLE_KEY missing",
        )
        return False

    sb_url = os.environ.get("SUPABASE_URL", "")
    expected_ref = _m8creds.project_ref_from_supabase_url(sb_url) or None
    validation = _m8creds.validate_staging_server_key(key, expected_project_ref=expected_ref)
    if not validation.ok:
        meta = _m8creds.safe_key_metadata(key, validation)
        _record(
            evidence,
            suite,
            "service_role_gate",
            result="blocked",
            blocker=validation.error or "invalid server credential",
            **{k: v for k, v in meta.items() if k != "error"},
        )
        return False

    meta = _m8creds.safe_key_metadata(key, validation)
    _record(
        evidence,
        suite,
        "service_role_gate",
        result="pass",
        **meta,
    )
    os.environ["SUPABASE_SERVICE_KEY"] = key
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = key
    return True


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


def _staging_meta() -> dict[str, Any]:
    """Non-secret staging identifiers only — never tokens/keys."""
    return {
        "api_base": (os.environ.get("M8_SMOKE_API_BASE") or "").strip() or None,
        "railway_project_id": (
            os.environ.get("M8_SMOKE_RAILWAY_PROJECT_ID") or ""
        ).strip()
        or None,
        "railway_environment_id": (
            os.environ.get("M8_SMOKE_RAILWAY_ENVIRONMENT_ID") or ""
        ).strip()
        or None,
        "railway_environment_name": (
            os.environ.get("M8_SMOKE_RAILWAY_ENVIRONMENT_NAME") or "staging"
        ).strip(),
    }


def _probe_staging_api(evidence: dict) -> None:
    base = (os.environ.get("M8_SMOKE_API_BASE") or "").strip().rstrip("/")
    if not base:
        _record(
            evidence,
            "staging",
            "api_base",
            result="blocked",
            blocker="M8_SMOKE_API_BASE unset — no staging deploy URL to probe",
        )
        return
    import urllib.error
    import urllib.request

    url = f"{base}/health"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
            code = getattr(resp, "status", None) or resp.getcode()
            body = resp.read(200).decode("utf-8", errors="replace")
        _record(
            evidence,
            "staging",
            "health_probe",
            result="pass" if int(code) == 200 else "fail",
            http_status=int(code),
            url=url,
            body_preview=body[:120],
        )
    except urllib.error.URLError as exc:
        _record(
            evidence,
            "staging",
            "health_probe",
            result="fail",
            url=url,
            detail=type(exc).__name__,
        )


def _load_smoke_corpus(client_id: str) -> tuple[list, str, int | None]:
    """Return (corpus, source_label, db_chunk_count_or_None)."""
    from backend.services.business_retrieval import CorpusChunk
    from backend.services.tenant_kb_index import (
        documents_to_chunks,
        load_corpus_from_documents,
    )

    if _service_creds_present():
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
        corpus = load_corpus_from_documents(db, client_id)
        chunk_count = None
        try:
            rows = (
                db.table("tenant_kb_chunks")
                .select("id", count="exact")
                .eq("client_id", client_id)
                .eq("status", "active")
                .execute()
            )
            chunk_count = int(getattr(rows, "count", None) or len(rows.data or []))
        except Exception:
            chunk_count = None
        return corpus, "db_documents_compile_path", chunk_count

    # Artifact mirror of indexed chunks (written after compile/index). Not a
    # substitute for Agent OS HTTP, but proves retrieval against real smoke KB.
    art = ARTIFACT_DIR / "m8-smoke-kb-chunks.json"
    if art.exists():
        raw = json.loads(art.read_text(encoding="utf-8"))
        corpus = []
        for row in raw:
            if row.get("client_id") != client_id:
                continue
            if (row.get("status") or "active") != "active":
                continue
            corpus.append(
                CorpusChunk(
                    chunk_id=str(row.get("id") or f"{row.get('document_id')}#{row.get('chunk_index')}"),
                    document_id=str(row.get("document_id") or ""),
                    account_id=client_id,
                    title=row.get("title") or "document",
                    section=row.get("section") or "",
                    content=row.get("content") or "",
                    source_type=row.get("source_type") or "upload",
                    citation_label=row.get("citation_label") or "",
                    status="active",
                )
            )
        return corpus, "artifact_chunks_mirror", len(corpus)

    # Last resort: reconstruct from approved smoke markdown if present in repo.
    md_path = ARTIFACT_DIR / "m8-smoke-kb.md"
    if md_path.exists():
        corpus = documents_to_chunks(
            client_id,
            [
                {
                    "id": "a5dbe7dc-2277-4dd7-95ec-04a152bfff73",
                    "filename": "m8-smoke-kb.md",
                    "content_md": md_path.read_text(encoding="utf-8"),
                    "source": "upload",
                    "status": "active",
                }
            ],
        )
        return corpus, "artifact_markdown_compile_path", len(corpus)

    return [], "unavailable", None


def run_rag_tenant_proof(evidence: dict, client_id: str) -> int:
    """Smoke-tenant retrieval against compiled KB (citations + abstention)."""
    os.environ["RAG_ENABLED"] = "1"
    from backend.services.business_retrieval import (
        DEFAULT_MIN_SCORE,
        attach_rag_knowledge,
        retrieve_business_context,
    )

    if DEFAULT_MIN_SCORE != 1.0:
        _record(
            evidence,
            "rag",
            "threshold_guard",
            result="fail",
            detail=f"DEFAULT_MIN_SCORE drifted to {DEFAULT_MIN_SCORE}",
        )
        return 4

    corpus, source, chunk_count = _load_smoke_corpus(client_id)
    active = chunk_count if chunk_count is not None else len(corpus)
    if active <= 0 or not corpus:
        _record(
            evidence,
            "rag",
            "tenant_kb_chunks",
            result="blocked",
            blocker="active tenant_kb_chunks count is 0 / corpus empty",
            source=source,
            active_chunks=active,
        )
        return 3

    _record(
        evidence,
        "rag",
        "tenant_kb_chunks",
        result="pass",
        source=source,
        active_chunks=active,
        note="Does not flip Railway production RAG_ENABLED",
    )

    other = str(uuid.uuid4())
    cases = [
        ("services", "What services do you offer?", False),
        ("prices", "How much is an exterior wash?", False),
        ("warranty", "What is your ceramic coating warranty?", False),
        ("cancellation", "What is your cancellation policy?", False),
        ("faq", "Do you come to my driveway?", False),
        ("no_answer", "What is your cryptocurrency mining hash rate?", True),
    ]
    fails = 0
    for label, ask, expect_abstain in cases:
        result = retrieve_business_context(
            client_id, ask, corpus, min_score=DEFAULT_MIN_SCORE
        )
        cross = retrieve_business_context(
            other, ask, corpus, min_score=DEFAULT_MIN_SCORE
        )
        ok = (result.abstain is expect_abstain) and (
            cross.abstain and len(cross.evidence) == 0
        )
        if not ok:
            fails += 1
        _record(
            evidence,
            "rag",
            f"tenant_query_{label}",
            result="pass" if ok else "fail",
            abstain=result.abstain,
            reason=result.reason,
            citations=[e.citation_label for e in result.evidence[:3]],
            top_score=result.scores[0] if result.scores else None,
            cross_tenant_evidence=len(cross.evidence),
            expected_abstain=expect_abstain,
        )

    attached_ok = attach_rag_knowledge(
        {"kb": []}, client_id, "How much is an exterior wash?", corpus
    )
    attached_no = attach_rag_knowledge(
        {"kb": []},
        client_id,
        "What is your cryptocurrency mining hash rate?",
        corpus,
    )
    attach_pass = (
        attached_ok.get("ragStatus") == "ok"
        and bool(attached_ok.get("ragEvidence"))
        and attached_no.get("ragStatus") == "abstain"
    )
    _record(
        evidence,
        "rag",
        "attach_rag_contract",
        result="pass" if attach_pass else "fail",
        price_status=attached_ok.get("ragStatus"),
        no_answer_status=attached_no.get("ragStatus"),
        no_answer_reason=attached_no.get("ragAbstainReason"),
        agent_os_http="not_run_without_staging_api",
    )
    return 4 if fails or not attach_pass else 0


def run_rag_soak(evidence: dict, client_id: str | None = None) -> int:
    """Holdout soak + optional smoke-tenant retrieval proof."""
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
            "Does not enable Railway production RAG_ENABLED."
        ),
    )
    if not ok:
        return 4
    if client_id:
        return run_rag_tenant_proof(evidence, client_id)
    return 0


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
    if not _require_service_role_key(evidence, "calendar"):
        return 3

    os.environ.setdefault("CALENDAR_ACTIONS_ENABLED", "1")
    from backend.services.google_calendar import (
        get_integration,
        lookup_calendar_event,
        list_calendar_events_in_window,
    )
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
    cal_marker = f"m8-cal-{uuid.uuid4().hex[:8]}"
    title_internal = f"M8 smoke internal {cal_marker}"
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
            "title": title_internal,
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
    db_ok = _calendar_internal_db_matches(
        row,
        marker=cal_marker,
        title=title_internal,
        start_iso=start.isoformat(),
        end_iso=end.isoformat(),
        google_id=google_id,
    )
    _record(
        evidence,
        "calendar",
        "internal_db_readback",
        result="pass" if db_ok else "fail",
        appointment_id=event_id,
        provider_event_id=google_id,
        marker=cal_marker,
    )
    if not db_ok:
        return 4
    _record(
        evidence,
        "calendar",
        "internal_create",
        result="pass",
        appointment_id=event_id,
        provider_event_id=google_id,
        verification=detail,
        marker=cal_marker,
    )

    if not google_id:
        _record(
            evidence,
            "calendar",
            "provider_readback",
            result="fail",
            blocker="internal create missing google_event_id",
        )
        return 4
    fetched_internal = lookup_calendar_event(client_id, google_id)
    lookup_state = fetched_internal.get("state")
    internal_event = (
        fetched_internal.get("event")
        if lookup_state == "found"
        else None
    )
    readback_ok = lookup_state == "found" and _calendar_internal_provider_readback_matches(
        internal_event,
        google_id=google_id,
        marker=cal_marker,
        title=title_internal,
        expected_summary="Appointment with Customer",
        start_iso=start.isoformat(),
        end_iso=end.isoformat(),
    )
    _record(
        evidence,
        "calendar",
        "provider_readback",
        result="pass" if readback_ok else "fail",
        provider_event_id=google_id,
        lookup_state=lookup_state,
        provider_status=(internal_event or {}).get("status"),
        provider_summary=(internal_event or {}).get("summary"),
        invented=False,
    )
    if lookup_state == "unknown":
        return 4
    if not readback_ok:
        return 4

    # Redrive / idempotency: same fingerprint should dedupe.
    applied2, detail2, row2 = os_calendar_crm._upsert_local_event(
        db,
        client_id,
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "title": title_internal,
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
    if applied_c and google_id:
        cancel_lookup = lookup_calendar_event(client_id, google_id)
        cancel_state = cancel_lookup.get("state")
        if cancel_state == "not_found":
            cancel_readback_ok = True
        elif cancel_state == "found":
            cancel_readback_ok = (
                cancel_lookup.get("event") or {}
            ).get("status", "").lower() in {"cancelled", "canceled"}
        else:
            cancel_readback_ok = False
        _record(
            evidence,
            "calendar",
            "provider_cancel_readback",
            result="pass" if cancel_readback_ok else "fail",
            provider_event_id=google_id,
            lookup_state=cancel_state,
            provider_status=(cancel_lookup.get("event") or {}).get("status"),
            invented=False,
        )
        if not cancel_readback_ok:
            return 4

    # External-attendee path — Action Executor approval boundary (not direct Google).
    if not _require_staging_api(evidence, "calendar"):
        return 3
    ext_email, ext_blocker = _external_attendee_email()
    if not ext_email:
        _record(
            evidence,
            "calendar",
            "external_attendee_gate",
            result="blocked",
            blocker=ext_blocker,
        )
        return 3

    token, login_blocker = _staging_owner_token()
    if not token:
        _record(
            evidence,
            "calendar",
            "external_owner_login",
            result="blocked",
            blocker=login_blocker or "owner token unavailable",
        )
        return 3
    _record(evidence, "calendar", "external_owner_login", result="pass")

    from backend.services import os_tool_executions as ote

    ext_marker = f"m8-ext-{uuid.uuid4().hex[:8]}"
    ext_start = datetime.now(timezone.utc) + timedelta(days=5)
    ext_start = ext_start.replace(minute=0, second=0, microsecond=0)
    ext_end = ext_start + timedelta(hours=1)
    ext_title = f"M8 external smoke {ext_marker}"
    ext_execution_id = str(uuid.uuid4())
    ext_idempotency = f"m8-cal-ext-{ext_marker}"

    proposed = ote.propose_tool_execution(
        db,
        client_id,
        None,
        {
            "id": ext_execution_id,
            "toolId": "create_calendar_event",
            "agentId": "operations",
            "riskLevel": 2,
            "mutating": True,
            "requiresApproval": True,
            "approvalState": "pending",
            "status": "pending_approval",
            "input": {
                "start": ext_start.isoformat(),
                "end": ext_end.isoformat(),
                "title": ext_title,
                "attendees": [
                    {"email": ext_email, "display_name": "M8 External Guest"}
                ],
                "send_invitations": True,
            },
            "policyReason": (
                "calendar event includes external attendees or invitations — "
                "owner approval required"
            ),
            "idempotencyKey": ext_idempotency,
        },
    )
    pending_ok = bool(
        proposed
        and (proposed.get("status") or "") == "pending_approval"
        and (proposed.get("tool_id") or "") == "create_calendar_event"
    )
    _record(
        evidence,
        "calendar",
        "external_pending_approval",
        result="pass" if pending_ok else "fail",
        execution_id=ext_execution_id,
        approval_state=proposed.get("approval_state") if proposed else None,
    )
    if not pending_ok:
        return 4

    ext_window_min = ext_start - timedelta(hours=1)
    ext_window_max = ext_end + timedelta(hours=1)
    pre_state, pre_count = _provider_events_matching_marker(
        client_id, ext_marker, ext_window_min, ext_window_max
    )
    pre_provider_ok = pre_state == "ok" and pre_count == 0
    _record(
        evidence,
        "calendar",
        "external_pre_approve_no_provider_event",
        result="pass" if pre_provider_ok else "fail",
        lookup_state=pre_state,
        provider_event_count=pre_count,
        note="Provider list query by marker/time window — zero before approval",
    )
    if not pre_provider_ok:
        return 4

    code_a, approve_body = _approve_tool_execution(token, ext_execution_id)
    exec_after = (
        (approve_body or {}).get("execution") if isinstance(approve_body, dict) else None
    )
    approve_ok = code_a == 200 and isinstance(exec_after, dict) and (
        exec_after.get("status") in {"succeeded", "verified", "completed"}
    )
    ext_google_id = None
    if isinstance(exec_after, dict):
        result = exec_after.get("result") or {}
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except Exception:
                result = {}
        ext_google_id = result.get("googleEventId") or result.get("google_event_id")
    if not ext_google_id:
        post_appts = _appointments_with_marker(db, client_id, ext_marker)
        if post_appts:
            ext_google_id = post_appts[0].get("google_event_id")

    _record(
        evidence,
        "calendar",
        "external_approve_once",
        result="pass" if approve_ok and ext_google_id else "fail",
        http_status=code_a,
        execution_id=ext_execution_id,
        provider_event_id=ext_google_id,
        already_decided=(approve_body or {}).get("already_decided")
        if isinstance(approve_body, dict)
        else None,
    )
    if not approve_ok or not ext_google_id:
        return 4

    post_state, post_count = _provider_events_matching_marker(
        client_id, ext_marker, ext_window_min, ext_window_max
    )
    post_one_ok = post_state == "ok" and post_count == 1
    _record(
        evidence,
        "calendar",
        "external_post_approve_one_provider_event",
        result="pass" if post_one_ok else "fail",
        lookup_state=post_state,
        provider_event_count=post_count,
    )
    if not post_one_ok:
        return 4

    ext_lookup = lookup_calendar_event(client_id, ext_google_id)
    ext_event = ext_lookup.get("event") if ext_lookup.get("state") == "found" else None
    ext_readback_ok = ext_lookup.get("state") == "found" and _calendar_provider_matches(
        ext_event,
        google_id=ext_google_id,
        title=ext_title,
        start_iso=ext_start.isoformat(),
    )
    attendee_emails = [
        (a.get("email") or "").lower() for a in (ext_event or {}).get("attendees") or []
    ]
    _record(
        evidence,
        "calendar",
        "external_provider_readback",
        result="pass"
        if ext_readback_ok and ext_email.lower() in attendee_emails
        else "fail",
        provider_event_id=ext_google_id,
        lookup_state=ext_lookup.get("state"),
        attendee_count=len(attendee_emails),
        invented=False,
    )
    if not ext_readback_ok or ext_email.lower() not in attendee_emails:
        return 4

    code_redrive, redrive_body = _approve_tool_execution(token, ext_execution_id)
    redrive_exec = (
        (redrive_body or {}).get("execution")
        if isinstance(redrive_body, dict)
        else None
    )
    redrive_state, redrive_count = _provider_events_matching_marker(
        client_id, ext_marker, ext_window_min, ext_window_max
    )
    _record(
        evidence,
        "calendar",
        "external_redrive_no_duplicate",
        result="pass"
        if code_redrive == 200
        and isinstance(redrive_body, dict)
        and redrive_body.get("already_decided") is True
        and redrive_state == "ok"
        and redrive_count == 1
        else "fail",
        http_status=code_redrive,
        lookup_state=redrive_state,
        provider_event_count=redrive_count,
        execution_status=(redrive_exec or {}).get("status"),
    )
    if (
        code_redrive != 200
        or not isinstance(redrive_body, dict)
        or redrive_body.get("already_decided") is not True
        or redrive_state != "ok"
        or redrive_count != 1
    ):
        return 4

    ext_appt = _appointments_with_marker(db, client_id, ext_marker)
    ext_appt_id = ext_appt[0]["id"] if ext_appt else None
    cancel_exec_id = str(uuid.uuid4())
    cancel_proposed = ote.propose_tool_execution(
        db,
        client_id,
        None,
        {
            "id": cancel_exec_id,
            "toolId": "cancel_calendar_event",
            "agentId": "operations",
            "riskLevel": 2,
            "mutating": True,
            "requiresApproval": True,
            "approvalState": "pending",
            "status": "pending_approval",
            "input": {
                "event_id": ext_appt_id,
                "provider_event_id": ext_google_id,
            },
            "policyReason": "level 2 requires approval",
            "idempotencyKey": f"m8-cal-ext-cancel-{ext_marker}",
        },
    )
    if not cancel_proposed or cancel_proposed.get("status") != "pending_approval":
        _record(
            evidence,
            "calendar",
            "external_cancel_proposal",
            result="fail",
            execution_id=cancel_exec_id,
        )
        return 4
    code_cancel, cancel_body = _approve_tool_execution(token, cancel_exec_id)
    cancel_exec = (
        (cancel_body or {}).get("execution") if isinstance(cancel_body, dict) else None
    )
    cancel_ok = code_cancel == 200 and isinstance(cancel_exec, dict) and (
        cancel_exec.get("status") in {"succeeded", "verified", "completed"}
    )
    ext_cancel_lookup = lookup_calendar_event(client_id, ext_google_id)
    ext_cancel_state = ext_cancel_lookup.get("state")
    if ext_cancel_state == "not_found":
        ext_cancel_readback = True
    elif ext_cancel_state == "found":
        ext_cancel_readback = (
            ext_cancel_lookup.get("event") or {}
        ).get("status", "").lower() in {"cancelled", "canceled"}
    else:
        ext_cancel_readback = False
    _record(
        evidence,
        "calendar",
        "external_cancel",
        result="pass" if cancel_ok and ext_cancel_readback else "fail",
        http_status=code_cancel,
        provider_event_id=ext_google_id,
        lookup_state=ext_cancel_state,
        provider_status=(ext_cancel_lookup.get("event") or {}).get("status"),
    )
    if not cancel_ok or not ext_cancel_readback:
        return 4

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
    if not _require_service_role_key(evidence, "crm"):
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

    # Search + ambiguous-name clarification inputs via data-plane read-back.
    from backend.services.tenant_scope import tenant_table

    mike_a = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": f"tmp_{marker}_mike_a",
                "_op": "create",
                "name": "Mike Smoke",
                "email": f"{marker}-mike-a@example.invalid",
                "phone": "555-0001",
                "status": "new",
            }
        ],
    )
    mike_b = os_calendar_crm.apply_crm_mutations(
        db,
        client_id,
        [
            {
                "id": f"tmp_{marker}_mike_b",
                "_op": "create",
                "name": "Mike Smoke",
                "email": f"{marker}-mike-b@example.invalid",
                "phone": "555-0002",
                "status": "new",
            }
        ],
    )
    search_rows = (
        tenant_table(db, "leads", client_id)
        .select("id,name,email,phone,status")
        .eq("name", "Mike Smoke")
        .execute()
        .data
        or []
    )
    _record(
        evidence,
        "crm",
        "search_by_name",
        result="pass" if len(search_rows) >= 2 else "fail",
        match_count=len(search_rows),
        note="tenant-scoped lead search read-back",
    )
    _record(
        evidence,
        "crm",
        "ambiguous_name_clarification",
        result="pass" if len(search_rows) >= 2 else "fail",
        candidates=len(search_rows),
        clarification_required=True,
        created_a=(mike_a[0].get("applied") if mike_a else False),
        created_b=(mike_b[0].get("applied") if mike_b else False),
    )

    # os_tool_executions lifecycle via persist path (create mutation bundle).
    from backend.services import os_tool_executions as ote

    exec_id = str(uuid.uuid4())
    exec_rows = ote.persist_tool_executions(
        db,
        client_id,
        None,
        {
            "toolExecutions": [
                {
                    "id": exec_id,
                    "toolId": "create_customer",
                    "riskLevel": 1,
                    "mutating": True,
                    "requiresApproval": False,
                    "approvalState": "not_required",
                    "status": "succeeded",
                    "input": {
                        "name": f"Audit {marker}",
                        "email": f"{marker}-audit@example.invalid",
                        "phone": "555-7777",
                    },
                    "verificationState": "pending",
                    "idempotencyKey": f"m8-crm-{marker}",
                }
            ],
            "customers": [
                {
                    "id": f"tmp_audit_{marker}",
                    "_op": "create",
                    "name": f"Audit {marker}",
                    "email": f"{marker}-audit@example.invalid",
                    "phone": "555-7777",
                    "status": "new",
                }
            ],
        },
    )
    lifecycle_ok = False
    verification = None
    execution_id = None
    if exec_rows:
        execution_id = exec_rows[0].get("id")
        verification = exec_rows[0].get("verification_state") or exec_rows[0].get(
            "verificationState"
        )
        status = exec_rows[0].get("status")
        lifecycle_ok = bool(execution_id) and status in {
            "succeeded",
            "verified",
            "applied",
            "completed",
        }
        rb = (
            tenant_table(db, "os_tool_executions", client_id)
            .select("id,status,verification_state,tool_id")
            .eq("id", execution_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rb:
            verification = rb[0].get("verification_state") or verification
            lifecycle_ok = lifecycle_ok and rb[0].get("id") == execution_id
    _record(
        evidence,
        "crm",
        "os_tool_executions_lifecycle",
        result="pass" if lifecycle_ok else "fail",
        execution_id=execution_id,
        verification_state=verification,
        persist_count=len(exec_rows or []),
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
    if not _require_service_role_key(evidence, "gmail"):
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
    if not _truthy("M8_SMOKE_ALLOW_EXTERNAL_SEND"):
        _record(
            evidence,
            "gmail",
            "external_send_gate",
            result="blocked",
            blocker="M8_SMOKE_ALLOW_EXTERNAL_SEND=1 required for live Gmail proof",
        )
        return 3
    if not _require_staging_api(evidence, "gmail"):
        return 3

    recipient, recipient_blocker = _gmail_recipient_allowed()
    if not recipient:
        _record(
            evidence,
            "gmail",
            "recipient_gate",
            result="blocked",
            blocker=recipient_blocker,
        )
        return 3

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

    token, login_blocker = _staging_owner_token()
    if not token:
        _record(
            evidence,
            "gmail",
            "owner_login",
            result="blocked",
            blocker=login_blocker or "owner token unavailable",
        )
        return 3
    _record(evidence, "gmail", "owner_login", result="pass")

    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    marker = f"m8-gmail-{uuid.uuid4().hex[:8]}"
    subject, body, ask = _build_gmail_smoke_prompt(recipient, marker)
    if not _gmail_smoke_prompt_is_safe(subject, body, ask):
        _record(
            evidence,
            "gmail",
            "prompt_contract",
            result="fail",
            blocker="gmail smoke prompt contains forbidden destructive-action language",
        )
        return 4

    code_t, thread = _os_http(
        "POST",
        "/api/v1/os/threads",
        token,
        {"title": f"M8 Gmail smoke {marker}"},
    )
    if code_t not in (200, 201) or not isinstance(thread, dict) or not thread.get("id"):
        _record(
            evidence,
            "gmail",
            "create_thread",
            result="fail",
            http_status=code_t,
        )
        return 4
    thread_id = thread["id"]
    _record(evidence, "gmail", "create_thread", result="pass", thread_id=thread_id)

    poll_since = datetime.now(timezone.utc).isoformat()
    code_m, msg_body = _os_http(
        "POST",
        f"/api/v1/os/threads/{thread_id}/messages",
        token,
        {"content": ask},
    )
    if code_m not in (200, 201):
        _record(
            evidence,
            "gmail",
            "owner_ask",
            result="fail",
            http_status=code_m,
            detail=msg_body if not isinstance(msg_body, dict) else None,
        )
        return 4
    _record(evidence, "gmail", "owner_ask", result="pass", http_status=code_m)

    pending = _poll_tool_execution(
        db,
        client_id,
        token,
        tool_id="send_email",
        marker=marker,
        poll_since=poll_since,
        status="pending_approval",
    )
    if not pending:
        _record(
            evidence,
            "gmail",
            "pending_approval",
            result="fail",
            blocker="no send_email pending_approval row after owner ask",
        )
        return 4

    execution_id = pending.get("id")
    agent_id = pending.get("agent_id") or pending.get("agentId")
    sales_ok = (agent_id or "") == "sales"
    _record(
        evidence,
        "gmail",
        "pending_approval",
        result="pass" if sales_ok else "fail",
        execution_id=execution_id,
        agent_id=agent_id,
        approval_state=pending.get("approval_state"),
        note="Sales department required for live send",
    )
    if not sales_ok:
        return 4

    payload_ok = _send_payload_matches(pending, recipient, subject, body, marker)
    not_sent_yet = _send_email_pending_not_sent(pending)
    _record(
        evidence,
        "gmail",
        "pre_approve_not_sent",
        result="pass" if payload_ok and not_sent_yet else "fail",
        execution_id=execution_id,
        payload_matches=payload_ok,
        status=pending.get("status"),
        note=(
            "Send-only OAuth: prove pending_approval + approved payload, "
            "no provider messageId on row (no sender mailbox read)"
        ),
    )
    if not payload_ok or not not_sent_yet:
        return 4

    first_msg_id_before = _provider_message_id_from_execution(pending)

    code_a, approve_body = _approve_tool_execution(token, execution_id)
    exec_after = (
        (approve_body or {}).get("execution") if isinstance(approve_body, dict) else None
    )
    provider_msg_id = _provider_message_id_from_execution(exec_after or {})
    approve_ok = (
        code_a == 200
        and isinstance(exec_after, dict)
        and exec_after.get("status") in {"succeeded", "verified", "completed"}
        and bool(provider_msg_id)
        and _send_payload_matches(exec_after, recipient, subject, body, marker)
    )
    _record(
        evidence,
        "gmail",
        "approve_send_once",
        result="pass" if approve_ok else "fail",
        http_status=code_a,
        execution_id=execution_id,
        execution_status=(exec_after or {}).get("status"),
        provider_message_id=provider_msg_id,
        already_decided=(approve_body or {}).get("already_decided")
        if isinstance(approve_body, dict)
        else None,
        note="Succeeded only when users.messages.send returned a provider message id",
    )
    if not approve_ok:
        return 4

    verify_url = os.environ.get("M8_SMOKE_GMAIL_RECIPIENT_VERIFY_URL", "").strip()
    if verify_url:
        delivery_ok = _optional_recipient_delivery_verify(verify_url, marker, recipient)
        _record(
            evidence,
            "gmail",
            "recipient_side_delivery",
            result="pass" if delivery_ok else "fail",
            note="Independent recipient-side verifier (not product OAuth read)",
        )
        if not delivery_ok:
            return 4
    else:
        _record(
            evidence,
            "gmail",
            "recipient_side_delivery",
            result="skipped",
            note=(
                "No M8_SMOKE_GMAIL_RECIPIENT_VERIFY_URL — send-only scope cannot "
                "read sender mailbox; provider ack on execution row is the proof"
            ),
        )

    code_redrive, redrive_body = _approve_tool_execution(token, execution_id)
    redrive_exec = (
        (redrive_body or {}).get("execution") if isinstance(redrive_body, dict) else None
    )
    redrive_msg_id = _provider_message_id_from_execution(redrive_exec or {})
    redrive_outcome = (redrive_body or {}).get("outcome") if isinstance(redrive_body, dict) else None
    redrive_ok = (
        code_redrive == 200
        and isinstance(redrive_body, dict)
        and redrive_body.get("already_decided") is True
        and redrive_msg_id == provider_msg_id
        and redrive_msg_id != ""
        and not (isinstance(redrive_outcome, dict) and redrive_outcome.get("executed"))
    )
    _record(
        evidence,
        "gmail",
        "redrive_no_duplicate",
        result="pass" if redrive_ok else "fail",
        http_status=code_redrive,
        provider_message_id=redrive_msg_id,
        first_provider_message_id=first_msg_id_before or provider_msg_id,
        outcome_executed=(redrive_outcome or {}).get("executed")
        if isinstance(redrive_outcome, dict)
        else None,
        execution_status=(redrive_exec or {}).get("status")
        if isinstance(redrive_exec, dict)
        else None,
        note="Second approve is idempotent; send must not run again",
    )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "gmail" and r.get("result") == "fail"
    ]
    return 4 if fails else 0


def run_isolation_suite(evidence: dict, client_id: str) -> int:
    """Prove staging RLS posture: anon sees nothing; service_role sees smoke tenant only."""
    import urllib.error
    import urllib.request

    url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    anon = (
        os.environ.get("SUPABASE_KEY", "").strip()
        or os.environ.get("SUPABASE_ANON_KEY", "").strip()
    )
    if not url or not anon:
        _record(
            evidence,
            "isolation",
            "anon_gate",
            result="blocked",
            blocker="SUPABASE_URL / SUPABASE_KEY (anon) required",
        )
        return 3

    def _rest(path: str, key: str) -> tuple[int, Any]:
        req = urllib.request.Request(
            f"{url}/rest/v1/{path}",
            headers=_m8creds.supabase_rest_headers(key),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                code = int(getattr(resp, "status", None) or resp.getcode())
                body = json.loads(resp.read().decode("utf-8", errors="replace") or "null")
                return code, body
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw or "null")
            except Exception:
                body = raw[:200]
            return int(exc.code), body

    code, body = _rest("tenant_kb_chunks?select=id&limit=5", anon)
    anon_empty = code == 200 and isinstance(body, list) and len(body) == 0
    _record(
        evidence,
        "isolation",
        "anon_cannot_read_chunks",
        result="pass" if anon_empty else "fail",
        http_status=code,
        row_count=len(body) if isinstance(body, list) else None,
    )

    code2, body2 = _rest("leads?select=id&limit=5", anon)
    anon_leads_empty = code2 == 200 and isinstance(body2, list) and len(body2) == 0
    _record(
        evidence,
        "isolation",
        "anon_cannot_read_leads",
        result="pass" if anon_leads_empty else "fail",
        http_status=code2,
        row_count=len(body2) if isinstance(body2, list) else None,
    )

    if not _require_service_role_key(evidence, "isolation"):
        return 3

    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    own = (
        db.table("tenant_kb_chunks")
        .select("id", count="exact")
        .eq("client_id", client_id)
        .eq("status", "active")
        .execute()
    )
    own_count = int(getattr(own, "count", None) or len(own.data or []))
    _record(
        evidence,
        "isolation",
        "service_role_reads_smoke_chunks",
        result="pass" if own_count > 0 else "fail",
        active_chunks=own_count,
    )

    other = str(uuid.uuid4())
    foreign = (
        db.table("leads")
        .select("id")
        .eq("client_id", other)
        .limit(5)
        .execute()
        .data
        or []
    )
    _record(
        evidence,
        "isolation",
        "service_role_empty_foreign_leads",
        result="pass" if foreign == [] else "fail",
        foreign_count=len(foreign),
    )

    # In-process CRM: create under a foreign client_id must not appear on smoke tenant.
    os.environ.setdefault("CRM_ACTIONS_ENABLED", "1")
    from backend.services import os_calendar_crm

    foreign_email = f"x-{uuid.uuid4().hex[:8]}@example.invalid"
    refused2 = os_calendar_crm.apply_crm_mutations(
        db,
        other,
        [
            {
                "id": f"tmp_isolation_{uuid.uuid4().hex[:8]}",
                "_op": "create",
                "name": "Should Not Land On Smoke",
                "email": foreign_email,
                "status": "new",
            }
        ],
    )
    smoke_hit = (
        db.table("leads")
        .select("id")
        .eq("client_id", client_id)
        .eq("email", foreign_email)
        .limit(1)
        .execute()
        .data
        or []
    )
    _record(
        evidence,
        "isolation",
        "crm_other_tenant_create_isolated",
        result="pass" if not smoke_hit else "fail",
        other_create_applied=bool(refused2 and refused2[0].get("applied")),
        note="other-tenant create must not appear under smoke client_id",
    )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "isolation" and r.get("result") == "fail"
    ]
    return 4 if fails else 0


def _staging_owner_token() -> tuple[str | None, str | None]:
    """Login to staging API as smoke owner. Returns (token, blocker)."""
    import urllib.error
    import urllib.request

    base = (os.environ.get("M8_SMOKE_API_BASE") or "").strip().rstrip("/")
    email = (
        os.environ.get("M8_SMOKE_LOGIN_EMAIL")
        or os.environ.get("STAGING_SMOKE_TENANT_LOGIN_EMAIL")
        or ""
    ).strip()
    password = (
        os.environ.get("M8_SMOKE_LOGIN_PASSWORD")
        or os.environ.get("STAGING_SMOKE_TENANT_LOGIN_PASSWORD")
        or ""
    ).strip()
    preissued = (os.environ.get("M8_SMOKE_OWNER_JWT") or "").strip()
    if preissued:
        return preissued, None
    if not base:
        return None, "M8_SMOKE_API_BASE unset"
    if not email or not password:
        return None, "M8_SMOKE_LOGIN_EMAIL/PASSWORD unset"
    payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{base}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        return None, f"login_http_{exc.code}"
    except urllib.error.URLError as exc:
        return None, f"login_{type(exc).__name__}"
    token = body.get("token") or body.get("access_token")
    if not token:
        return None, "login_missing_token"
    return str(token), None


def _os_http(
    method: str, path: str, token: str, payload: dict | None = None
) -> tuple[int, Any]:
    import urllib.error
    import urllib.request

    base = (os.environ.get("M8_SMOKE_API_BASE") or "").strip().rstrip("/")
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            code = int(getattr(resp, "status", None) or resp.getcode())
            raw = resp.read().decode("utf-8", errors="replace")
            return code, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw or "null")
        except Exception:
            body = raw[:300]
        return int(exc.code), body


def _require_staging_api(evidence: dict, suite: str) -> bool:
    base = (os.environ.get("M8_SMOKE_API_BASE") or "").strip()
    if base:
        return True
    _record(
        evidence,
        suite,
        "api_base_gate",
        result="blocked",
        blocker="M8_SMOKE_API_BASE unset — owner HTTP path required",
    )
    return False


def _gmail_recipient_allowed() -> tuple[str | None, str | None]:
    """Return (recipient, blocker). Recipient must pass optional allowlist."""
    recipient = os.environ.get("M8_SMOKE_GMAIL_RECIPIENT", "").strip()
    if not recipient:
        return None, "M8_SMOKE_GMAIL_RECIPIENT unset"
    allowlist_raw = os.environ.get("M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST", "").strip()
    if allowlist_raw:
        allowed = {
            part.strip().lower()
            for part in allowlist_raw.split(",")
            if part.strip()
        }
        if recipient.lower() not in allowed:
            return None, "recipient not in M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST"
    return recipient, None


def _external_attendee_email() -> tuple[str | None, str | None]:
    email = os.environ.get("M8_SMOKE_EXTERNAL_ATTENDEE", "").strip()
    if not email:
        return None, "M8_SMOKE_EXTERNAL_ATTENDEE unset"
    return email, None


def _execution_input_contains(row: dict, marker: str) -> bool:
    blob = json.dumps(row.get("input") or row.get("result") or {}, default=str)
    return marker in blob


def _approve_tool_execution(token: str, execution_id: str) -> tuple[int, Any]:
    return _os_http(
        "POST", f"/api/v1/os/tool-executions/{execution_id}/approve", token
    )


def _poll_tool_execution(
    db: Any,
    client_id: str,
    token: str | None,
    *,
    tool_id: str,
    marker: str,
    poll_since: str,
    status: str | None = "pending_approval",
    attempts: int = 24,
    sleep_s: float = 5.0,
) -> dict | None:
    """Find a tool execution row scoped to this smoke run."""
    import time

    since = poll_since[:19]
    for _ in range(attempts):
        if token:
            path = "/api/v1/os/tool-executions?limit=50"
            if status:
                path += f"&status={status}"
            code, execs = _os_http("GET", path, token)
            items = (execs or {}).get("items") if isinstance(execs, dict) else None
            if code == 200 and isinstance(items, list):
                for row in items:
                    created = (row.get("created_at") or row.get("createdAt") or "")[:19]
                    if created and created < since:
                        continue
                    tid = row.get("tool_id") or row.get("toolId") or ""
                    if tid != tool_id:
                        continue
                    if not _execution_input_contains(row, marker):
                        continue
                    if status and (row.get("status") or "") != status:
                        continue
                    return row
        if db is not None:
            q = (
                db.table("os_tool_executions")
                .select("*")
                .eq("client_id", client_id)
                .eq("tool_id", tool_id)
                .gte("created_at", since)
                .order("created_at", desc=True)
                .limit(30)
            )
            if status:
                q = q.eq("status", status)
            rows = q.execute().data or []
            for row in rows:
                if _execution_input_contains(row, marker):
                    return row
        time.sleep(sleep_s)
    return None


def _parse_execution_field(row: dict | None, field: str) -> dict:
    if not isinstance(row, dict):
        return {}
    raw = row.get(field) or {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return raw if isinstance(raw, dict) else {}


def _send_email_pending_not_sent(row: dict | None) -> bool:
    """True when row is parked and has no provider send acknowledgement yet."""
    if not isinstance(row, dict):
        return False
    if (row.get("status") or "") != "pending_approval":
        return False
    result = _parse_execution_field(row, "result")
    return not _provider_message_id_from_execution({"result": result})


def _send_payload_matches(
    row: dict | None,
    recipient: str,
    subject: str,
    body: str,
    marker: str,
) -> bool:
    inp = _parse_execution_field(row, "input")
    to = (inp.get("to") or "").strip().lower()
    subj = inp.get("subject") or ""
    bod = inp.get("body") or ""
    return (
        to == recipient.strip().lower()
        and marker in subj
        and marker in bod
        and subject in subj
        and body in bod
    )


def _provider_message_id_from_execution(row: dict | None) -> str | None:
    if not isinstance(row, dict):
        return None
    result = _parse_execution_field(row, "result")
    mid = result.get("messageId") or result.get("message_id")
    if mid is None and "result" not in row:
        mid = row.get("messageId") or row.get("message_id")
    text = str(mid).strip() if mid else ""
    return text or None


def _provider_events_matching_marker(
    client_id: str,
    marker: str,
    time_min: datetime,
    time_max: datetime,
) -> tuple[str, int]:
    """Return (lookup_state, count). count is -1 when lookup_state != ok."""
    from backend.services.google_calendar import list_calendar_events_in_window

    listed = list_calendar_events_in_window(
        client_id, time_min, time_max, summary_contains=marker
    )
    if listed.get("state") != "ok":
        return "unknown", -1
    events = listed.get("events") or []
    matched = [ev for ev in events if marker in (ev.get("summary") or "")]
    return "ok", len(matched)


def _cancel_lookup_proves_deleted(lookup: dict) -> bool:
    state = lookup.get("state")
    if state == "not_found":
        return True
    if state == "found":
        return (lookup.get("event") or {}).get("status", "").lower() in {
            "cancelled",
            "canceled",
        }
    return False


def _optional_recipient_delivery_verify(
    verify_url: str, marker: str, recipient: str
) -> bool:
    """POST to a controlled recipient-side verifier (not product Gmail OAuth)."""
    import urllib.error
    import urllib.request

    payload = json.dumps({"marker": marker, "recipient": recipient}).encode()
    req = urllib.request.Request(
        verify_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return False
    return bool(body.get("found") or body.get("delivered"))


def _appointments_with_marker(db: Any, client_id: str, marker: str) -> list[dict]:
    from backend.services.tenant_scope import tenant_table

    return (
        tenant_table(db, "appointments", client_id)
        .select("id,google_event_id,status,notes,start_time,end_time")
        .ilike("notes", f"%{marker}%")
        .execute()
        .data
        or []
    )


_GMAIL_SMOKE_FORBIDDEN_WORDS = ("delete", "remove", "erase", "destroy", "cancel")


def _build_gmail_smoke_prompt(recipient: str, marker: str) -> tuple[str, str, str]:
    """Build Gmail live-smoke subject/body/owner-ask without destructive-action language."""
    subject = f"M8 smoke {marker}"
    body = (
        f"Milestone 8 controlled test message {marker}. "
        "No follow-up action is required."
    )
    ask = (
        f"Using Sales email tools only, send an email to {recipient} with subject "
        f"'{subject}' and body '{body}'. Send exactly this email and perform no other "
        "action. This email must require owner approval before sending."
    )
    return subject, body, ask


def _gmail_smoke_prompt_is_safe(subject: str, body: str, ask: str) -> bool:
    combined = f"{subject} {body} {ask}".lower()
    return not any(word in combined for word in _GMAIL_SMOKE_FORBIDDEN_WORDS)


def _gmail_smoke_ask_targets_send_email(ask: str) -> bool:
    lower = ask.lower()
    return (
        "sales email tools only" in lower
        and "send an email" in lower
        and "owner approval" in lower
    )


def _gmail_smoke_not_destructive_crm_intent(subject: str, body: str, ask: str) -> bool:
    return _gmail_smoke_prompt_is_safe(subject, body, ask) and _gmail_smoke_ask_targets_send_email(
        ask
    )


def _calendar_internal_db_matches(
    row: dict | None,
    *,
    marker: str,
    title: str,
    start_iso: str,
    end_iso: str,
    google_id: str | None,
) -> bool:
    if not row or not row.get("id"):
        return False
    if not google_id or row.get("google_event_id") != google_id:
        return False
    notes = row.get("notes") or ""
    if marker not in notes and title not in notes:
        return False
    row_start = (row.get("start_time") or "")[:16]
    row_end = (row.get("end_time") or "")[:16]
    if start_iso[:16] not in row_start:
        return False
    if end_iso[:16] not in row_end:
        return False
    return True


def _calendar_internal_provider_readback_matches(
    fetched: dict | None,
    *,
    google_id: str,
    marker: str,
    title: str,
    expected_summary: str,
    start_iso: str,
    end_iso: str,
) -> bool:
    if not fetched or fetched.get("id") != google_id:
        return False
    summary = fetched.get("summary") or ""
    if expected_summary not in summary:
        return False
    description = fetched.get("description") or ""
    if marker not in description and title not in description:
        return False
    provider_start = (fetched.get("start") or "")[:16]
    provider_end = (fetched.get("end") or "")[:16]
    if start_iso[:16] not in provider_start:
        return False
    if end_iso[:16] not in provider_end:
        return False
    return True


def _calendar_provider_matches(
    fetched: dict | None,
    *,
    google_id: str,
    title: str,
    start_iso: str,
) -> bool:
    if not fetched or fetched.get("id") != google_id:
        return False
    if title and title not in (fetched.get("summary") or ""):
        return False
    provider_start = (fetched.get("start") or "")[:16]
    return start_iso[:16] in provider_start


def _extract_pending_proposal(msg_body: dict, marker: str) -> dict | None:
    """Return agent_run when the turn parked a draft/proposal instead of a tool row."""
    runs = msg_body.get("agent_runs") if isinstance(msg_body, dict) else None
    if not isinstance(runs, list) or not runs:
        return None
    run = runs[0]
    if not isinstance(run, dict):
        return None
    status = (run.get("deliverable_status") or "").lower()
    if status not in ("pending_approval", "pending"):
        return None
    deliverable = run.get("deliverable") or {}
    blob = json.dumps(deliverable, default=str)
    if marker not in blob:
        return None
    return run


def _poll_e2e_tool_execution(
    db, client_id: str, token: str, marker: str, poll_since: str
) -> tuple[dict | None, bool]:
    """Find a marker-scoped CRM tool execution created during this e2e run."""
    import time

    for _ in range(12):
        time.sleep(5)
        code_e, execs = _os_http("GET", "/api/v1/os/tool-executions?limit=50", token)
        items = (execs or {}).get("items") if isinstance(execs, dict) else None
        if code_e == 200 and isinstance(items, list):
            for row in items:
                if _e2e_exec_matches(row, marker, poll_since):
                    return row, True
        if _service_creds_present() and _m8creds.is_trusted_server_key(_service_key()):
            rows = (
                db.table("os_tool_executions")
                .select("id,tool_id,status,result,input,created_at")
                .eq("client_id", client_id)
                .gte("created_at", poll_since[:19])
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data
                or []
            )
            for row in rows:
                if _e2e_exec_matches(row, marker, poll_since):
                    return row, True
    return None, False


def _e2e_exec_matches(row: dict, marker: str, since_iso: str) -> bool:
    """True when a tool-execution row belongs to this e2e run (not stale CRM audit)."""
    created = (row.get("created_at") or row.get("createdAt") or "")[:19]
    if created and created < since_iso[:19]:
        return False
    tool = (row.get("toolId") or row.get("tool_id") or "").lower()
    if not any(k in tool for k in ("crm", "lead", "customer")):
        return False
    blob = json.dumps(row.get("input") or row.get("result") or {}, default=str)
    return marker in blob


def _lead_id_from_tool_execution(row: dict, marker: str) -> str | None:
    """Extract a leads.id from a tool-execution row when the orchestrator used a
    different email pattern than the smoke prompt assumed."""
    result = row.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            result = {}
    if not isinstance(result, dict):
        result = {}

    for key in ("lead_id", "leadId"):
        if result.get(key):
            return str(result[key])

    for container_key in ("response_payload", "responsePayload", "row"):
        nested = result.get(container_key)
        if isinstance(nested, dict) and nested.get("id"):
            return str(nested["id"])
        if isinstance(nested, dict) and nested.get("lead_id"):
            return str(nested["lead_id"])

    inp = row.get("input") or {}
    if isinstance(inp, str):
        try:
            inp = json.loads(inp)
        except Exception:
            inp = {}
    customers = (inp.get("customers") if isinstance(inp, dict) else None) or []
    for cust in customers:
        if not isinstance(cust, dict):
            continue
        blob = f"{cust.get('name', '')} {cust.get('email', '')}"
        if marker in blob:
            cid = cust.get("id") or cust.get("customerId")
            if cid:
                return str(cid)
    return None


def _verify_lead_in_db(db, client_id: str, marker: str, lead_id: str | None) -> list[dict]:
    """Resolve the lead row created by agent_os_e2e — prefer execution id."""
    if lead_id:
        rows = (
            db.table("leads")
            .select("id,email,name,status")
            .eq("client_id", client_id)
            .eq("id", lead_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return rows
    rows = (
        db.table("leads")
        .select("id,email,name,status")
        .eq("client_id", client_id)
        .ilike("name", f"%{marker}%")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if rows:
        return rows
    return (
        db.table("leads")
        .select("id,email,name,status")
        .eq("client_id", client_id)
        .eq("email", f"{marker}@example.invalid")
        .limit(1)
        .execute()
        .data
        or []
    )


def run_agent_os_e2e_suite(evidence: dict, client_id: str) -> int:
    """HTTP Agent OS smoke: connectivity vs action execution.

    Connectivity (must pass before action checks):
      login → thread → message → engine_connectivity (FastAPI + agent-service)

    Action E2E (strict — engine_live does NOT substitute):
      action_tool_execution → matching os_tool_executions row for this marker
      db_lead_verification → persisted lead row when mutation expected

    When the turn legitimately parks a draft/proposal (marker in deliverable),
    draft_proposal_artifact is asserted instead of treating absence as pass.
    """
    token, blocker = _staging_owner_token()
    if not token:
        _record(
            evidence,
            "agent_os_e2e",
            "login",
            result="blocked",
            blocker=blocker or "owner token unavailable",
        )
        return 3

    _record(evidence, "agent_os_e2e", "login", result="pass")

    code, thread = _os_http(
        "POST",
        "/api/v1/os/threads",
        token,
        {"title": f"M8 E2E {datetime.now(timezone.utc).strftime('%H%M%S')}"},
    )
    if code not in (200, 201) or not isinstance(thread, dict) or not thread.get("id"):
        _record(
            evidence,
            "agent_os_e2e",
            "create_thread",
            result="fail",
            http_status=code,
            detail=thread if not isinstance(thread, dict) else {k: thread.get(k) for k in ("id", "detail", "error")},
        )
        return 4
    thread_id = thread["id"]
    _record(evidence, "agent_os_e2e", "create_thread", result="pass", thread_id=thread_id)

    marker = f"m8-e2e-{uuid.uuid4().hex[:8]}"
    prompt = (
        f"Using CRM tools only, create a lead named 'M8 E2E {marker}' with email "
        f"{marker}@example.invalid and status new. Do not email anyone."
    )
    poll_since = datetime.now(timezone.utc).isoformat()
    code_m, msg_body = _os_http(
        "POST",
        f"/api/v1/os/threads/{thread_id}/messages",
        token,
        {"content": prompt},
    )
    if code_m not in (200, 201):
        _record(
            evidence,
            "agent_os_e2e",
            "post_message_orchestrate",
            result="fail",
            http_status=code_m,
            detail=msg_body,
        )
        return 4
    _record(
        evidence,
        "agent_os_e2e",
        "post_message_orchestrate",
        result="pass",
        http_status=code_m,
        note="message accepted by FastAPI OS route (orchestrator invoked)",
    )

    assistant_preview = ""
    engine_live = False
    action_kind = None
    if isinstance(msg_body, dict):
        am = msg_body.get("assistant_message") or {}
        assistant_preview = (am.get("content") or "")[:240]
        action_kind = msg_body.get("action")
        engine_live = "agent engine is temporarily unavailable" not in assistant_preview.lower()
    if not engine_live:
        _record(
            evidence,
            "agent_os_e2e",
            "engine_connectivity",
            result="blocked",
            blocker="agent-service unreachable or misconfigured on staging",
            assistant_preview=assistant_preview,
        )
        _record(
            evidence,
            "agent_os_e2e",
            "action_tool_execution",
            result="blocked",
            blocker="engine offline — no action rows expected",
        )
        _record(
            evidence,
            "agent_os_e2e",
            "db_lead_verification",
            result="blocked",
            blocker="engine offline",
        )
        return 3

    _record(
        evidence,
        "agent_os_e2e",
        "engine_connectivity",
        result="pass",
        action=action_kind,
        note="FastAPI + agent-service orchestration reachable (connectivity only)",
    )

    db = None
    if _service_creds_present() and _m8creds.is_trusted_server_key(_service_key()):
        from backend.models.database import get_service_supabase

        db = get_service_supabase()

    matched_exec: dict | None = None
    found_exec = False
    if db is not None:
        matched_exec, found_exec = _poll_e2e_tool_execution(
            db, client_id, token, marker, poll_since
        )
    else:
        import time

        for _ in range(12):
            time.sleep(5)
            code_e, execs = _os_http("GET", "/api/v1/os/tool-executions?limit=50", token)
            items = (execs or {}).get("items") if isinstance(execs, dict) else None
            if code_e == 200 and isinstance(items, list):
                for row in items:
                    if _e2e_exec_matches(row, marker, poll_since):
                        matched_exec = row
                        found_exec = True
                        break
            if found_exec:
                break

    captured_lead_id = (
        _lead_id_from_tool_execution(matched_exec, marker) if matched_exec else None
    )
    proposal_run = _extract_pending_proposal(msg_body or {}, marker)
    expect_proposal = os.environ.get("M8_E2E_EXPECT_PROPOSAL", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    if found_exec:
        _record(
            evidence,
            "agent_os_e2e",
            "action_tool_execution",
            result="pass",
            execution_id=matched_exec.get("id") if matched_exec else None,
            tool_id=matched_exec.get("tool_id") or matched_exec.get("toolId") if matched_exec else None,
            verification_state=(matched_exec or {}).get("status"),
            note="Marker-scoped os_tool_executions row created for this request",
        )
        _record(
            evidence,
            "agent_os_e2e",
            "draft_proposal_artifact",
            result="skipped",
            note="Mutation path — draft assertion not applicable",
        )
        if db is not None:
            leads = _verify_lead_in_db(db, client_id, marker, captured_lead_id)
            _record(
                evidence,
                "agent_os_e2e",
                "db_lead_verification",
                result="pass" if leads else "fail",
                lead_id=(leads[0]["id"] if leads else captured_lead_id),
                verified_by="execution_id_or_name_marker",
            )
        else:
            _record(
                evidence,
                "agent_os_e2e",
                "db_lead_verification",
                result="blocked",
                blocker="service_role required to verify lead persistence",
            )
    elif expect_proposal and proposal_run:
        _record(
            evidence,
            "agent_os_e2e",
            "action_tool_execution",
            result="skipped",
            note="Proposal-only mode — no os_tool_executions row expected",
        )
        _record(
            evidence,
            "agent_os_e2e",
            "draft_proposal_artifact",
            result="pass",
            agent_run_id=proposal_run.get("id"),
            deliverable_status=proposal_run.get("deliverable_status"),
            note="Draft/proposal references e2e marker and is pending approval",
        )
        _record(
            evidence,
            "agent_os_e2e",
            "db_lead_verification",
            result="skipped",
            note="Proposal-only mode — no CRM mutation expected yet",
        )
    else:
        generic_proposal = None
        if isinstance(msg_body, dict):
            runs = msg_body.get("agent_runs") or []
            if runs and isinstance(runs[0], dict):
                status = (runs[0].get("deliverable_status") or "").lower()
                if status in ("pending_approval", "pending") and runs[0].get("deliverable"):
                    generic_proposal = runs[0]
        _record(
            evidence,
            "agent_os_e2e",
            "action_tool_execution",
            result="fail",
            found_crm_tool_execution=False,
            note=(
                "No marker-scoped os_tool_executions row — engine_live does not "
                "substitute for action execution"
            ),
        )
        if generic_proposal or proposal_run:
            _record(
                evidence,
                "agent_os_e2e",
                "draft_proposal_artifact",
                result="fail",
                agent_run_id=(proposal_run or generic_proposal or {}).get("id"),
                deliverable_status=(proposal_run or generic_proposal or {}).get(
                    "deliverable_status"
                ),
                note=(
                    "Draft/proposal without matching tool execution — mutation prompt "
                    "requires os_tool_executions row (set M8_E2E_EXPECT_PROPOSAL=1 "
                    "only for proposal-only scenarios)"
                ),
            )
        else:
            _record(
                evidence,
                "agent_os_e2e",
                "draft_proposal_artifact",
                result="fail",
                note="No tool execution and no draft/proposal artifact for this turn",
            )
        _record(
            evidence,
            "agent_os_e2e",
            "db_lead_verification",
            result="fail",
            lead_id=None,
            verified_by="execution_id_or_name_marker",
            note="No persisted lead for this e2e marker",
        )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "agent_os_e2e"
        and r.get("result") == "fail"
    ]
    blocked = [
        r
        for r in evidence["results"]
        if r.get("suite") == "agent_os_e2e"
        and r.get("result") == "blocked"
    ]
    if blocked:
        return 3
    return 4 if fails else 0


def main(argv: list[str] | None = None) -> int:
    client_id, evidence = _require_auth()
    suites_raw = os.environ.get("M8_SMOKE_SUITES", "rag,calendar,crm,gmail")
    suites = [s.strip().lower() for s in suites_raw.split(",") if s.strip()]
    evidence["suites"] = suites
    evidence["staging"] = _staging_meta()
    evidence["feature_flags_process"] = {
        "RAG_ENABLED": os.environ.get("RAG_ENABLED", "0"),
        "CALENDAR_ACTIONS_ENABLED": os.environ.get("CALENDAR_ACTIONS_ENABLED", "0"),
        "CRM_ACTIONS_ENABLED": os.environ.get("CRM_ACTIONS_ENABLED", "0"),
        "SEND_EMAIL_ENABLED": os.environ.get("SEND_EMAIL_ENABLED", "0"),
        "DEFAULT_MIN_SCORE": 1.0,
        "note": "Process-local only unless staging Railway vars are set by owner",
    }
    _probe_staging_api(evidence)

    codes: list[int] = []
    for suite in suites:
        if suite == "rag":
            codes.append(run_rag_soak(evidence, client_id))
        elif suite == "calendar":
            codes.append(run_calendar_suite(evidence, client_id))
        elif suite == "crm":
            codes.append(run_crm_suite(evidence, client_id))
        elif suite == "gmail":
            codes.append(run_gmail_suite(evidence, client_id))
        elif suite in {"isolation", "rls"}:
            codes.append(run_isolation_suite(evidence, client_id))
        elif suite in {"agent_os_e2e", "e2e", "agentos"}:
            codes.append(run_agent_os_e2e_suite(evidence, client_id))
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
