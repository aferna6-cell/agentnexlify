"""Public booking page — shareable URL where customers can book appointments
without going through the chat widget.

Two public endpoints (NO auth required):
  GET  /api/v1/book/{business_slug}         — server-rendered HTML booking page
  POST /api/v1/book/{business_slug}/submit  — create appointment + lead
"""

import html
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.services.booking import generate_available_slots, link_appointment_to_lead
from backend.services.email_sender import send_email
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/book", tags=["booking-page"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BookingSubmitRequest(BaseModel):
    name: str
    email: str
    phone: str
    date: str        # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    service_type_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lookup_tenant_by_slug(slug: str) -> dict:
    """Return tenant row for the given business_slug. Raises 404 on miss."""
    db = get_supabase()
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, owner_email, plan")
            .eq("business_slug", slug)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("DB error looking up tenant by slug %s", slug)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    if not result.data:
        raise HTTPException(status_code=404, detail="Booking page not found")

    return result.data[0]


def _fetch_widget_color(tenant_id: str) -> str:
    """Return the tenant's primary branding color, or a safe default."""
    db = get_supabase()
    try:
        result = (
            db.table("widget_configs")
            .select("primary_color")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("primary_color"):
            return result.data[0]["primary_color"]
    except Exception:
        logger.warning("Could not fetch widget color for tenant %s", tenant_id, exc_info=True)
    return "#00BFFF"


def _slot_available(tenant_id: str, target_date: date, start_time_str: str, end_time_str: str) -> bool:
    """Return True if the requested slot is still open (no overlapping confirmed appt)."""
    db = get_supabase()
    try:
        result = (
            db.table("appointments")
            .select("id")
            .eq("tenant_id", tenant_id)
            .eq("status", "confirmed")
            .lt("start_time", end_time_str)
            .gt("end_time", start_time_str)
            .limit(1)
            .execute()
        )
        return not result.data
    except Exception:
        logger.exception("DB error checking slot availability for tenant %s", tenant_id)
        # Fail safe — treat as unavailable so we don't double-book
        return False


def _build_service_type_section(service_types: list[dict], safe_color: str) -> str:
    """Build HTML for the service type selector, if service types are configured."""
    if not service_types:
        return ""

    options_html = ""
    for st in service_types:
        safe_id = html.escape(str(st["id"]))
        safe_name = html.escape(st.get("name") or "Service")
        duration = st.get("duration_minutes", 30)
        price = st.get("price")
        desc = st.get("description") or ""
        safe_desc = html.escape(desc)

        price_html = ""
        if price is not None and float(price) > 0:
            price_html = f'<span style="color:{safe_color};font-weight:600;">${float(price):.0f}</span>'

        options_html += f"""
        <label class="service-option" style="display:flex;align-items:center;gap:12px;padding:14px 16px;border:1px solid #333;border-radius:10px;cursor:pointer;transition:border-color 0.2s;" onmouseover="this.style.borderColor='{safe_color}'" onmouseout="if(!this.querySelector('input').checked)this.style.borderColor='#333'">
          <input type="radio" name="service_type" value="{safe_id}" data-duration="{duration}" style="accent-color:{safe_color};width:18px;height:18px;" onchange="selectService(this)"/>
          <div style="flex:1;">
            <div style="font-weight:600;font-size:0.95rem;">{safe_name}</div>
            <div style="font-size:0.8rem;color:#999;">{duration} min{' — ' + safe_desc if safe_desc else ''}</div>
          </div>
          {price_html}
        </label>"""

    return f"""
    <div class="card" id="service-card">
      <h2>Select a Service</h2>
      <div style="display:flex;flex-direction:column;gap:10px;">
        {options_html}
      </div>
      <input type="hidden" id="f-service-type" value="" />
    </div>"""


def _build_booking_page_html(
    business_name: str,
    primary_color: str,
    slug: str,
    slots_by_date: dict[str, list[dict]],
    service_types: list[dict] | None = None,
) -> str:
    """Return a fully self-contained HTML booking page."""

    safe_name = html.escape(business_name)
    safe_color = html.escape(primary_color)
    service_types = service_types or []

    # Build slot option elements grouped by date
    slot_options_html = ""
    if not slots_by_date:
        slot_options_html = "<p style='color:#aaa;text-align:center;'>No available slots in the next 7 days.</p>"
    else:
        date_tabs_html = ""
        date_panels_html = ""
        first = True
        for day_str, slots in slots_by_date.items():
            try:
                day_dt = date.fromisoformat(day_str)
                day_label = day_dt.strftime("%a, %b %-d")
            except Exception:
                logger.debug("Could not format date label for %s, using raw string", day_str)
                day_label = day_str

            active_class = "date-tab active" if first else "date-tab"
            panel_style = "display:block;" if first else "display:none;"
            safe_day = html.escape(day_str)

            date_tabs_html += (
                f'<button class="{active_class}" onclick="showDay(\'{safe_day}\')" '
                f'id="tab-{safe_day}">{html.escape(day_label)}</button>\n'
            )

            panel_html = f'<div id="panel-{safe_day}" class="day-panel" style="{panel_style}">'
            for slot in slots:
                safe_start = html.escape(slot["start"])
                safe_end = html.escape(slot["end"])
                safe_start_full = html.escape(day_str + "T" + slot["start"])
                safe_end_full = html.escape(day_str + "T" + slot["end"])
                panel_html += (
                    f'<button class="slot-btn" '
                    f'onclick="selectSlot(\'{safe_day}\',\'{safe_start}\',\'{safe_end}\')" '
                    f'data-date="{safe_day}" data-start="{safe_start}" data-end="{safe_end}">'
                    f'{safe_start} – {safe_end}</button>\n'
                )

            panel_html += "</div>"
            date_panels_html += panel_html
            first = False

        slot_options_html = (
            f'<div class="date-tabs">{date_tabs_html}</div>'
            f'<div class="slot-panels">{date_panels_html}</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Book an Appointment — {safe_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: #0f0f0f;
      color: #e5e5e5;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
    }}
    .header {{
      background: {safe_color};
      padding: 24px 20px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 1.6rem;
      color: #fff;
      font-weight: 700;
    }}
    .header p {{
      margin: 6px 0 0;
      color: rgba(255,255,255,0.85);
      font-size: 0.95rem;
    }}
    .container {{
      max-width: 680px;
      margin: 32px auto;
      padding: 0 16px 48px;
    }}
    .card {{
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 12px;
      padding: 28px 24px;
      margin-bottom: 24px;
    }}
    .card h2 {{
      margin: 0 0 18px;
      font-size: 1.1rem;
      font-weight: 600;
      color: #fff;
    }}
    /* Date tabs */
    .date-tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .date-tab {{
      background: #252525;
      border: 1px solid #333;
      color: #ccc;
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.85rem;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }}
    .date-tab:hover {{ background: #2e2e2e; }}
    .date-tab.active {{
      background: {safe_color};
      border-color: {safe_color};
      color: #fff;
      font-weight: 600;
    }}
    /* Slot buttons */
    .slot-panels {{
      min-height: 60px;
    }}
    .day-panel {{
      display: none;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .slot-btn {{
      background: #252525;
      border: 1px solid #333;
      color: #ccc;
      border-radius: 8px;
      padding: 10px 16px;
      font-size: 0.88rem;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }}
    .slot-btn:hover {{ background: #2e2e2e; color: #fff; }}
    .slot-btn.selected {{
      background: {safe_color};
      border-color: {safe_color};
      color: #fff;
      font-weight: 600;
    }}
    /* Form */
    .form-group {{
      margin-bottom: 16px;
    }}
    label {{
      display: block;
      font-size: 0.85rem;
      color: #aaa;
      margin-bottom: 6px;
    }}
    input[type="text"],
    input[type="email"],
    input[type="tel"] {{
      width: 100%;
      background: #252525;
      border: 1px solid #333;
      border-radius: 8px;
      padding: 11px 14px;
      color: #e5e5e5;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.15s;
    }}
    input:focus {{ border-color: {safe_color}; }}
    /* Selected slot display */
    #selected-slot-display {{
      background: #252525;
      border: 1px solid #333;
      border-radius: 8px;
      padding: 11px 14px;
      color: #aaa;
      font-size: 0.9rem;
      margin-bottom: 20px;
    }}
    #selected-slot-display.chosen {{ color: #e5e5e5; border-color: {safe_color}; }}
    /* Submit button */
    .submit-btn {{
      width: 100%;
      background: {safe_color};
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 14px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s;
    }}
    .submit-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .submit-btn:hover:not(:disabled) {{ opacity: 0.88; }}
    /* Status messages */
    #status-msg {{
      margin-top: 16px;
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 0.9rem;
      display: none;
    }}
    #status-msg.success {{ background: #0d2e18; border: 1px solid #1a6b35; color: #5bd98a; }}
    #status-msg.error   {{ background: #2e0d0d; border: 1px solid #6b1a1a; color: #d98a8a; }}
    .powered-by {{
      text-align: center;
      margin-top: 32px;
      font-size: 0.78rem;
      color: #555;
    }}
    .powered-by a {{ color: #555; text-decoration: none; }}
    .powered-by a:hover {{ color: #888; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>{safe_name}</h1>
    <p>Book an appointment online</p>
  </div>

  <div class="container">
    {_build_service_type_section(service_types, safe_color)}
    <div class="card">
      <h2>Choose a Time</h2>
      {slot_options_html}
    </div>

    <div class="card">
      <h2>Your Details</h2>
      <p id="selected-slot-display">No time slot selected yet</p>

      <div class="form-group">
        <label for="f-name">Full Name</label>
        <input type="text" id="f-name" placeholder="Jane Smith" required />
      </div>
      <div class="form-group">
        <label for="f-email">Email Address</label>
        <input type="email" id="f-email" placeholder="jane@example.com" required />
      </div>
      <div class="form-group">
        <label for="f-phone">Phone Number</label>
        <input type="tel" id="f-phone" placeholder="+1 555 123 4567" />
      </div>

      <button class="submit-btn" id="submit-btn" onclick="submitBooking()" disabled>
        Confirm Appointment
      </button>
      <div id="status-msg"></div>
    </div>

    <div class="powered-by">
      Powered by <a href="https://agentnexlify.com" target="_blank" rel="noopener">AgentNexLiFy</a>
    </div>
  </div>

  <script>
    var selectedDate = null;
    var selectedStart = null;
    var selectedEnd = null;

    function selectService(radio) {{
      document.getElementById('f-service-type').value = radio.value;
      // Highlight the selected option
      document.querySelectorAll('.service-option').forEach(function(opt) {{
        opt.style.borderColor = '#333';
      }});
      radio.closest('.service-option').style.borderColor = '{safe_color}';
    }}

    function showDay(dateStr) {{
      // Deactivate all tabs
      var tabs = document.querySelectorAll('.date-tab');
      tabs.forEach(function(t) {{ t.classList.remove('active'); }});
      // Hide all panels
      var panels = document.querySelectorAll('.day-panel');
      panels.forEach(function(p) {{ p.style.display = 'none'; }});

      // Activate clicked tab and panel
      var tab = document.getElementById('tab-' + dateStr);
      if (tab) {{ tab.classList.add('active'); }}
      var panel = document.getElementById('panel-' + dateStr);
      if (panel) {{ panel.style.display = 'flex'; }}
    }}

    // Show first panel as flex on load
    (function() {{
      var firstPanel = document.querySelector('.day-panel');
      if (firstPanel) {{ firstPanel.style.display = 'flex'; }}
    }})();

    function selectSlot(dateStr, startTime, endTime) {{
      // Clear previous selection
      var allSlots = document.querySelectorAll('.slot-btn');
      allSlots.forEach(function(b) {{ b.classList.remove('selected'); }});

      // Mark this one selected
      var clicked = document.querySelector(
        '.slot-btn[data-date="' + dateStr + '"][data-start="' + startTime + '"]'
      );
      if (clicked) {{ clicked.classList.add('selected'); }}

      selectedDate = dateStr;
      selectedStart = startTime;
      selectedEnd = endTime;

      var display = document.getElementById('selected-slot-display');
      display.textContent = dateStr + ' at ' + startTime + ' – ' + endTime;
      display.classList.add('chosen');

      document.getElementById('submit-btn').disabled = false;
    }}

    function submitBooking() {{
      var name  = document.getElementById('f-name').value.trim();
      var email = document.getElementById('f-email').value.trim();
      var phone = document.getElementById('f-phone').value.trim();

      if (!name || !email) {{
        showStatus('Please fill in your name and email.', 'error');
        return;
      }}
      if (!selectedDate || !selectedStart || !selectedEnd) {{
        showStatus('Please select a time slot.', 'error');
        return;
      }}

      var btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.textContent = 'Booking...';

      var serviceTypeId = (document.getElementById('f-service-type') || {{}}).value || null;

      fetch('/api/v1/book/{slug}/submit', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          name: name,
          email: email,
          phone: phone,
          date: selectedDate,
          start_time: selectedStart,
          end_time: selectedEnd,
          service_type_id: serviceTypeId
        }})
      }})
      .then(function(resp) {{ return resp.json(); }})
      .then(function(data) {{
        if (data.success) {{
          showStatus(data.message || 'Appointment booked!', 'success');
          btn.textContent = 'Booked!';
          // Disable slot buttons to prevent double-submit
          document.querySelectorAll('.slot-btn').forEach(function(b) {{ b.disabled = true; }});
        }} else {{
          showStatus(data.detail || 'Something went wrong. Please try again.', 'error');
          btn.disabled = false;
          btn.textContent = 'Confirm Appointment';
        }}
      }})
      .catch(function(err) {{
        showStatus('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.textContent = 'Confirm Appointment';
      }});
    }}

    function showStatus(msg, type) {{
      var el = document.getElementById('status-msg');
      el.textContent = msg;
      el.className = type;
      el.style.display = 'block';
    }}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# GET /api/v1/book/{business_slug}
# ---------------------------------------------------------------------------


@router.get("/{business_slug}", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def booking_page(request: Request, business_slug: str):
    """Return a server-rendered HTML booking page for a business."""
    tenant = _lookup_tenant_by_slug(business_slug)
    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "Business"

    primary_color = _fetch_widget_color(tenant_id)

    # Fetch service types for this tenant
    service_types = []
    try:
        db = get_supabase()
        st_result = (
            db.table("service_types")
            .select("id, name, duration_minutes, description, price")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        service_types = st_result.data or []
    except Exception:
        logger.warning("Could not fetch service types for tenant %s", tenant_id, exc_info=True)

    # Build available slots for the next 7 days
    today = date.today()
    slots_by_date: dict[str, list[dict]] = {}
    for i in range(7):
        target = today + timedelta(days=i)
        try:
            day_slots = generate_available_slots(tenant_id, target)
        except Exception:
            logger.warning(
                "Could not generate slots for tenant %s on %s",
                tenant_id,
                target.isoformat(),
                exc_info=True,
            )
            day_slots = []

        if day_slots:
            slots_by_date[target.isoformat()] = day_slots

    page_html = _build_booking_page_html(
        business_name=business_name,
        primary_color=primary_color,
        slug=html.escape(business_slug),
        slots_by_date=slots_by_date,
        service_types=service_types,
    )
    return HTMLResponse(content=page_html, status_code=200)


# ---------------------------------------------------------------------------
# POST /api/v1/book/{business_slug}/submit
# ---------------------------------------------------------------------------


@router.post("/{business_slug}/submit")
@limiter.limit("5/minute")
async def booking_submit(
    request: Request,
    business_slug: str,
    body: BookingSubmitRequest,
):
    """Accept a booking submission and create an appointment + lead record."""
    tenant = _lookup_tenant_by_slug(business_slug)
    tenant_id = tenant["id"]
    business_name = tenant.get("business_name") or "Business"

    # Basic field validation
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not body.date or not body.start_time or not body.end_time:
        raise HTTPException(status_code=400, detail="Date and time slot are required")

    # Build ISO timestamps for the slot.
    # The page always submits local (business-timezone) HH:MM strings.
    # We store as naive ISO strings; create_appointment stores them in appointments.start_time.
    start_iso = f"{body.date}T{body.start_time}:00"
    end_iso = f"{body.date}T{body.end_time}:00"

    # Validate slot is still available (prevent double-booking)
    if not _slot_available(tenant_id, date.fromisoformat(body.date), start_iso, end_iso):
        raise HTTPException(
            status_code=409,
            detail="That time slot is no longer available. Please choose another.",
        )

    db = get_supabase()

    # Resolve service type name if provided
    service_note = "Booked via public booking page"
    if body.service_type_id:
        try:
            st_row = (
                db.table("service_types")
                .select("name, duration_minutes")
                .eq("id", body.service_type_id)
                .eq("tenant_id", tenant_id)
                .limit(1)
                .execute()
            )
            if st_row.data:
                service_note = f"Service: {st_row.data[0]['name']} ({st_row.data[0]['duration_minutes']} min) — Booked via public booking page"
        except Exception:
            logger.warning("Could not look up service type %s", body.service_type_id, exc_info=True)

    # Create appointment
    try:
        appt_result = db.table("appointments").insert({
            "tenant_id": tenant_id,
            "customer_name": body.name.strip(),
            "customer_email": body.email.strip(),
            "customer_phone": body.phone.strip() if body.phone else None,
            "start_time": start_iso,
            "end_time": end_iso,
            "status": "confirmed",
            "notes": service_note,
        }).execute()
    except Exception:
        logger.exception(
            "Failed to create appointment for tenant %s slug %s", tenant_id, business_slug
        )
        raise HTTPException(status_code=500, detail="Could not create appointment. Please try again.")

    if not appt_result.data:
        logger.error("Appointment insert returned no data for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Could not create appointment. Please try again.")

    appointment = appt_result.data[0]
    appointment_id = appointment["id"]

    # Create or find lead (uses client_id, not tenant_id — critical rule)
    lead_id: str | None = None
    try:
        lead_id = link_appointment_to_lead(tenant_id, {
            "customer_name": body.name.strip(),
            "customer_email": body.email.strip(),
            "customer_phone": body.phone.strip() if body.phone else None,
        })
        if lead_id:
            db.table("appointments").update({"lead_id": lead_id}).eq("id", appointment_id).execute()
    except Exception:
        logger.warning(
            "Could not link appointment %s to lead for tenant %s",
            appointment_id,
            tenant_id,
            exc_info=True,
        )

    # Send confirmation email to customer (best-effort)
    try:
        confirmation_html = (
            f"<h2>Appointment Confirmed</h2>"
            f"<p>Hi {html.escape(body.name.strip())},</p>"
            f"<p>Your appointment with <strong>{html.escape(business_name)}</strong> has been confirmed.</p>"
            f"<ul>"
            f"<li><strong>Date:</strong> {html.escape(body.date)}</li>"
            f"<li><strong>Time:</strong> {html.escape(body.start_time)} – {html.escape(body.end_time)}</li>"
            f"</ul>"
            f"<p>If you need to cancel or reschedule, please contact us directly.</p>"
        )
        await send_email(
            to=body.email.strip(),
            subject=f"Appointment Confirmed — {business_name}",
            body_html=confirmation_html,
            tenant_id=tenant_id,
            lead_id=lead_id or "",
        )
    except Exception:
        logger.warning(
            "Could not send confirmation email for appointment %s", appointment_id, exc_info=True
        )

    # Fire webhook event (best-effort, non-blocking)
    try:
        fire_event_background(
            tenant_id=tenant_id,
            event="appointment.booked",
            data={
                "appointment_id": appointment_id,
                "customer_name": body.name.strip(),
                "customer_email": body.email.strip(),
                "customer_phone": body.phone.strip() if body.phone else None,
                "start_time": start_iso,
                "end_time": end_iso,
                "lead_id": lead_id,
                "source": "public_booking_page",
            },
        )
    except Exception:
        logger.warning(
            "Could not fire appointment.booked webhook for tenant %s", tenant_id, exc_info=True
        )

    return JSONResponse(
        content={"success": True, "message": "Appointment booked! You'll receive a confirmation email shortly."},
        status_code=200,
    )
