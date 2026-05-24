"""Public booking page — HTML rendering helpers.

Pure string builders for booking and reschedule pages. No DB, no auth.
"""

import html
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)


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


def build_booking_page_html(
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
    .header {{ background: {safe_color}; padding: 24px 20px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 1.6rem; color: #fff; font-weight: 700; }}
    .header p {{ margin: 6px 0 0; color: rgba(255,255,255,0.85); font-size: 0.95rem; }}
    .container {{ max-width: 680px; margin: 32px auto; padding: 0 16px 48px; }}
    .card {{ background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 28px 24px; margin-bottom: 24px; }}
    .card h2 {{ margin: 0 0 18px; font-size: 1.1rem; font-weight: 600; color: #fff; }}
    .date-tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
    .date-tab {{ background: #252525; border: 1px solid #333; color: #ccc; border-radius: 8px; padding: 8px 14px; font-size: 0.85rem; cursor: pointer; transition: background 0.15s, border-color 0.15s, color 0.15s; }}
    .date-tab:hover {{ background: #2e2e2e; }}
    .date-tab.active {{ background: {safe_color}; border-color: {safe_color}; color: #fff; font-weight: 600; }}
    .slot-panels {{ min-height: 60px; }}
    .day-panel {{ display: none; flex-wrap: wrap; gap: 8px; }}
    .slot-btn {{ background: #252525; border: 1px solid #333; color: #ccc; border-radius: 8px; padding: 10px 16px; font-size: 0.88rem; cursor: pointer; transition: background 0.15s, border-color 0.15s, color 0.15s; }}
    .slot-btn:hover {{ background: #2e2e2e; color: #fff; }}
    .slot-btn.selected {{ background: {safe_color}; border-color: {safe_color}; color: #fff; font-weight: 600; }}
    .form-group {{ margin-bottom: 16px; }}
    label {{ display: block; font-size: 0.85rem; color: #aaa; margin-bottom: 6px; }}
    input[type="text"], input[type="email"], input[type="tel"] {{ width: 100%; background: #252525; border: 1px solid #333; border-radius: 8px; padding: 11px 14px; color: #e5e5e5; font-size: 0.95rem; outline: none; transition: border-color 0.15s; }}
    input:focus {{ border-color: {safe_color}; }}
    #selected-slot-display {{ background: #252525; border: 1px solid #333; border-radius: 8px; padding: 11px 14px; color: #aaa; font-size: 0.9rem; margin-bottom: 20px; }}
    #selected-slot-display.chosen {{ color: #e5e5e5; border-color: {safe_color}; }}
    .submit-btn {{ width: 100%; background: {safe_color}; color: #fff; border: none; border-radius: 8px; padding: 14px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }}
    .submit-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .submit-btn:hover:not(:disabled) {{ opacity: 0.88; }}
    #status-msg {{ margin-top: 16px; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem; display: none; }}
    #status-msg.success {{ background: #0d2e18; border: 1px solid #1a6b35; color: #5bd98a; }}
    #status-msg.error   {{ background: #2e0d0d; border: 1px solid #6b1a1a; color: #d98a8a; }}
    .powered-by {{ text-align: center; margin-top: 32px; font-size: 0.78rem; color: #555; }}
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
      <button class="submit-btn" id="submit-btn" onclick="submitBooking()" disabled>Confirm Appointment</button>
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
      document.querySelectorAll('.service-option').forEach(function(opt) {{ opt.style.borderColor = '#333'; }});
      radio.closest('.service-option').style.borderColor = '{safe_color}';
    }}
    function showDay(dateStr) {{
      document.querySelectorAll('.date-tab').forEach(function(t) {{ t.classList.remove('active'); }});
      document.querySelectorAll('.day-panel').forEach(function(p) {{ p.style.display = 'none'; }});
      var tab = document.getElementById('tab-' + dateStr);
      if (tab) {{ tab.classList.add('active'); }}
      var panel = document.getElementById('panel-' + dateStr);
      if (panel) {{ panel.style.display = 'flex'; }}
    }}
    (function() {{
      var firstPanel = document.querySelector('.day-panel');
      if (firstPanel) {{ firstPanel.style.display = 'flex'; }}
    }})();
    function selectSlot(dateStr, startTime, endTime) {{
      document.querySelectorAll('.slot-btn').forEach(function(b) {{ b.classList.remove('selected'); }});
      var clicked = document.querySelector('.slot-btn[data-date="' + dateStr + '"][data-start="' + startTime + '"]');
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
      if (!name || !email) {{ showStatus('Please fill in your name and email.', 'error'); return; }}
      if (!selectedDate || !selectedStart || !selectedEnd) {{ showStatus('Please select a time slot.', 'error'); return; }}
      var btn = document.getElementById('submit-btn');
      btn.disabled = true;
      btn.textContent = 'Booking...';
      var serviceTypeId = (document.getElementById('f-service-type') || {{}}).value || null;
      fetch('/api/v1/book/{slug}/submit', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          name: name, email: email, phone: phone,
          date: selectedDate, start_time: selectedStart, end_time: selectedEnd,
          service_type_id: serviceTypeId
        }})
      }})
      .then(function(resp) {{ return resp.json(); }})
      .then(function(data) {{
        if (data.success) {{
          showStatus(data.message || 'Appointment booked!', 'success');
          btn.textContent = 'Booked!';
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


def build_reschedule_page_html(
    appointment_id: str,
    token: str,
    biz_name: str,
    current_dt_label: str,
    slots_by_day: dict[str, list[dict]],
) -> str:
    """Return the reschedule page HTML for a customer appointment.

    Uses createElement + textContent for option lists (no innerHTML) — safe DOM
    even though SLOTS payload is server-controlled.
    """
    safe_biz = html.escape(biz_name)
    safe_current = html.escape(current_dt_label)
    slots_json = json.dumps(slots_by_day)
    safe_appt = html.escape(appointment_id)
    safe_token = html.escape(token)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reschedule Appointment - {safe_biz}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f9fafb; margin: 0; padding: 20px; color: #1f2937; }}
  .container {{ max-width: 500px; margin: 40px auto; background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  h1 {{ font-size: 1.5rem; margin: 0 0 8px; }}
  .current {{ background: #fef3c7; padding: 12px 16px; border-radius: 8px; margin: 16px 0; font-size: 0.9rem; }}
  label {{ display: block; font-weight: 600; margin: 16px 0 6px; }}
  select, button {{ width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 1rem; }}
  button {{ background: #2563eb; color: #fff; border: none; cursor: pointer; font-weight: 600; margin-top: 16px; }}
  button:hover {{ background: #1d4ed8; }}
  button:disabled {{ background: #93c5fd; cursor: not-allowed; }}
  .success {{ background: #dcfce7; padding: 16px; border-radius: 8px; color: #166534; text-align: center; }}
  .error {{ background: #fee2e2; padding: 12px; border-radius: 8px; color: #991b1b; margin-top: 12px; }}
  .cancel-link {{ display: block; text-align: center; margin-top: 16px; color: #ef4444; cursor: pointer; font-size: 0.9rem; }}
</style>
</head><body>
<div class="container">
  <h1>Reschedule Your Appointment</h1>
  <p style="color:#6b7280;">{safe_biz}</p>
  <div class="current">Current: <strong>{safe_current}</strong></div>
  <div id="form">
    <label for="day">Select a new date:</label>
    <select id="day" onchange="updateSlots()"><option value="">Choose a date...</option></select>
    <label for="slot">Select a time:</label>
    <select id="slot"><option value="">Choose a time...</option></select>
    <button id="submitBtn" onclick="submitReschedule()" disabled>Reschedule Appointment</button>
    <div id="error" class="error" style="display:none;"></div>
  </div>
  <div id="success" class="success" style="display:none;">
    Your appointment has been rescheduled! You'll receive a confirmation email shortly.
  </div>
  <div class="cancel-link" onclick="cancelAppointment()">Cancel this appointment instead</div>
</div>
<script>
const SLOTS = {slots_json};
const APPT_ID = "{safe_appt}";
const TOKEN = "{safe_token}";
const daySelect = document.getElementById('day');
const slotSelect = document.getElementById('slot');
const submitBtn = document.getElementById('submitBtn');

function addOption(sel, value, text) {{
  const opt = document.createElement('option');
  opt.value = value;
  opt.textContent = text;
  sel.appendChild(opt);
}}

function resetSelect(sel, placeholder) {{
  while (sel.firstChild) sel.removeChild(sel.firstChild);
  addOption(sel, '', placeholder);
}}

Object.keys(SLOTS).sort().forEach(function(d) {{
  const dt = new Date(d + 'T12:00:00');
  const label = dt.toLocaleDateString('en-US', {{ weekday: 'long', month: 'long', day: 'numeric' }});
  addOption(daySelect, d, label);
}});

function updateSlots() {{
  const day = daySelect.value;
  resetSelect(slotSelect, 'Choose a time...');
  submitBtn.disabled = true;
  if (!day || !SLOTS[day]) return;
  SLOTS[day].forEach(function(s, i) {{ addOption(slotSelect, String(i), s.label); }});
  slotSelect.onchange = function() {{ submitBtn.disabled = !slotSelect.value; }};
}}

async function submitReschedule() {{
  const day = daySelect.value;
  const idx = parseInt(slotSelect.value);
  if (!day || isNaN(idx)) return;
  const slot = SLOTS[day][idx];
  submitBtn.disabled = true;
  submitBtn.textContent = 'Rescheduling...';
  document.getElementById('error').style.display = 'none';
  try {{
    const res = await fetch('/api/v1/book/reschedule/' + APPT_ID + '/submit', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ token: TOKEN, new_start: slot.start, new_end: slot.end }}),
    }});
    const data = await res.json();
    if (res.ok) {{
      document.getElementById('form').style.display = 'none';
      document.getElementById('success').style.display = 'block';
      document.querySelector('.cancel-link').style.display = 'none';
    }} else {{
      document.getElementById('error').textContent = data.detail || 'Failed to reschedule.';
      document.getElementById('error').style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Reschedule Appointment';
    }}
  }} catch(e) {{
    document.getElementById('error').textContent = 'Network error. Please try again.';
    document.getElementById('error').style.display = 'block';
    submitBtn.disabled = false;
    submitBtn.textContent = 'Reschedule Appointment';
  }}
}}

async function cancelAppointment() {{
  if (!confirm('Are you sure you want to cancel this appointment?')) return;
  try {{
    const res = await fetch('/api/v1/book/reschedule/' + APPT_ID + '/cancel', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ token: TOKEN }}),
    }});
    if (res.ok) {{
      document.getElementById('form').style.display = 'none';
      document.querySelector('.cancel-link').style.display = 'none';
      document.getElementById('success').textContent = 'Your appointment has been cancelled.';
      document.getElementById('success').style.display = 'block';
    }}
  }} catch(e) {{}}
}}
</script>
</body></html>"""
