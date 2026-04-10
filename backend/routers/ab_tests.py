"""A/B Test CRUD endpoints for marketing campaign experimentation."""

import hashlib
import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.models.database import get_service_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ab-tests", tags=["ab-tests"])

VALID_TEST_TYPES = {"subject_line", "send_time", "body_content", "campaign_variant"}
VALID_STATUSES = {"draft", "running", "completed", "paused"}
VALID_OUTCOMES = {"sent", "delivered", "opened", "clicked"}


class ABTestVariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    subject: str | None = Field(None, max_length=200)
    body: str | None = Field(None, max_length=50000)
    send_time_override: str | None = Field(None, description="HH:MM format")
    allocation_percent: int = Field(50, ge=0, le=100)


class ABTestVariantUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    subject: str | None = Field(None, max_length=200)
    body: str | None = Field(None, max_length=50000)
    send_time_override: str | None = None
    allocation_percent: int | None = Field(None, ge=0, le=100)


class ABTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    test_type: str = Field(
        ..., description="subject_line, send_time, body_content, campaign_variant"
    )
    variants: list[ABTestVariantCreate] = Field(..., min_length=2, max_length=4)


class ABTestUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None


class WinnerSelection(BaseModel):
    variant_id: str


def _assign_lead_to_variant(lead_id: str, test_id: str, allocation: list[dict]) -> str:
    """Assign a lead to a variant based on hash of lead_id + test_id for reproducibility."""
    hash_input = f"{lead_id}:{test_id}"
    hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    total = sum(a["allocation_percent"] for a in allocation)
    normalized = (hash_val % total) + 1
    cumulative = 0
    for variant in allocation:
        cumulative += variant["allocation_percent"]
        if normalized <= cumulative:
            return variant["id"]
    return allocation[0]["id"]


@router.get("/{tenant_id}")
async def list_ab_tests(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all A/B tests for a tenant."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        result = (
            db.table("ab_tests")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        items = result.data or []

        count_result = (
            db.table("ab_tests")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        total = count_result.count if count_result.count is not None else len(items)

        return {"ab_tests": items, "total": total}
    except Exception:
        logger.exception("Failed to list A/B tests for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list A/B tests")


@router.post("/{tenant_id}")
async def create_ab_test(
    tenant_id: str,
    req: ABTestCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new A/B test with variants."""
    verify_tenant(claims, tenant_id)

    if req.test_type not in VALID_TEST_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid test_type. Must be one of: {', '.join(sorted(VALID_TEST_TYPES))}",
        )

    if not (2 <= len(req.variants) <= 4):
        raise HTTPException(status_code=400, detail="Must have 2-4 variants")

    total_allocation = sum(v.allocation_percent for v in req.variants)
    if total_allocation != 100:
        raise HTTPException(
            status_code=400,
            detail=f"Variant allocation percentages must sum to 100, got {total_allocation}",
        )

    try:
        db = get_service_supabase()

        test_payload = {
            "tenant_id": tenant_id,
            "name": req.name,
            "description": req.description,
            "test_type": req.test_type,
            "status": "draft",
        }
        test_result = db.table("ab_tests").insert(test_payload).execute()
        if not test_result.data:
            raise HTTPException(status_code=500, detail="Failed to create A/B test")
        test = test_result.data[0]
        test_id = test["id"]

        variants_payload = []
        for v in req.variants:
            variants_payload.append(
                {
                    "ab_test_id": test_id,
                    "name": v.name,
                    "subject": v.subject,
                    "body": v.body,
                    "send_time_override": v.send_time_override,
                    "allocation_percent": v.allocation_percent,
                }
            )

        variants_result = (
            db.table("ab_test_variants").insert(variants_payload).execute()
        )
        test["variants"] = variants_result.data or []

        return test
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create A/B test for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create A/B test")


@router.get("/{tenant_id}/{test_id}")
async def get_ab_test(
    tenant_id: str,
    test_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single A/B test with its variants."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        test_result = (
            db.table("ab_tests")
            .select("*")
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not test_result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")
        test = test_result.data[0]

        variants_result = (
            db.table("ab_test_variants")
            .select("*")
            .eq("ab_test_id", test_id)
            .order("created_at")
            .execute()
        )
        test["variants"] = variants_result.data or []

        return test
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to get A/B test")


@router.put("/{tenant_id}/{test_id}")
async def update_ab_test(
    tenant_id: str,
    test_id: str,
    req: ABTestUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update an A/B test."""
    verify_tenant(claims, tenant_id)

    updates = {}
    for k, v in req.model_dump().items():
        if v is not None:
            updates[k] = v

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        db = get_service_supabase()
        result = (
            db.table("ab_tests")
            .update(updates)
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to update A/B test")


@router.delete("/{tenant_id}/{test_id}", status_code=204)
async def delete_ab_test(
    tenant_id: str,
    test_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete an A/B test and all its variants."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()
        result = (
            db.table("ab_tests")
            .delete()
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to delete A/B test")


@router.post("/{tenant_id}/{test_id}/start")
async def start_ab_test(
    tenant_id: str,
    test_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Start an A/B test — changes status to running and records started_at."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        test_result = (
            db.table("ab_tests")
            .select("*")
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not test_result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")

        test = test_result.data[0]
        if test["status"] not in ("draft", "paused"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start test in '{test['status']}' status",
            )

        now = datetime.now(timezone.utc).isoformat()
        result = (
            db.table("ab_tests")
            .update({"status": "running", "started_at": now})
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to start A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to start A/B test")


@router.post("/{tenant_id}/{test_id}/pause")
async def pause_ab_test(
    tenant_id: str,
    test_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Pause a running A/B test."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        test_result = (
            db.table("ab_tests")
            .select("*")
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not test_result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")

        test = test_result.data[0]
        if test["status"] != "running":
            raise HTTPException(status_code=400, detail="Can only pause a running test")

        result = (
            db.table("ab_tests")
            .update({"status": "paused"})
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to pause A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to pause A/B test")


@router.post("/{tenant_id}/{test_id}/complete")
async def complete_ab_test(
    tenant_id: str,
    test_id: str,
    req: WinnerSelection,
    claims: dict = Depends(_get_current_tenant),
):
    """Manually complete an A/B test and select a winner variant."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        test_result = (
            db.table("ab_tests")
            .select("*")
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not test_result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")

        test = test_result.data[0]
        if test["status"] not in ("running", "paused"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete test in '{test['status']}' status",
            )

        variant_result = (
            db.table("ab_test_variants")
            .select("id")
            .eq("ab_test_id", test_id)
            .eq("id", req.variant_id)
            .limit(1)
            .execute()
        )
        if not variant_result.data:
            raise HTTPException(status_code=400, detail="Invalid winner variant_id")

        now = datetime.now(timezone.utc).isoformat()
        result = (
            db.table("ab_tests")
            .update(
                {
                    "status": "completed",
                    "winner_variant_id": req.variant_id,
                    "completed_at": now,
                }
            )
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )

        try:
            db.table("ab_test_variants").update({"is_winner": True}).eq(
                "id", req.variant_id
            ).execute()
            db.table("ab_test_variants").update({"is_winner": False}).eq(
                "ab_test_id", test_id
            ).neq("id", req.variant_id).execute()
        except Exception:
            logger.exception(
                "Failed to update winner variants for A/B test %s", test_id
            )
            raise HTTPException(status_code=500, detail="Failed to update winner variants")

        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to complete A/B test %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to complete A/B test")


@router.get("/{tenant_id}/{test_id}/results")
async def get_ab_test_results(
    tenant_id: str,
    test_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get per-variant breakdown with engagement metrics for an A/B test."""
    verify_tenant(claims, tenant_id)

    try:
        db = get_service_supabase()

        test_result = (
            db.table("ab_tests")
            .select("*")
            .eq("id", test_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not test_result.data:
            raise HTTPException(status_code=404, detail="A/B test not found")

        variants_result = (
            db.table("ab_test_variants")
            .select("*")
            .eq("ab_test_id", test_id)
            .order("created_at")
            .execute()
        )
        variants = variants_result.data or []

        variant_ids = [v["id"] for v in variants]

        if variant_ids:
            sends_result = (
                db.table("ab_test_sends")
                .select("variant_id, outcome")
                .eq("ab_test_id", test_id)
                .eq("tenant_id", tenant_id)
                .in_("variant_id", variant_ids)
                .limit(10000)
                .execute()
            )
        else:
            sends_result = type("obj", (object,), {"data": []})()

        outcome_map: dict[str, dict[str, int]] = {
            vid: {"sent": 0, "delivered": 0, "opened": 0, "clicked": 0}
            for vid in variant_ids
        }
        for send in sends_result.data or []:
            vid = send.get("variant_id")
            outcome = send.get("outcome")
            if vid in outcome_map and outcome in outcome_map[vid]:
                outcome_map[vid][outcome] += 1

        results = []
        for v in variants:
            outcomes = outcome_map.get(
                v["id"], {"sent": 0, "delivered": 0, "opened": 0, "clicked": 0}
            )
            sent = outcomes["sent"]
            opened = outcomes["opened"]
            clicked = outcomes["clicked"]
            open_rate = round((opened / sent * 100), 1) if sent > 0 else 0.0
            click_rate = round((clicked / sent * 100), 1) if sent > 0 else 0.0

            p_value = None
            if sent >= 100 and len(variants) == 2:
                p_value = _calculate_significance(variants, outcome_map, v["id"])

            results.append(
                {
                    "variant": v,
                    "metrics": {
                        "sent": sent,
                        "delivered": outcomes["delivered"],
                        "opened": opened,
                        "clicked": clicked,
                        "open_rate": open_rate,
                        "click_rate": click_rate,
                    },
                    "is_winner": v.get("is_winner", False),
                    "p_value": p_value,
                }
            )

        return {
            "test": test_result.data[0],
            "variants": results,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get A/B test results for %s", test_id)
        raise HTTPException(status_code=500, detail="Failed to load A/B test results")


def _calculate_significance(
    variants: list[dict], outcome_map: dict, winner_id: str
) -> float | None:
    """Calculate rough statistical significance between two variants using z-test for proportions."""
    if len(variants) != 2:
        return None

    other = next((v for v in variants if v["id"] != winner_id), None)
    if not other:
        return None

    w_outcomes = outcome_map.get(winner_id, {"opened": 0, "sent": 0})
    o_outcomes = outcome_map.get(other["id"], {"opened": 0, "sent": 0})

    w_sent = max(w_outcomes.get("sent", 0), 1)
    o_sent = max(o_outcomes.get("sent", 0), 1)
    w_opens = w_outcomes.get("opened", 0)
    o_opens = o_outcomes.get("opened", 0)

    p1 = w_opens / w_sent
    p2 = o_opens / o_sent
    p_pooled = (w_opens + o_opens) / (w_sent + o_sent)
    se = (p_pooled * (1 - p_pooled) * (1 / w_sent + 1 / o_sent)) ** 0.5

    if se == 0:
        return None

    z = abs(p1 - p2) / se
    p_value = 2 * (1 - _normal_cdf(z))
    return round(p_value, 4)


def _normal_cdf(z: float) -> float:
    """Approximation of the normal cumulative distribution function."""
    t = 1 / (1 + 0.2316419 * abs(z))
    d = 0.3989422804014327 * math.exp(-z * z / 2)
    p = (
        d
        * t
        * (
            0.319381530
            + t
            * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
        )
    )
    return 1 - p if z > 0 else p
