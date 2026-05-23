"""Form rendering, validation, and lead extraction — pure logic.

Router stays thin: HTTP + auth + Pydantic + DB calls only.
This module owns:
  - Public token generation
  - Required-field validation
  - Auto-lead field extraction (name/email/phone)
  - HTML embed rendering (form-as-iframe page)
"""

import html
import secrets


def generate_public_token() -> str:
    """Generate a short, URL-safe public token for form embedding."""
    return f"frm_{secrets.token_urlsafe(24)}"


def validate_required_fields(fields_spec: list[dict], submitted_data: dict) -> list[str]:
    """Return labels (or IDs) of required fields missing/blank in the submission."""
    missing: list[str] = []
    for field_def in fields_spec or []:
        if not field_def.get("required"):
            continue
        field_id = field_def.get("id", "")
        value = submitted_data.get(field_id)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field_def.get("label") or field_id)
    return missing


def extract_lead_fields(submitted_data: dict, fields_spec: list[dict]) -> dict:
    """Sniff name/email/phone out of a submission using field type + ID heuristics.

    Returns dict with keys 'name', 'email', 'phone' — any may be None.
    """
    field_type_map = {f.get("id", ""): f.get("type", "text") for f in (fields_spec or [])}

    lead_name: str | None = None
    lead_email: str | None = None
    lead_phone: str | None = None

    for field_id, value in (submitted_data or {}).items():
        if not value or not isinstance(value, str):
            continue
        value = value.strip()
        if not value:
            continue

        ftype = field_type_map.get(field_id, "text")
        field_lower = field_id.lower()

        if ftype == "email" or field_lower in ("email", "email_address", "e-mail"):
            lead_email = value
        elif ftype == "phone" or field_lower in ("phone", "phone_number", "mobile", "tel"):
            lead_phone = value
        elif field_lower in ("name", "full_name", "fullname", "your_name", "customer_name"):
            lead_name = value

    return {"name": lead_name, "email": lead_email, "phone": lead_phone}


def _render_field(field: dict) -> str:
    """Render a single form field as escaped HTML. Returns '' for unknown types."""
    fid = html.escape(field.get("id", ""))
    flabel = html.escape(field.get("label", ""))
    ftype = field.get("type", "text")
    freq = field.get("required", False)
    fplaceholder = html.escape(field.get("placeholder") or "")
    req_attr = "required" if freq else ""
    req_mark = ' <span style="color:#ef4444">*</span>' if freq else ""

    if ftype in ("text", "email", "phone", "number", "date"):
        input_type = {"phone": "tel"}.get(ftype, ftype)
        return (
            f'<div class="field"><label>{flabel}{req_mark}</label>'
            f'<input type="{input_type}" name="{fid}" placeholder="{fplaceholder}" {req_attr}/></div>'
        )
    if ftype == "textarea":
        return (
            f'<div class="field"><label>{flabel}{req_mark}</label>'
            f'<textarea name="{fid}" placeholder="{fplaceholder}" rows="4" {req_attr}></textarea></div>'
        )
    if ftype in ("select", "radio"):
        options = field.get("options") or []
        if ftype == "select":
            opts_html = '<option value="">Select...</option>'
            for o in options:
                ov = html.escape(str(o))
                opts_html += f'<option value="{ov}">{ov}</option>'
            return (
                f'<div class="field"><label>{flabel}{req_mark}</label>'
                f'<select name="{fid}" {req_attr}>{opts_html}</select></div>'
            )
        radios = ""
        for o in options:
            ov = html.escape(str(o))
            radios += (
                f'<label class="radio">'
                f'<input type="radio" name="{fid}" value="{ov}" {req_attr}/> {ov}</label>'
            )
        return (
            f'<div class="field"><label>{flabel}{req_mark}</label>'
            f'<div class="radio-group">{radios}</div></div>'
        )
    if ftype == "checkbox":
        return (
            f'<div class="field checkbox"><label>'
            f'<input type="checkbox" name="{fid}" value="true" {req_attr}/> {flabel}</label></div>'
        )
    return ""


def render_form_embed_html(
    form: dict,
    *,
    default_theme: str = "#7c3aed",
    default_submit_text: str = "Submit",
    default_success_msg: str = "Thank you for your submission!",
) -> str:
    """Render a complete self-contained iframe-embeddable HTML page for the form.

    All user-controlled strings are HTML-escaped at boundaries.
    """
    fields = form.get("fields_json") or []
    settings = form.get("settings_json") or {}
    theme_color = html.escape(settings.get("theme_color", default_theme))
    submit_text = html.escape(settings.get("submit_button_text", default_submit_text))
    form_name = html.escape(form.get("name", "Form"))
    form_desc = html.escape(form.get("description") or "")
    success_message_js = repr(form.get("success_message") or default_success_msg)

    field_html_parts = [_render_field(f) for f in fields]
    fields_html = "\n".join(part for part in field_html_parts if part)

    desc_html = f"<p class='desc'>{form_desc}</p>" if form_desc else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{form_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#1e293b;padding:24px}}
.form-container{{max-width:560px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:32px}}
h1{{font-size:1.5rem;margin-bottom:4px}}
.desc{{color:#64748b;margin-bottom:24px;font-size:.9rem}}
.field{{margin-bottom:16px}}
.field label{{display:block;font-weight:600;font-size:.85rem;margin-bottom:6px;color:#334155}}
.field input,.field textarea,.field select{{width:100%;padding:10px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:.9rem;transition:border .15s}}
.field input:focus,.field textarea:focus,.field select:focus{{outline:none;border-color:{theme_color};box-shadow:0 0 0 3px {theme_color}22}}
.checkbox label{{font-weight:normal;display:flex;align-items:center;gap:8px;cursor:pointer}}
.radio-group{{display:flex;flex-direction:column;gap:6px}}
.radio label{{font-weight:normal;display:flex;align-items:center;gap:6px;cursor:pointer}}
.submit-btn{{width:100%;padding:12px;border:none;border-radius:8px;background:{theme_color};color:#fff;font-size:1rem;font-weight:600;cursor:pointer;margin-top:8px;transition:opacity .15s}}
.submit-btn:hover{{opacity:.9}}
.submit-btn:disabled{{opacity:.5;cursor:wait}}
.success{{text-align:center;padding:40px 20px;color:#16a34a;font-size:1.1rem}}
.error{{color:#ef4444;font-size:.85rem;margin-top:8px}}
.powered{{text-align:center;margin-top:16px;font-size:.75rem;color:#94a3b8}}
.powered a{{color:#94a3b8;text-decoration:none}}
</style></head><body>
<div class="form-container">
<h1>{form_name}</h1>
{desc_html}
<form id="publicForm">
{fields_html}
<button type="submit" class="submit-btn" id="submitBtn">{submit_text}</button>
<div id="errorMsg" class="error" style="display:none"></div>
</form>
<div id="successMsg" class="success" style="display:none"></div>
</div>
<div class="powered">Powered by <a href="https://agentnexlify.com" target="_blank">AgentNexLiFy</a></div>
<script>
document.getElementById("publicForm").addEventListener("submit",async function(e){{
e.preventDefault();
const btn=document.getElementById("submitBtn");
const err=document.getElementById("errorMsg");
btn.disabled=true;err.style.display="none";
const fd=new FormData(this);
const data={{}};
fd.forEach((v,k)=>{{if(data[k]){{if(!Array.isArray(data[k]))data[k]=[data[k]];data[k].push(v)}}else data[k]=v}});
try{{
const r=await fetch(window.location.href.replace("/embed","/submit"),{{
method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{data:data}})
}});
if(!r.ok)throw new Error((await r.json().catch(()=>({{}}))).detail||"Submission failed");
document.getElementById("publicForm").style.display="none";
document.getElementById("successMsg").style.display="block";
document.getElementById("successMsg").textContent={success_message_js};
}}catch(ex){{err.textContent=ex.message;err.style.display="block"}}
finally{{btn.disabled=false}}
}});
</script></body></html>"""
