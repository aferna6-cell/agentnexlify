"""Pure logic for contractor bids — totals, AI prompt + parse, branded HTML render.

No FastAPI / no DB / no Anthropic client. Router wires DB + LLM calls and
delegates to these helpers. All user-controlled strings in HTML output are
escaped via html.escape() to prevent XSS in the public PDF view.
"""

import html
import json
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------

def compute_totals(items: list[dict]) -> tuple[float, float, float]:
    """Compute subtotal, tax (0 for now), and total from line items.

    Mutates each item in-place to fill in `total` if missing or zero.
    Returns (subtotal, tax, total) rounded to 2 decimals.
    """
    subtotal = 0.0
    for item in items:
        line_total = item.get("total", 0.0)
        if line_total == 0.0:
            line_total = item.get("quantity", 1) * item.get("unit_price", 0)
            item["total"] = round(line_total, 2)
        subtotal += line_total
    subtotal = round(subtotal, 2)
    tax = 0.0
    total = round(subtotal + tax, 2)
    return subtotal, tax, total


# ---------------------------------------------------------------------------
# AI bid generation — prompt + parse
# ---------------------------------------------------------------------------

def build_ai_bid_prompt(job_description: str, business_context: str) -> str:
    """Build the Anthropic prompt for AI bid generation.

    `business_context` may be empty; caller is responsible for assembling it
    (e.g. "Business: Acme (painting) in Clemson").
    """
    return (
        "You are a professional contractor bid estimator. Based on the job description below, "
        "generate a detailed bid with line items, pricing, terms, timeline, and warranty.\n\n"
        f"Job description: \"{job_description}\"\n\n"
        f"{business_context}\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "title": "Short bid title",\n'
        '  "description": "1-2 paragraph summary of the scope of work",\n'
        '  "items": [\n'
        '    {"description": "Line item name", "quantity": 1, "unit": "sqft", "unit_price": 3.50, "total": 350.00}\n'
        "  ],\n"
        '  "terms": "Payment terms (e.g., 50% upfront, 50% on completion)",\n'
        '  "timeline": "Estimated duration (e.g., 5-7 business days)",\n'
        '  "warranty": "Warranty details (e.g., 2-year warranty on workmanship)"\n'
        "}\n\n"
        "Rules:\n"
        "- Generate realistic line items with materials and labor separated\n"
        "- Use market-rate pricing for the area if a location is given\n"
        "- Each item must have description, quantity, unit, unit_price, and total (quantity * unit_price)\n"
        "- Include at least 3 line items\n"
        "- Terms should be professional and standard for the trade\n"
        "- Output ONLY the JSON object, no markdown fences or extra text"
    )


def build_business_context(biz_name: str, biz_type: str, city: str) -> str:
    """Assemble the optional business-context line passed into the AI prompt."""
    if not biz_name:
        return ""
    context = f"Business: {biz_name}"
    if biz_type:
        context += f" ({biz_type})"
    if city:
        context += f" in {city}"
    return context


def parse_ai_bid_response(text: str) -> dict[str, Any]:
    """Parse the AI's JSON bid output, stripping markdown fences if present.

    Raises json.JSONDecodeError on invalid JSON. Caller wraps in HTTPException.
    Normalizes line items: backfills `total` when missing/zero, recomputes
    subtotal across items. Tax is always 0 for now (caller may add later).
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()

    result = json.loads(text)
    items = result.get("items") or []
    for item in items:
        if "total" not in item or item["total"] == 0:
            item["total"] = round(
                item.get("quantity", 1) * item.get("unit_price", 0), 2
            )
    subtotal = round(sum(i.get("total", 0) for i in items), 2)

    return {
        "title": result.get("title", "Untitled Bid"),
        "description": result.get("description"),
        "items_json": items,
        "subtotal": subtotal,
        "tax": 0.0,
        "total": subtotal,
        "terms": result.get("terms"),
        "timeline": result.get("timeline"),
        "warranty": result.get("warranty"),
    }


# ---------------------------------------------------------------------------
# Branded HTML render
# ---------------------------------------------------------------------------

def _escape(value: Any) -> str:
    """html.escape with str() coercion + None → ''."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _format_bid_date(created_at: str) -> str:
    if not created_at:
        return ""
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y")
    except Exception:
        return created_at[:10] if len(created_at) >= 10 else created_at


def _build_items_rows(items: list[dict]) -> str:
    rows = ""
    for i, item in enumerate(items, 1):
        desc = _escape(item.get("description", ""))
        qty = _escape(item.get("quantity", 1))
        unit = _escape(item.get("unit", "each"))
        try:
            unit_price = float(item.get("unit_price", 0) or 0)
        except (TypeError, ValueError):
            unit_price = 0.0
        try:
            line_total = float(item.get("total", 0) or 0)
        except (TypeError, ValueError):
            line_total = 0.0
        rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{i}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{desc}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center;'>{qty} {unit}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${unit_price:,.2f}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;'>${line_total:,.2f}</td>"
            f"</tr>"
        )
    return rows


def _optional_section(label: str, body: str) -> str:
    if not body:
        return ""
    return (
        f"<div style='margin-top:24px;'>"
        f"<h3 style='font-size:14px;color:#374151;margin:0 0 8px 0;"
        f"text-transform:uppercase;letter-spacing:0.5px;'>{_escape(label)}</h3>"
        f"<p style='margin:0;color:#4b5563;line-height:1.6;'>{_escape(body)}</p>"
        f"</div>"
    )


def _customer_block(name: str, email: str, phone: str) -> str:
    if not (name or email or phone):
        return ""
    parts = [
        "<div>",
        "<h3 style='font-size:12px;color:#6b7280;text-transform:uppercase;"
        "letter-spacing:0.5px;margin:0 0 8px 0;'>Prepared For</h3>",
        f"<p style='margin:0;font-weight:600;color:#111827;'>{_escape(name)}</p>",
    ]
    if email:
        parts.append(
            f"<p style='margin:2px 0;color:#4b5563;'>{_escape(email)}</p>"
        )
    if phone:
        parts.append(
            f"<p style='margin:2px 0;color:#4b5563;'>{_escape(phone)}</p>"
        )
    parts.append("</div>")
    return "".join(parts)


def render_bid_html(bid: dict, business: dict, customer: dict) -> str:
    """Build a print-friendly HTML document for a bid.

    All user-controlled strings are HTML-escaped to prevent XSS in the
    public-facing PDF view. Numeric fields are coerced to float and rendered
    with %.2f formatting (no escape needed).
    """
    biz_name = _escape(business.get("business_name") or "Business")
    biz_email = _escape(business.get("owner_email") or "")
    biz_phone = _escape(business.get("phone") or "")
    biz_city = _escape(business.get("city") or "")

    cust_name = customer.get("name") or ""
    cust_email = customer.get("email") or ""
    cust_phone = customer.get("phone") or ""

    title = _escape(bid.get("title") or "Bid")
    description = _escape(bid.get("description") or "")
    items = bid.get("items_json") or []
    try:
        subtotal = float(bid.get("subtotal", 0) or 0)
    except (TypeError, ValueError):
        subtotal = 0.0
    try:
        tax = float(bid.get("tax", 0) or 0)
    except (TypeError, ValueError):
        tax = 0.0
    try:
        total = float(bid.get("total", 0) or 0)
    except (TypeError, ValueError):
        total = 0.0
    bid_status = _escape(bid.get("status") or "draft")
    date_display = _escape(_format_bid_date(bid.get("created_at") or ""))

    items_rows = _build_items_rows(items)
    terms_section = _optional_section("Payment Terms", bid.get("terms") or "")
    timeline_section = _optional_section("Timeline", bid.get("timeline") or "")
    warranty_section = _optional_section("Warranty", bid.get("warranty") or "")
    customer_block = _customer_block(cust_name, cust_email, cust_phone)

    header_meta = biz_email
    if biz_phone:
        header_meta += f" | {biz_phone}"
    if biz_city:
        header_meta += f" | {biz_city}"

    description_html = (
        f'<p style="margin:0 0 24px 0;color:#4b5563;line-height:1.6;">{description}</p>'
        if description
        else '<div style="margin-bottom:24px;"></div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {biz_name}</title>
<style>
  @media print {{
    body {{ margin: 0; padding: 0; }}
    .no-print {{ display: none !important; }}
    @page {{ margin: 0.75in; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #111827; margin: 0; padding: 0; background: #f9fafb; }}
</style>
</head>
<body>
<div style="max-width:800px;margin:24px auto;background:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);overflow:hidden;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:32px 40px;color:#ffffff;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
      <div>
        <h1 style="margin:0;font-size:28px;font-weight:700;">{biz_name}</h1>
        <p style="margin:4px 0 0 0;opacity:0.85;font-size:14px;">{header_meta}</p>
      </div>
      <div style="text-align:right;">
        <span style="background:rgba(255,255,255,0.2);padding:4px 16px;border-radius:20px;font-size:13px;text-transform:uppercase;letter-spacing:1px;">{bid_status}</span>
        <p style="margin:8px 0 0 0;font-size:13px;opacity:0.85;">{date_display}</p>
      </div>
    </div>
  </div>

  <!-- Body -->
  <div style="padding:32px 40px;">

    <!-- Title & Description -->
    <h2 style="margin:0 0 8px 0;font-size:22px;color:#1e3a5f;">{title}</h2>
    {description_html}

    <!-- Customer Info -->
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:24px;padding:16px;background:#f3f4f6;border-radius:6px;">
      {customer_block}
    </div>

    <!-- Line Items -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;width:40px;">#</th>
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Description</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Qty</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Unit Price</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;letter-spacing:0.5px;border-bottom:2px solid #e5e7eb;">Total</th>
        </tr>
      </thead>
      <tbody>
        {items_rows}
      </tbody>
    </table>

    <!-- Totals -->
    <div style="display:flex;justify-content:flex-end;margin-bottom:32px;">
      <div style="width:280px;">
        <div style="display:flex;justify-content:space-between;padding:6px 0;color:#4b5563;">
          <span>Subtotal</span><span>${subtotal:,.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;color:#4b5563;">
          <span>Tax</span><span>${tax:,.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0;margin-top:4px;border-top:2px solid #1e3a5f;font-size:18px;font-weight:700;color:#1e3a5f;">
          <span>Total</span><span>${total:,.2f}</span>
        </div>
      </div>
    </div>

    <!-- Terms / Timeline / Warranty -->
    {terms_section}
    {timeline_section}
    {warranty_section}

  </div>

  <!-- Footer -->
  <div style="padding:16px 40px;background:#f9fafb;border-top:1px solid #e5e7eb;text-align:center;">
    <p style="margin:0;font-size:12px;color:#9ca3af;">Generated by {biz_name} via AgentNexLiFy</p>
  </div>

</div>

<!-- Print button (hidden in print) -->
<div class="no-print" style="text-align:center;padding:16px;">
  <button onclick="window.print()" style="background:#2563eb;color:#fff;border:none;padding:10px 32px;border-radius:6px;font-size:14px;cursor:pointer;">Print / Save as PDF</button>
</div>

</body>
</html>"""
