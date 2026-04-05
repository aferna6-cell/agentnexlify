"""Widget booking-adjacent flows: restaurant order extraction and contractor bid requests.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_supabase
from backend.services.email_sender import send_email
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Order extraction + notifications (restaurant ordering via chat)
# ---------------------------------------------------------------------------

ORDER_JSON_RE = re.compile(r"<!--ORDER_JSON:(.*?)-->", re.DOTALL)

_ALLOWED_ORDER_TYPES = {"pickup", "delivery"}
_MAX_ORDER_ITEMS = 25


def _extract_order_from_response(response_text: str) -> dict | None:
    """Extract structured order JSON from AI response, if present and valid."""
    match = ORDER_JSON_RE.search(response_text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("order_extract: found ORDER_JSON marker but JSON parse failed")
        return None
    return _validate_order_payload(data)


def _strip_order_json_from_response(response_text: str) -> str:
    """Remove the ORDER_JSON marker from the response shown to the user."""
    return ORDER_JSON_RE.sub("", response_text).rstrip()


def _coerce_money(value: Any) -> float | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount < 0 or amount > 100000:
        return None
    return round(amount, 2)


def _validate_order_payload(order_data: Any) -> dict | None:
    if not isinstance(order_data, dict):
        logger.warning("order_extract: order payload is not an object")
        return None

    raw_items = order_data.get("items")
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > _MAX_ORDER_ITEMS:
        logger.warning("order_extract: invalid items payload")
        return None

    clean_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            logger.warning("order_extract: item payload is not an object")
            return None
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 120:
            logger.warning("order_extract: invalid item name")
            return None
        try:
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError):
            logger.warning("order_extract: invalid item quantity")
            return None
        if quantity < 1 or quantity > 50:
            logger.warning("order_extract: quantity out of range")
            return None
        price = _coerce_money(item.get("price", 0))
        if price is None:
            logger.warning("order_extract: invalid item price")
            return None
        clean_items.append({
            "name": name,
            "price": price,
            "quantity": quantity,
        })

    subtotal = _coerce_money(order_data.get("subtotal", 0))
    tax = _coerce_money(order_data.get("tax", 0))
    total = _coerce_money(order_data.get("total", 0))
    order_type = str(order_data.get("order_type") or "pickup").strip().lower()
    customer_name = str(order_data.get("customer_name") or "").strip()
    customer_phone = str(order_data.get("customer_phone") or "").strip()
    customer_email = str(order_data.get("customer_email") or "").strip()
    delivery_address = str(order_data.get("delivery_address") or "").strip()
    notes = str(order_data.get("notes") or "").strip()

    if subtotal is None or tax is None or total is None:
        logger.warning("order_extract: invalid subtotal/tax/total")
        return None
    if order_type not in _ALLOWED_ORDER_TYPES:
        logger.warning("order_extract: invalid order_type=%s", order_type)
        return None
    if not customer_name or len(customer_name) > 120:
        logger.warning("order_extract: missing or invalid customer_name")
        return None
    if not customer_phone or len(customer_phone) > 40:
        logger.warning("order_extract: missing or invalid customer_phone")
        return None
    if customer_email and len(customer_email) > 255:
        logger.warning("order_extract: invalid customer_email")
        return None
    if delivery_address and len(delivery_address) > 500:
        logger.warning("order_extract: invalid delivery_address")
        return None
    if notes and len(notes) > 1000:
        logger.warning("order_extract: invalid notes")
        return None
    if order_type == "delivery" and not delivery_address:
        logger.warning("order_extract: delivery order missing delivery_address")
        return None

    computed_subtotal = round(sum(item["price"] * item["quantity"] for item in clean_items), 2)
    computed_total = round(computed_subtotal + tax, 2)
    if abs(computed_subtotal - subtotal) > 0.05:
        logger.warning("order_extract: subtotal mismatch model=%s computed=%s", subtotal, computed_subtotal)
        return None
    if abs(computed_total - total) > 0.05:
        logger.warning("order_extract: total mismatch model=%s computed=%s", total, computed_total)
        return None

    return {
        "items": clean_items,
        "subtotal": computed_subtotal,
        "tax": tax,
        "total": computed_total,
        "order_type": order_type,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "delivery_address": delivery_address,
        "notes": notes,
    }


async def _process_order_from_chat(
    tenant_id: str, session_id: str, order_data: dict,
) -> None:
    """Create an order record and send notifications to owner + customer."""
    import html as html_mod

    db = get_supabase()

    # Build order record
    items = order_data.get("items", [])
    record = {
        "tenant_id": tenant_id,
        "session_id": session_id,
        "customer_name": order_data.get("customer_name"),
        "customer_phone": order_data.get("customer_phone"),
        "customer_email": order_data.get("customer_email"),
        "items_json": items,
        "subtotal": float(order_data.get("subtotal", 0)),
        "tax": float(order_data.get("tax", 0)),
        "total": float(order_data.get("total", 0)),
        "order_type": order_data.get("order_type", "pickup"),
        "delivery_address": order_data.get("delivery_address") or None,
        "notes": order_data.get("notes") or None,
        "status": "new",
    }

    try:
        result = db.table("orders").insert(record).execute()
        if not result.data:
            logger.error("order_create: insert returned no data for tenant=%s", tenant_id)
            return
        order = result.data[0]
        logger.info("order_create: order %s created for tenant=%s", order["id"], tenant_id)
    except Exception:
        logger.exception("order_create: failed for tenant=%s", tenant_id)
        return

    # Fetch tenant info for notifications
    try:
        tenant_result = (
            db.table("tenants")
            .select("owner_email, business_name, business_phone")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if not tenant_result.data:
            return
        tenant = tenant_result.data[0]
    except Exception:
        logger.exception("order_notify: failed to fetch tenant %s", tenant_id)
        return

    business_name = tenant.get("business_name") or "Your Business"
    customer_name = record["customer_name"] or "Customer"
    items_summary = ", ".join(
        f"{i.get('name', 'item')} x{i.get('quantity', 1)}"
        for i in items[:5]
    )
    if len(items) > 5:
        items_summary += f" +{len(items) - 5} more"
    total_str = f"${record['total']:.2f}"

    # --- SMS notification to owner ---
    owner_phone = tenant.get("business_phone")
    if owner_phone:
        sms_body = (
            f"New {record['order_type']} order from {customer_name}!\n"
            f"Items: {items_summary}\n"
            f"Total: {total_str}\n"
            f"Check your dashboard to confirm."
        )
        try:
            from backend.services.twilio_service import send_sms
            await send_sms(to=owner_phone, body=sms_body)
            logger.info("order_notify: SMS sent to owner for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: owner SMS failed for tenant=%s", tenant_id, exc_info=True)

    # --- Email notification to owner ---
    owner_email = tenant.get("owner_email")
    if owner_email:
        safe_biz = html_mod.escape(business_name)
        safe_name = html_mod.escape(customer_name)
        safe_phone = html_mod.escape(record.get("customer_phone") or "Not provided")
        safe_type = html_mod.escape(record["order_type"].capitalize())

        items_rows = ""
        for i in items:
            iname = html_mod.escape(i.get("name", "Item"))
            qty = i.get("quantity", 1)
            iprice = f"${float(i.get('price', 0)):.2f}"
            items_rows += (
                f"<tr><td style='padding:4px 12px 4px 0;'>{iname}</td>"
                f"<td style='padding:4px 8px;text-align:center;'>{qty}</td>"
                f"<td style='padding:4px 0;text-align:right;'>{iprice}</td></tr>"
            )

        body_html = (
            f"<h2>New Order for {safe_biz}</h2>"
            f"<p>A new <strong>{safe_type}</strong> order was just placed via your chat widget:</p>"
            f"<p><strong>Customer:</strong> {safe_name}<br>"
            f"<strong>Phone:</strong> {safe_phone}</p>"
            f"<table style='border-collapse:collapse;margin:16px 0;width:100%;'>"
            f"<tr style='border-bottom:1px solid #ddd;'>"
            f"<th style='text-align:left;padding:4px 12px 4px 0;'>Item</th>"
            f"<th style='text-align:center;padding:4px 8px;'>Qty</th>"
            f"<th style='text-align:right;padding:4px 0;'>Price</th></tr>"
            f"{items_rows}"
            f"<tr style='border-top:2px solid #333;'>"
            f"<td colspan='2' style='padding:8px 12px 4px 0;font-weight:bold;'>Total</td>"
            f"<td style='padding:8px 0 4px;text-align:right;font-weight:bold;'>{total_str}</td></tr>"
            f"</table>"
        )
        if record["delivery_address"]:
            safe_addr = html_mod.escape(record["delivery_address"])
            body_html += f"<p><strong>Delivery address:</strong> {safe_addr}</p>"
        if record["notes"]:
            safe_notes = html_mod.escape(record["notes"])
            body_html += f"<p><strong>Notes:</strong> {safe_notes}</p>"
        body_html += "<p>Log in to your dashboard to confirm this order.</p>"

        try:
            await send_email(
                to=owner_email,
                subject=f"New order for {business_name}: {customer_name} ({total_str})",
                body_html=body_html,
                tenant_id=tenant_id,
            )
            logger.info("order_notify: email sent to owner for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: owner email failed for tenant=%s", tenant_id, exc_info=True)

    # --- SMS confirmation to customer ---
    customer_phone = record.get("customer_phone")
    if customer_phone:
        confirm_body = (
            f"Your {record['order_type']} order from {business_name} has been received!\n"
            f"Items: {items_summary}\n"
            f"Total: {total_str}\n"
        )
        if owner_phone:
            confirm_body += f"Questions? Call us at {owner_phone}"
        try:
            from backend.services.twilio_service import send_sms
            await send_sms(to=customer_phone, body=confirm_body)
            logger.info("order_notify: confirmation SMS sent to customer for tenant=%s", tenant_id)
        except Exception:
            logger.error("order_notify: customer SMS failed for tenant=%s", tenant_id, exc_info=True)

    # Fire webhook for new order
    fire_event_background(tenant_id, "order.created", {
        "order_id": order["id"],
        "customer_name": customer_name,
        "total": record["total"],
        "order_type": record["order_type"],
        "items_count": len(items),
    })


# ---------------------------------------------------------------------------
# Bid request extraction from chat (contractor quick-bid via chat)
# ---------------------------------------------------------------------------

BID_REQUEST_RE = re.compile(r"<!--BID_REQUEST:(.*?)-->", re.DOTALL)


def _extract_bid_request_from_response(response_text: str) -> dict | None:
    """Extract structured bid request JSON from AI response, if present and valid."""
    match = BID_REQUEST_RE.search(response_text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("bid_extract: found BID_REQUEST marker but JSON parse failed")
        return None
    return _validate_bid_request_payload(data)


def _strip_bid_request_from_response(response_text: str) -> str:
    """Remove the BID_REQUEST marker from the response shown to the user."""
    return BID_REQUEST_RE.sub("", response_text).rstrip()


def _validate_bid_request_payload(bid_data: Any) -> dict | None:
    if not isinstance(bid_data, dict):
        logger.warning("bid_extract: payload is not an object")
        return None

    scope = str(bid_data.get("scope") or "").strip()
    timeline = str(bid_data.get("timeline") or "").strip()
    location = str(bid_data.get("location") or "").strip()
    budget = str(bid_data.get("budget") or "").strip()
    customer_name = str(bid_data.get("customer_name") or "").strip()
    customer_email = str(bid_data.get("customer_email") or "").strip()
    customer_phone = str(bid_data.get("customer_phone") or "").strip()

    if not scope or len(scope) > 1000:
        logger.warning("bid_extract: missing or invalid scope")
        return None
    if not customer_name or len(customer_name) > 120:
        logger.warning("bid_extract: missing or invalid customer_name")
        return None
    if (not customer_email and not customer_phone):
        logger.warning("bid_extract: missing customer contact info")
        return None
    if customer_email and len(customer_email) > 255:
        logger.warning("bid_extract: invalid customer_email")
        return None
    if customer_phone and len(customer_phone) > 40:
        logger.warning("bid_extract: invalid customer_phone")
        return None
    if timeline and len(timeline) > 200:
        logger.warning("bid_extract: invalid timeline")
        return None
    if location and len(location) > 300:
        logger.warning("bid_extract: invalid location")
        return None
    if budget and len(budget) > 120:
        logger.warning("bid_extract: invalid budget")
        return None

    return {
        "scope": scope,
        "timeline": timeline,
        "location": location,
        "budget": budget,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
    }


def _process_bid_request_from_chat(
    tenant_id: str, session_id: str, bid_data: dict,
) -> None:
    """Log a bid request as a high-priority action item for the business owner."""
    db = get_supabase()

    scope = bid_data.get("scope", "")
    customer_name = bid_data.get("customer_name", "Unknown")
    customer_email = bid_data.get("customer_email", "")
    customer_phone = bid_data.get("customer_phone", "")
    timeline = bid_data.get("timeline", "")
    location = bid_data.get("location", "")
    budget = bid_data.get("budget", "")

    # Build a readable description
    parts = [f"Bid request from {customer_name}"]
    if scope:
        parts.append(f"Scope: {scope}")
    if timeline:
        parts.append(f"Timeline: {timeline}")
    if location:
        parts.append(f"Location: {location}")
    if budget:
        parts.append(f"Budget: {budget}")
    if customer_email:
        parts.append(f"Email: {customer_email}")
    if customer_phone:
        parts.append(f"Phone: {customer_phone}")
    description = " | ".join(parts)

    # Find the conversation_id for this session
    conversation_id = None
    try:
        conv_result = (
            db.table("conversations")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if conv_result.data:
            conversation_id = conv_result.data[0]["id"]
    except Exception:
        logger.warning("bid_request: failed to find conversation for session %s", session_id, exc_info=True)

    try:
        db.table("action_items").insert({
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "description": description[:1000],
            "priority": "high",
            "status": "open",
        }).execute()
        logger.info(
            "bid_request: logged action item for tenant=%s session=%s customer=%s",
            tenant_id, session_id, customer_name,
        )
    except Exception:
        logger.exception(
            "bid_request: failed to insert action_item for tenant=%s session=%s",
            tenant_id, session_id,
        )
