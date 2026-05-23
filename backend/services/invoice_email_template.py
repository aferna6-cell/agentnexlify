"""Invoice email HTML builder — produces the customer-facing invoice email body."""

import html as _html


def build_invoice_email_html(invoice: dict, business: dict, lead: dict) -> str:
    """Build a professional HTML email body for an invoice with payment link."""
    biz_name = business.get("business_name") or "Your Service Provider"
    biz_email = business.get("owner_email") or ""

    cust_name = _html.escape(lead.get("name") or "Valued Customer")
    invoice_number = _html.escape(invoice.get("invoice_number") or "N/A")
    total = invoice.get("total", 0)
    due_date = _html.escape(invoice.get("due_date") or "")
    notes = _html.escape(invoice.get("notes") or "")
    payment_link = invoice.get("stripe_payment_link") or ""
    items = invoice.get("items_json") or []
    subtotal = invoice.get("subtotal", 0)
    tax_amount = invoice.get("tax_amount", 0)

    due_section = f"<p style='color:#4b5563;'>Due: <strong>{due_date}</strong></p>" if due_date else ""
    notes_section = f"<p style='color:#4b5563;margin-top:16px;'>{notes}</p>" if notes else ""

    pay_button = ""
    if payment_link:
        pay_button = (
            f"<div style='text-align:center;margin:32px 0;'>"
            f"<a href='{payment_link}' style='background:#2563eb;color:#ffffff;padding:14px 32px;"
            f"border-radius:6px;text-decoration:none;font-size:16px;font-weight:600;display:inline-block;'>"
            f"Pay Now — ${total:,.2f}</a></div>"
        )

    rows = ""
    for item in items:
        desc = item.get("description", "")
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        line_total = round(qty * unit_price, 2)
        rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;'>{desc}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center;'>{qty}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${unit_price:,.2f}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;'>${line_total:,.2f}</td>"
            f"</tr>"
        )

    tax_row = ""
    if tax_amount and tax_amount > 0:
        tax_row = (
            f"<tr><td colspan='3' style='text-align:right;padding:4px 12px;color:#6b7280;'>Tax</td>"
            f"<td style='text-align:right;padding:4px 12px;color:#6b7280;'>${tax_amount:,.2f}</td></tr>"
        )

    return f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:28px 32px;border-radius:8px 8px 0 0;">
    <h1 style="color:#ffffff;margin:0;font-size:22px;">{biz_name}</h1>
    <p style="color:rgba(255,255,255,0.85);margin:4px 0 0 0;font-size:14px;">Invoice {invoice_number}</p>
  </div>
  <div style="background:#ffffff;padding:28px 32px;border:1px solid #e5e7eb;border-top:none;">
    <p style="color:#374151;font-size:16px;">Hi {cust_name},</p>
    <p style="color:#4b5563;">Please find your invoice from {biz_name} below.</p>
    {due_section}

    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
      <thead>
        <tr style="background:#f9fafb;">
          <th style="padding:10px 12px;text-align:left;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Description</th>
          <th style="padding:10px 12px;text-align:center;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Qty</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Unit Price</th>
          <th style="padding:10px 12px;text-align:right;font-size:12px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb;">Total</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
      <tfoot>
        <tr>
          <td colspan="3" style="text-align:right;padding:8px 12px;color:#4b5563;border-top:1px solid #e5e7eb;">Subtotal</td>
          <td style="text-align:right;padding:8px 12px;color:#4b5563;border-top:1px solid #e5e7eb;">${subtotal:,.2f}</td>
        </tr>
        {tax_row}
        <tr>
          <td colspan="3" style="text-align:right;padding:10px 12px;font-size:16px;font-weight:700;color:#1e3a5f;border-top:2px solid #1e3a5f;">Total Due</td>
          <td style="text-align:right;padding:10px 12px;font-size:16px;font-weight:700;color:#1e3a5f;border-top:2px solid #1e3a5f;">${total:,.2f}</td>
        </tr>
      </tfoot>
    </table>

    {pay_button}
    {notes_section}

    <p style="color:#6b7280;font-size:13px;margin-top:24px;">
      Questions? Contact us at {biz_email}
    </p>
  </div>
  <div style="background:#f9fafb;padding:12px 32px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">Sent via AgentNexLiFy</p>
  </div>
</div>
"""
