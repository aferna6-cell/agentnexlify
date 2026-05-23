"""FAQ CRUD service."""

from fastapi import HTTPException

from backend.models.database import get_service_supabase as _get_service_supabase


def _get_db():
    return _get_service_supabase()


def list_faqs(tenant_id: str) -> list[dict]:
    """Return active FAQ entries for a tenant."""
    db = _get_db()
    result = (
        db.table("faq_entries")
        .select("id, question, answer, category, is_active")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def create_faq(
    tenant_id: str, question: str, answer: str, category: str | None
) -> dict:
    """Insert a new FAQ entry. Returns the created row."""
    db = _get_db()
    result = (
        db.table("faq_entries")
        .insert(
            {
                "tenant_id": tenant_id,
                "question": question,
                "answer": answer,
                "category": category,
                "is_active": True,
            }
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create FAQ entry")
    return result.data[0]


def update_faq(
    tenant_id: str, faq_id: str, question: str, answer: str, category: str | None
) -> dict:
    """Update an existing FAQ entry. Returns updated row or raises 404."""
    db = _get_db()
    update_data: dict = {"question": question, "answer": answer}
    if category is not None:
        update_data["category"] = category
    result = (
        db.table("faq_entries")
        .update(update_data)
        .eq("id", faq_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    return result.data[0]


def delete_faq(tenant_id: str, faq_id: str) -> None:
    """Soft-delete a FAQ entry (sets is_active=False)."""
    db = _get_db()
    db.table("faq_entries").update({"is_active": False}).eq("id", faq_id).eq(
        "tenant_id", tenant_id
    ).execute()
