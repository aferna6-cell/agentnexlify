"""Sequential invoice number generation per tenant."""

import logging

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)


async def get_next_invoice_number(db, tenant_id: str, attempt: int = 0) -> str:
    """Generate a sequential invoice number: INV-{tenant_id[:4].upper()}-{NNN}.

    The `attempt` param offsets the sequence to handle retry on uniqueness conflict.
    """
    try:
        result = (
            tenant_table(db, "invoices", tenant_id)
            .select("invoice_number")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last_num = result.data[0].get("invoice_number", "INV-XXXX-000")
            parts = last_num.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                seq = int(parts[1]) + 1 + attempt
            else:
                seq = 1 + attempt
        else:
            seq = 1 + attempt
    except Exception:
        logger.warning(
            "Could not determine next invoice number for tenant %s",
            tenant_id,
            exc_info=True,
        )
        seq = 1 + attempt
    prefix = tenant_id[:4].upper()
    return f"INV-{prefix}-{seq:03d}"
