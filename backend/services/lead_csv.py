"""CSV import/export helpers for the leads router.

Pulled out of `export_leads_csv` and `import_leads_csv` so the router stays
focused on HTTP I/O and auth. Functions here own CSV parsing, serialization,
batch email deduplication, and row-by-row import application.

DB-handling helpers accept `db: Any` as argument so test patches at
`backend.routers.leads.get_service_supabase` still apply.
"""

import csv
import io
import logging
import re
from typing import Any, Callable

from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update

logger = logging.getLogger(__name__)


CSV_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "stage": "status",
    "status": "status",
    "score": "lead_score",
    "source": "source",
    "temperature": "lead_temperature",
    "service interest": "areas_of_interest",
    "service_interest": "areas_of_interest",
    "areas_of_interest": "areas_of_interest",
    "timeline": "timeline",
    "budget": "budget",
    "notes": "conversation_summary",
    "conversation_summary": "conversation_summary",
    "next_steps": "next_steps",
    "lead_type": "lead_type",
}

VALID_STATUSES: set[str] = {"new", "contacted", "appointment_booked", "closed", "lost"}
MAX_IMPORT_ROWS = 500

EXPORT_FIELDS: list[str] = [
    "name", "email", "phone", "status", "lead_score", "lead_temperature",
    "areas_of_interest", "tags", "conversation_summary", "deal_value",
    "source", "created_at", "updated_at",
]

EXPORT_COLUMNS = (
    "name, email, phone, status, lead_score, lead_temperature, "
    "areas_of_interest, tags, conversation_summary, deal_value, "
    "source, created_at, updated_at"
)


_MAX_UPLOAD_BYTES = 2 * 1024 * 1024


def validate_csv_upload(filename: str | None, content: bytes) -> str:
    """Validate a CSV file upload and return its decoded text.

    Checks the extension, size, and encoding before parsing. Raises
    `ValueError` with a user-safe message for each rejection — router maps
    to HTTP 400.
    """
    if not filename or not filename.lower().endswith(".csv"):
        raise ValueError("File must be a .csv")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 2MB)")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 encoded") from exc


def build_export_query(
    db: Any,
    tenant_id: str,
    *,
    stage: str | None,
    search: str | None,
    assigned_to: str | None,
) -> Any:
    """Return a Supabase query for filtered/ordered leads export.

    Sanitizes `search` to alphanumerics + @_-+ . space; caller calls
    `.execute()` on returned query.
    """
    query = tenant_select(db, "leads", tenant_id, EXPORT_COLUMNS)

    if stage:
        query = query.eq("status", stage)
    if assigned_to:
        if assigned_to == "unassigned":
            query = query.is_("assigned_to", "null")
        else:
            query = query.eq("assigned_to", assigned_to)
    if search:
        safe_search = re.sub(r"[^a-zA-Z0-9@_ \-+.]", "", search).strip()[:100]
        if safe_search:
            query = query.or_(
                f"name.ilike.%{safe_search}%,email.ilike.%{safe_search}%,phone.ilike.%{safe_search}%"
            )

    return query.order("created_at", desc=True).limit(5000)


def serialize_leads_to_csv(leads_data: list[dict[str, Any]]) -> str:
    """Render lead rows as CSV text using EXPORT_FIELDS columns.

    Tag arrays are joined with ", ".
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for lead in leads_data:
        row = {**lead}
        if isinstance(row.get("tags"), list):
            row["tags"] = ", ".join(row["tags"])
        writer.writerow(row)
    return output.getvalue()


def parse_csv_for_import(
    text: str,
) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]], dict[str, str]]:
    """Parse a CSV upload into `(parsed_rows, errors, col_map)`.

    Caller checks `col_map` emptiness to map to HTTP 400 "no recognized
    columns". Stops at MAX_IMPORT_ROWS, recording a final error row.

    Raises ValueError if the CSV has no headers.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no headers")

    col_map: dict[str, str] = {}
    for header in reader.fieldnames:
        key = header.strip().lower().replace(" ", "_")
        if key in CSV_FIELD_MAP:
            col_map[header] = CSV_FIELD_MAP[key]
        elif key.replace("_", " ") in CSV_FIELD_MAP:
            col_map[header] = CSV_FIELD_MAP[key.replace("_", " ")]

    parsed_rows: list[tuple[int, dict[str, Any]]] = []
    errors: list[dict[str, Any]] = []

    if not col_map:
        return parsed_rows, errors, col_map

    for i, row in enumerate(reader, start=2):
        if i - 1 > MAX_IMPORT_ROWS:
            errors.append({"row": i, "error": f"Stopped at {MAX_IMPORT_ROWS} rows"})
            break

        lead_data: dict[str, Any] = {}
        for csv_col, db_col in col_map.items():
            val = (row.get(csv_col) or "").strip()
            if val:
                lead_data[db_col] = val

        if not lead_data.get("email") and not lead_data.get("phone") and not lead_data.get("name"):
            errors.append({"row": i, "error": "No name, email, or phone"})
            continue

        if lead_data.get("status") and lead_data["status"] not in VALID_STATUSES:
            lead_data["status"] = "new"

        if lead_data.get("lead_score"):
            try:
                lead_data["lead_score"] = int(lead_data["lead_score"])
            except ValueError:
                del lead_data["lead_score"]

        parsed_rows.append((i, lead_data))

    return parsed_rows, errors, col_map


def fetch_existing_emails(
    db: Any, tenant_id: str, emails: list[str]
) -> dict[str, str]:
    """Single-query batch dedup: email (lowercased) -> existing lead id."""
    existing_by_email: dict[str, str] = {}
    if not emails:
        return existing_by_email
    try:
        result = (
            tenant_select(db, "leads", tenant_id, "id, email")
            .in_("email", list(set(emails)))
            .execute()
        )
        for lead in (result.data or []):
            if lead.get("email"):
                existing_by_email[lead["email"].lower()] = lead["id"]
    except Exception as e:
        logger.warning("Import batch dedup query failed: %s", e)
    return existing_by_email


def apply_import_batch(
    db: Any,
    tenant_id: str,
    *,
    parsed_rows: list[tuple[int, dict[str, Any]]],
    existing_by_email: dict[str, str],
    errors: list[dict[str, Any]],
    fire_event: Callable[[str, str, dict[str, Any]], None],
) -> tuple[int, int]:
    """Apply parsed rows to the leads table. Returns `(created, updated)`.

    Updates `errors` in place. Fires `lead.created` events via callback so
    tests can patch `fire_event_background` at the router level.
    """
    created = 0
    updated = 0

    for i, lead_data in parsed_rows:
        email = (lead_data.get("email") or "").lower()
        if email and email in existing_by_email:
            updates = {k: v for k, v in lead_data.items() if k != "email"}
            if updates:
                try:
                    tenant_update(db, "leads", tenant_id, updates).eq(
                        "id", existing_by_email[email]
                    ).execute()
                except Exception as e:
                    errors.append({"row": i, "error": str(e)[:100]})
                    continue
            updated += 1
            continue

        lead_data.setdefault("status", "new")
        try:
            result = tenant_insert(db, "leads", tenant_id, lead_data).execute()
            if result.data:
                created += 1
                fire_event(tenant_id, "lead.created", {
                    "lead_id": result.data[0]["id"],
                    "name": lead_data.get("name"),
                    "email": lead_data.get("email"),
                    "source": "csv_import",
                })
            else:
                errors.append({"row": i, "error": "Insert returned no data"})
        except Exception as e:
            errors.append({"row": i, "error": str(e)[:100]})

    return created, updated
