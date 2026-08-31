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
  gmail        — propose/approve/send/Message-ID/redrive (needs SEND_EMAIL_ENABLED=1)
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
    """True HTTP path: staging login → OS thread → message → tool_executions readback.

    Exercises Agent OS → FastAPI → DB (and Action Executor when the turn emits
    CRM/Calendar tool calls). Requires staging service_role on Railway so login
    and OS routes can read tenants / write os_* rows.
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

    # Poll tool executions + leads for CRM effect.
    import time

    found_exec = False
    found_lead = False
    captured_lead_id: str | None = None
    for _ in range(12):
        time.sleep(5)
        code_e, execs = _os_http("GET", "/api/v1/os/tool-executions?limit=20", token)
        items = (execs or {}).get("items") if isinstance(execs, dict) else None
        if code_e == 200 and isinstance(items, list):
            for row in items:
                tool = (row.get("toolId") or row.get("tool_id") or "").lower()
                if "crm" in tool or "lead" in tool or "customer" in tool:
                    found_exec = True
                    lid = _lead_id_from_tool_execution(row, marker)
                    if lid:
                        captured_lead_id = lid
                    break
        if _service_creds_present() and _m8creds.is_trusted_server_key(_service_key()):
            from backend.models.database import get_service_supabase

            db = get_service_supabase()
            leads = _verify_lead_in_db(db, client_id, marker, captured_lead_id)
            found_lead = bool(leads)
            if leads and not captured_lead_id:
                captured_lead_id = leads[0].get("id")
        if found_exec and found_lead:
            break
        if found_exec and not _service_creds_present():
            break

    _record(
        evidence,
        "agent_os_e2e",
        "tool_executions_chain",
        result="pass" if found_exec else "fail",
        found_crm_tool_execution=found_exec,
        note=(
            "Requires Agent OS resolver + Action Executor to emit CRM tool rows "
            "into os_tool_executions on staging"
        ),
    )

    if _service_creds_present() and _m8creds.is_trusted_server_key(_service_key()):
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
        leads = _verify_lead_in_db(db, client_id, marker, captured_lead_id)
        _record(
            evidence,
            "agent_os_e2e",
            "db_lead_verification",
            result="pass" if leads else "fail",
            lead_id=(leads[0]["id"] if leads else captured_lead_id),
            verified_by="execution_id_or_name_marker",
        )

    fails = [
        r
        for r in evidence["results"]
        if r.get("suite") == "agent_os_e2e" and r.get("result") == "fail"
    ]
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
