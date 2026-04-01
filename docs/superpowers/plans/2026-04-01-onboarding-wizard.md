# Onboarding Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an SMB owner go from zero to a working AI chat widget embed code in under 5 minutes, with no developer involvement.

**Architecture:** Six-step wizard (`/onboarding` route) builds `wizardData` in `sessionStorage` across steps, makes two backend calls (generate-kb at step 3, complete at step 5), and redirects to Stripe Checkout for paid plans before returning to step 6 (embed code). Backend: one new endpoint (`generate-kb`), one extended endpoint (`complete`), one patched endpoint (Stripe `success_url`), one updated function (`_build_system_prompt`). Frontend: shell page + six step components + one preview iframe component.

**Tech Stack:** FastAPI, Pydantic, Supabase Python client, Anthropic `claude-sonnet-4-6`, Stripe Checkout, React 18, React Router v6, `sessionStorage`.

---

## File Map

### Backend — New / Modified
| File | Action | Change |
|------|--------|--------|
| `migrations/076_widget_knowledge_base.sql` | **Create** | `ALTER TABLE widget_configs ADD COLUMN knowledge_base TEXT` |
| `backend/routers/onboarding.py` | **Modify** | Add `GenerateKbRequest/Response` models + `POST /{tenant_id}/generate-kb` endpoint; extend `OnboardingCompleteRequest` with widget + FAQ fields; handle them in `complete_onboarding` |
| `backend/routers/auth.py` | **Modify** | `billing_checkout`: accept `source` in body; if `source == "wizard"` set `success_url` to `/onboarding?step=6&...` |
| `backend/routers/widget_helpers.py` | **Modify** | `_build_system_prompt`: add `knowledge_base: str | None = None` param; inject as a block in the returned prompt |
| `backend/routers/widget_chat.py` | **Modify** | Pass `knowledge_base=widget.get("knowledge_base") or None` to `_build_system_prompt` |

### Frontend — New / Modified
| File | Action | Change |
|------|--------|--------|
| `frontend/public/widget-preview.html` | **Create** | Static HTML; reads `?api_key=` from URL; loads widget JS |
| `frontend/src/utils/api/onboarding.js` | **Create** | `generateKb()`, `completeOnboarding()`, `checkoutForWizard()` |
| `frontend/src/pages/OnboardingWizardPage.jsx` | **Create** | Shell: step state, `wizardData`, progress bar, step render switch |
| `frontend/src/pages/wizard/WizardStepBusiness.jsx` | **Create** | Step 1: business info form |
| `frontend/src/pages/wizard/WizardStepServices.jsx` | **Create** | Step 2: services chips + FAQ pairs |
| `frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx` | **Create** | Step 3: call generate-kb, show result |
| `frontend/src/pages/wizard/WizardStepCustomize.jsx` | **Create** | Step 4: bot name, color, greeting, preview iframe |
| `frontend/src/pages/wizard/WizardStepPlan.jsx` | **Create** | Step 5: plan cards + Stripe redirect |
| `frontend/src/pages/wizard/WizardStepEmbed.jsx` | **Create** | Step 6: embed code + copy button |
| `frontend/src/main.jsx` | **Modify** | Add `/onboarding` route (lazy-load `OnboardingWizardPage`) |
| `frontend/src/pages/SignupPage.jsx` | **Modify** | After successful registration: redirect to `/onboarding` instead of `/dashboard` |

---

## Task 1: Migration 076 — `widget_configs.knowledge_base`

**Files:**
- Create: `migrations/076_widget_knowledge_base.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- 076_widget_knowledge_base.sql
-- Add AI-generated knowledge base storage to widget_configs.
-- teaser_message (071), custom_instructions (072), email_sequences (073),
-- lead_captured (074), teaser_enabled/teaser_delay (075) are all taken.

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS knowledge_base TEXT;

COMMENT ON COLUMN widget_configs.knowledge_base IS
  'AI-generated markdown knowledge base produced during onboarding wizard. '
  'Injected into the chat system prompt when present. Editable post-onboarding.';
```

Save to: `migrations/076_widget_knowledge_base.sql`

- [ ] **Step 2: Apply via Supabase MCP**

Use `mcp__supabase__apply_migration` with name `076_widget_knowledge_base` and the SQL above.

- [ ] **Step 3: Verify the column exists**

Run SQL: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'widget_configs' AND column_name = 'knowledge_base';`

Expected: one row — `knowledge_base | text`

- [ ] **Step 4: Commit**

```bash
git add migrations/076_widget_knowledge_base.sql
git commit -m "feat: migration 076 — add knowledge_base to widget_configs"
```

---

## Task 2: Backend — `generate-kb` endpoint

**Files:**
- Modify: `backend/routers/onboarding.py`

- [ ] **Step 1: Add Pydantic models after `OnboardingStatusResponse` (line ~65)**

Find the block ending with `OnboardingStatusResponse` and add immediately after:

```python
class FaqInput(BaseModel):
    question: str = Field(..., max_length=500)
    answer: str = Field(..., max_length=2000)


class GenerateKbRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., max_length=100)
    phone: str | None = Field(None, max_length=30)
    website_url: str | None = Field(None, max_length=500)
    services: list[str] = Field(default_factory=list)
    faqs: list[FaqInput] = Field(default_factory=list)
    hours: dict[str, Any] | None = None


class GenerateKbResponse(BaseModel):
    knowledge_base: str | None
    generated: bool
```

- [ ] **Step 2: Add the endpoint after `complete_onboarding` (before the status endpoint)**

```python
@router.post("/{tenant_id}/generate-kb", response_model=GenerateKbResponse)
@limiter.limit("5/minute")
async def generate_knowledge_base(
    request: Request,
    tenant_id: str,
    req: GenerateKbRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Generate an AI knowledge base from onboarding answers and persist it."""
    _verify_tenant(claims, tenant_id)

    # Format hours as human-readable text for the prompt
    hours_text = "Not specified"
    if req.hours:
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        lines = []
        tz = req.hours.get("timezone", "")
        for day in days:
            day_cfg = req.hours.get(day)
            if not day_cfg:
                continue
            if day_cfg.get("enabled") or (day_cfg.get("open") and day_cfg.get("close")):
                open_t = day_cfg.get("open") or day_cfg.get("start", "09:00")
                close_t = day_cfg.get("close") or day_cfg.get("end", "17:00")
                lines.append(f"  {day.capitalize()}: {open_t} – {close_t}")
            else:
                lines.append(f"  {day.capitalize()}: Closed")
        hours_text = "\n".join(lines)
        if tz:
            hours_text += f"\n  Timezone: {tz}"

    services_text = ", ".join(req.services) if req.services else "Not specified"
    faqs_text = "\n".join(
        f"Q: {faq.question}\nA: {faq.answer}" for faq in req.faqs
    ) if req.faqs else "None provided"

    prompt = f"""You are setting up an AI chat assistant for a local business. Generate a concise, structured knowledge base in markdown that the AI will use to answer customer questions.

Business: {req.business_name}
Industry: {req.business_type}
Location: {req.city}
Phone: {req.phone or "Not provided"}
Website: {req.website_url or "Not provided"}
Services offered: {services_text}

Business hours:
{hours_text}

The business owner provided these common customer questions and answers:
{faqs_text}

Generate a knowledge base with these sections (use ## headers):
- About (2-3 sentences describing the business)
- Services (bullet list with brief descriptions)
- Hours & Location
- FAQs (expand the provided Q&As into polished, customer-friendly answers; add 2-3 additional FAQs that are typical for this industry if fewer than 3 were provided)
- Contact

Keep it concise. Do not invent facts not supported by the input. Do not add markdown formatting beyond headers and bullet lists."""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )
        kb_text = message.content[0].text.strip()
    except Exception:
        logger.error("KB generation failed for tenant %s", tenant_id, exc_info=True)
        return GenerateKbResponse(knowledge_base=None, generated=False)

    # Persist to widget_configs
    try:
        db = get_supabase()
        db.table("widget_configs").update({"knowledge_base": kb_text}).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error("Failed to persist knowledge_base for tenant %s", tenant_id, exc_info=True)
        # Still return the generated text — frontend can retry or proceed without persistence

    return GenerateKbResponse(knowledge_base=kb_text, generated=True)
```

- [ ] **Step 3: Verify imports** — `onboarding.py` already imports `anthropic` and `settings`. Confirm at top of file:

```python
import anthropic
from backend.config import settings
```

Both are already present (lines 19 and 23). No changes needed.

- [ ] **Step 4: Smoke-test the module loads**

```bash
cd /home/aidan/agentnexlify
python -c "from backend.routers.onboarding import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/onboarding.py
git commit -m "feat: add generate-kb endpoint to onboarding router"
```

---

## Task 3: Backend — extend `OnboardingCompleteRequest`

**Files:**
- Modify: `backend/routers/onboarding.py`

- [ ] **Step 1: Extend `OnboardingCompleteRequest`** (currently lines 38–45)

Replace the existing model with:

```python
class OnboardingCompleteRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: str = Field(..., min_length=1, max_length=50)
    city: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)
    website_url: str | None = Field(None, max_length=500)
    hours: dict[str, Any] | None = None
    services: list[str] | None = None
    # Wizard additions
    widget_bot_name: str | None = Field(None, max_length=100)
    widget_primary_color: str | None = Field(None, max_length=20)
    widget_greeting_message: str | None = Field(None, max_length=500)
    widget_position: str | None = Field(None, pattern=r"^(bottom-right|bottom-left)$")
    faqs: list[FaqInput] | None = None  # FaqInput defined in Task 2
```

- [ ] **Step 2: Handle widget fields in `complete_onboarding`**

Find the section that updates `tenants` (currently ends around line 215). After `configured["business_info"] = True`, add a new section to handle widget customization:

```python
    # 4b. Update widget config with customization from wizard
    widget_updates: dict[str, Any] = {}
    if req.widget_bot_name:
        widget_updates["bot_name"] = req.widget_bot_name
    if req.widget_primary_color:
        widget_updates["primary_color"] = req.widget_primary_color
    if req.widget_greeting_message:
        widget_updates["greeting_message"] = req.widget_greeting_message
    if req.widget_position:
        widget_updates["position"] = req.widget_position

    if widget_updates:
        try:
            db.table("widget_configs").update(widget_updates).eq("tenant_id", tenant_id).execute()
        except Exception:
            logger.error("Failed to update widget_configs during onboarding for %s", tenant_id, exc_info=True)
```

Add this block immediately after the `configured["business_info"] = True` line and before the hours section.

- [ ] **Step 3: Handle FAQ insertion** (insert after `complete_onboarding` already handles its own FAQ creation, just after the existing `faqs` block)

Find where existing `services` FAQs are created (search for `faq_entries` in `complete_onboarding`). After the existing FAQ creation block, add:

```python
    # Insert wizard-provided FAQs
    if req.faqs:
        try:
            faq_rows = [
                {
                    "tenant_id": tenant_id,
                    "question": faq.question,
                    "answer": faq.answer,
                    "category": "wizard",
                    "is_active": True,
                }
                for faq in req.faqs
            ]
            db.table("faq_entries").insert(faq_rows).execute()
            configured["faqs"] = True
            result_obj.faqs_created += len(faq_rows)
        except Exception:
            logger.error("Failed to insert wizard FAQs for tenant %s", tenant_id, exc_info=True)
```

Note: `result_obj` is the `OnboardingCompleteResponse` built at the end — you'll need to read the full `complete_onboarding` function to find the exact variable name used and place this code correctly before it's returned.

- [ ] **Step 4: Smoke-test**

```bash
python -c "from backend.routers.onboarding import OnboardingCompleteRequest; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/onboarding.py
git commit -m "feat: extend OnboardingCompleteRequest with widget + FAQ fields"
```

---

## Task 4: Backend — Stripe `success_url` with `source` param

**Files:**
- Modify: `backend/routers/auth.py`

- [ ] **Step 1: Find the `billing_checkout` function** (currently around line 1413)

Read `backend/routers/auth.py` lines 1413–1463.

- [ ] **Step 2: Update the function to read `source` and use conditional `success_url`**

Find this block (currently lines 1444–1452):
```python
    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.frontend_url}/billing/cancel",
        "metadata": {"tenant_id": tenant_id, "plan": plan},
        "subscription_data": {"metadata": {"tenant_id": tenant_id, "plan": plan}},
    }
```

Replace with:
```python
    source = body.get("source")  # "wizard" | None
    if source == "wizard":
        success_url = f"{settings.frontend_url}/onboarding?step=6&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/onboarding?step=5&cancelled=1"
    else:
        success_url = f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.frontend_url}/billing/cancel"

    session_params: dict = {
        "mode": "subscription",
        "customer": customer.id,
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"tenant_id": tenant_id, "plan": plan},
        "subscription_data": {"metadata": {"tenant_id": tenant_id, "plan": plan}},
    }
```

- [ ] **Step 3: Verify existing callers are unaffected**

The existing `SignupPage.jsx` calls `POST /api/v1/auth/billing/checkout` with `{ plan: checkoutPlan }` — no `source` field. With `source=None`, the function uses the old success_url (`/billing/success`). Backward-compatible. ✓

- [ ] **Step 4: Smoke-test**

```bash
python -c "from backend.routers.auth import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/auth.py
git commit -m "feat: billing_checkout — conditional success_url for wizard source"
```

---

## Task 5: Backend — `knowledge_base` in system prompt

**Files:**
- Modify: `backend/routers/widget_helpers.py`
- Modify: `backend/routers/widget_chat.py`

- [ ] **Step 1: Update `_build_system_prompt` signature** (line 352 in `widget_helpers.py`)

Find:
```python
def _build_system_prompt(
    tenant: dict, faq_entries: list[dict], business_hours: dict | None = None,
    corrections: list[dict] | None = None,
    website_content: str | None = None,
    menu_items: list[dict] | None = None,
    job_listings: list[dict] | None = None,
    bid_templates: list[dict] | None = None,
    custom_field_defs: list[dict] | None = None,
    custom_instructions: str | None = None,
) -> str:
```

Replace with:
```python
def _build_system_prompt(
    tenant: dict, faq_entries: list[dict], business_hours: dict | None = None,
    corrections: list[dict] | None = None,
    website_content: str | None = None,
    menu_items: list[dict] | None = None,
    job_listings: list[dict] | None = None,
    bid_templates: list[dict] | None = None,
    custom_field_defs: list[dict] | None = None,
    custom_instructions: str | None = None,
    knowledge_base: str | None = None,
) -> str:
```

- [ ] **Step 2: Add `knowledge_block` variable** (add after `website_block = ...` around line 390)

After the `website_block` assignment, add:
```python
    knowledge_block = ""
    if knowledge_base:
        kb_content = knowledge_base[:6000]
        if len(knowledge_base) > 6000:
            kb_content += "\n[Content truncated]"
        knowledge_block = f"\n\nBusiness Knowledge Base (use this as primary reference for customer questions):\n{kb_content}"
```

- [ ] **Step 3: Insert `knowledge_block` into the return string** (currently around line 533)

Find the return statement:
```python
    return (
        f"{identity_line}\n\n"
        ...
        f"{faq_block}"
        f"{website_block}"
        ...
    )
```

Add `f"{knowledge_block}"` after `f"{website_block}"`:
```python
    return (
        f"{identity_line}\n\n"
        f"Rules:\n"
        f"- Be helpful, friendly, and concise (2-3 sentences max)\n"
        f"- Answer questions about the business using the FAQs and website content below\n"
        f"- Lead capture: When a visitor asks about pricing, cost, free trial, getting started, or shows clear buying intent, naturally ask for their email to send details or get them started. Frame it helpfully, e.g. 'I can send you the full details — what email should I use?' or 'I can set that up for you. What's your email address?'\n"
        f"- Don't ask for email on the first message, casual greetings, or simple questions. Wait for real interest or a question about services/pricing/trial.\n"
        f"- If they provide an email, thank them and move forward. Never ask for it again.\n"
        f"- NEVER re-ask for info already in the conversation. If they said their name, use it. If they gave email, move on.\n"
        f"- Don't follow a rigid script. Have a natural conversation.\n"
        f"- If you don't know something, say you'll have someone follow up\n"
        f"- Never claim to be human\n"
        f"- ALWAYS respond in the same language the visitor uses. If they write in Spanish, reply in Spanish. If they write in French, reply in French. Match their language exactly.\n"
        f"- If the visitor explicitly asks to speak with a human, a real person, or a team member, include the exact marker HANDOFF_REQUESTED at the very end of your response (after your message). Say something like 'Let me connect you with a team member who can help.' followed by HANDOFF_REQUESTED"
        f"{healthcare_block}"
        f"{hours_block}"
        f"{faq_block}"
        f"{website_block}"
        f"{knowledge_block}"
        f"{custom_fields_block}"
        f"{menu_block}"
        f"{jobs_block}"
        f"{bid_block}"
        f"{corrections_block}"
    )
```

- [ ] **Step 4: Pass `knowledge_base` from `widget_chat.py`** (line 333)

Find:
```python
    system_prompt = _build_system_prompt(
        tenant, faq_data, bh_data, corrections, website_content,
        menu_items, job_listings, bid_templates=bid_templates or None,
        custom_field_defs=custom_field_defs or None,
        custom_instructions=widget.get("custom_instructions") or None,
    )
```

Replace with:
```python
    system_prompt = _build_system_prompt(
        tenant, faq_data, bh_data, corrections, website_content,
        menu_items, job_listings, bid_templates=bid_templates or None,
        custom_field_defs=custom_field_defs or None,
        custom_instructions=widget.get("custom_instructions") or None,
        knowledge_base=widget.get("knowledge_base") or None,
    )
```

Note: `_get_widget_config` uses `select("*")`, so `knowledge_base` will be included automatically once the migration is applied. No change needed to `_get_widget_config`.

- [ ] **Step 5: Smoke-test**

```bash
python -c "from backend.routers.widget_helpers import _build_system_prompt; print('OK')"
python -c "from backend.routers.widget_chat import router; print('OK')"
```

Both: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/routers/widget_helpers.py backend/routers/widget_chat.py
git commit -m "feat: inject knowledge_base into widget chat system prompt"
```

---

## Task 6: Frontend — routing and signup redirect

**Files:**
- Modify: `frontend/src/main.jsx`
- Modify: `frontend/src/pages/SignupPage.jsx`
- Create: `frontend/public/widget-preview.html`

- [ ] **Step 1: Create `frontend/public/widget-preview.html`**

This static file loads the widget in an iframe for the Step 4 preview. It reads `api_key` from the URL query string.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Widget Preview</title>
  <style>
    body { margin: 0; background: #f0f4f8; min-height: 100vh; }
  </style>
</head>
<body>
<script>
  (function() {
    var params = new URLSearchParams(window.location.search);
    var apiKey = params.get("api_key");
    if (!apiKey) return;
    var s = document.createElement("script");
    s.src = "/widget/agentnexlify-widget.js";
    s.setAttribute("data-api-key", apiKey);
    s.async = true;
    document.body.appendChild(s);
  })();
</script>
</body>
</html>
```

- [ ] **Step 2: Add `/onboarding` route in `frontend/src/main.jsx`**

Add the lazy import at the top with the other lazy imports (after line 31):
```javascript
const OnboardingWizardPage = lazy(() => import("./pages/OnboardingWizardPage"));
```

Add the route before the `*` catch-all route (before line 131):
```jsx
<Route path="/onboarding" element={<AuthProvider><OnboardingWizardPage /></AuthProvider>} />
```

- [ ] **Step 3: Update `SignupPage.jsx` post-registration redirect** (line 144)

Find:
```javascript
      window.location.href = "/dashboard";
```

Replace with:
```javascript
      window.location.href = "/onboarding";
```

- [ ] **Step 4: Build to verify no import errors**

```bash
cd /home/aidan/agentnexlify/frontend && npm run build 2>&1 | tail -5
```

Expected: `✓ built in ...` with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.jsx frontend/src/pages/SignupPage.jsx frontend/public/widget-preview.html
git commit -m "feat: add /onboarding route; redirect signup to wizard"
```

---

## Task 7: Frontend — onboarding API helpers

**Files:**
- Create: `frontend/src/utils/api/onboarding.js`
- Modify: `frontend/src/utils/api/index.js`

- [ ] **Step 1: Check how `request` helper works**

Read `frontend/src/utils/api/dashboard.js` lines 1–20 to understand the `request` helper pattern.

- [ ] **Step 2: Create `frontend/src/utils/api/onboarding.js`**

```javascript
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function apiFetch(path, { token, method = "POST", body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Generate an AI knowledge base from onboarding answers.
 * Returns { knowledge_base: string|null, generated: boolean }
 */
export function generateKb(tenantId, token, data) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/generate-kb`, { token, body: data });
}

/**
 * Complete onboarding — persists all wizard data to the backend.
 */
export function completeOnboarding(tenantId, token, data) {
  return apiFetch(`/api/v1/onboarding/${tenantId}/complete`, { token, body: data });
}

/**
 * Create a Stripe Checkout session from the wizard (source="wizard").
 * Returns { checkout_url: string }
 */
export function checkoutForWizard(token, plan) {
  return apiFetch(`/api/v1/auth/billing/checkout`, {
    token,
    body: { plan, source: "wizard" },
  });
}
```

- [ ] **Step 3: Export from `frontend/src/utils/api/index.js`**

Read `frontend/src/utils/api/index.js` and add at the bottom:
```javascript
export * from "./onboarding";
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/api/onboarding.js frontend/src/utils/api/index.js
git commit -m "feat: add onboarding API helpers (generateKb, completeOnboarding, checkoutForWizard)"
```

---

## Task 8: Frontend — `OnboardingWizardPage` shell

**Files:**
- Create: `frontend/src/pages/OnboardingWizardPage.jsx`

- [ ] **Step 1: Create the shell with step management**

```jsx
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import WizardStepBusiness from "./wizard/WizardStepBusiness";
import WizardStepServices from "./wizard/WizardStepServices";
import WizardStepKnowledgeBase from "./wizard/WizardStepKnowledgeBase";
import WizardStepCustomize from "./wizard/WizardStepCustomize";
import WizardStepPlan from "./wizard/WizardStepPlan";
import WizardStepEmbed from "./wizard/WizardStepEmbed";

const STORAGE_KEY = "anx_wizard";
const TOTAL_STEPS = 6;

function loadState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveState(step, data) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ step, data }));
  } catch {}
}

export default function OnboardingWizardPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  // Redirect if not authenticated
  useEffect(() => {
    if (user === null) navigate("/signup", { replace: true });
  }, [user, navigate]);

  // Check URL params for Stripe return (step=6)
  const urlParams = new URLSearchParams(window.location.search);
  const urlStep = parseInt(urlParams.get("step") || "0", 10);

  const saved = loadState();
  const [step, setStep] = useState(() => urlStep >= 1 && urlStep <= 6 ? urlStep : (saved?.step || 1));
  const [wizardData, setWizardData] = useState(() => saved?.data || {
    business_name: user?.businessName || "",
    business_type: user?.businessType || "",
    city: user?.city || "",
    phone: "",
    website_url: "",
    hours: null,
    services: [],
    faqs: [],
    knowledge_base: null,
    widget_bot_name: "",
    widget_primary_color: "#00BFFF",
    widget_greeting_message: "",
    widget_position: "bottom-right",
  });

  // Persist to sessionStorage on every change
  useEffect(() => {
    saveState(step, wizardData);
  }, [step, wizardData]);

  const goNext = useCallback((updates = {}) => {
    setWizardData(prev => ({ ...prev, ...updates }));
    setStep(s => Math.min(s + 1, TOTAL_STEPS));
  }, []);

  const goBack = useCallback(() => {
    setStep(s => Math.max(s - 1, 1));
  }, []);

  if (!user) return null;

  const stepComponents = [
    null, // 1-indexed
    <WizardStepBusiness key="1" wizardData={wizardData} onNext={goNext} />,
    <WizardStepServices key="2" wizardData={wizardData} onNext={goNext} onBack={goBack} />,
    <WizardStepKnowledgeBase key="3" wizardData={wizardData} onNext={goNext} onBack={goBack} token={token} tenantId={user?.tenantId} />,
    <WizardStepCustomize key="4" wizardData={wizardData} onNext={goNext} onBack={goBack} apiKey={user?.widgetApiKey} />,
    <WizardStepPlan key="5" wizardData={wizardData} onNext={goNext} onBack={goBack} token={token} tenantId={user?.tenantId} />,
    <WizardStepEmbed key="6" wizardData={wizardData} apiKey={user?.widgetApiKey} />,
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary, #0a0a0f)", color: "var(--text-primary, #e2e8f0)", fontFamily: "system-ui, sans-serif" }}>
      {/* Progress bar */}
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, height: 3, background: "rgba(255,255,255,0.1)", zIndex: 100 }}>
        <div style={{ height: "100%", width: `${(step / TOTAL_STEPS) * 100}%`, background: "#6366f1", transition: "width 0.3s ease" }} />
      </div>

      {/* Header */}
      <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "#6366f1" }}>AgentNexLiFy</span>
        <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.85rem" }}>Step {step} of {TOTAL_STEPS}</span>
      </div>

      {/* Step content */}
      <div style={{ maxWidth: 640, margin: "0 auto", padding: "40px 24px 80px" }}>
        {stepComponents[step]}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Check what `user` object contains**

Read `frontend/src/context/AuthContext.jsx` to verify `user.tenantId`, `user.widgetApiKey`, `user.businessName` are available. Note the exact field names and adjust the `wizardData` defaults above if needed.

- [ ] **Step 3: Build to check for import errors**

```bash
cd /home/aidan/agentnexlify/frontend && npm run build 2>&1 | grep -E "error|Error" | head -10
```

Expected: no errors (step components don't exist yet but the build should fail on missing imports — create stubs in next tasks if needed to unblock this build).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/OnboardingWizardPage.jsx
git commit -m "feat: OnboardingWizardPage shell with step management and sessionStorage"
```

---

## Task 9: Frontend — `WizardStepBusiness` (Step 1)

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepBusiness.jsx`

- [ ] **Step 1: Create the directory and component**

```bash
mkdir -p /home/aidan/agentnexlify/frontend/src/pages/wizard
```

```jsx
// frontend/src/pages/wizard/WizardStepBusiness.jsx
import { useState } from "react";

const INDUSTRIES = [
  "plumbing", "hvac", "electrical", "roofing", "landscaping",
  "cleaning", "pest_control", "painting", "flooring", "general_contractor",
  "auto_shop", "salon", "spa", "dental", "medical", "veterinary",
  "legal", "accounting", "real_estate", "restaurant", "retail", "other",
];

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

const TIMEZONES = [
  "America/New_York", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "America/Phoenix", "America/Anchorage", "Pacific/Honolulu",
];

function defaultHours() {
  const h = { timezone: "America/New_York" };
  DAYS.forEach(d => {
    h[d] = d === "saturday" || d === "sunday"
      ? { enabled: false, open: "09:00", close: "17:00" }
      : { enabled: true, open: "09:00", close: "17:00" };
  });
  return h;
}

export default function WizardStepBusiness({ wizardData, onNext }) {
  const [form, setForm] = useState({
    business_name: wizardData.business_name || "",
    business_type: wizardData.business_type || "plumbing",
    city: wizardData.city || "",
    phone: wizardData.phone || "",
    website_url: wizardData.website_url || "",
    hours: wizardData.hours || defaultHours(),
  });
  const [error, setError] = useState("");

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }));
  }

  function setHours(day, field, value) {
    setForm(f => ({
      ...f,
      hours: {
        ...f.hours,
        [day]: { ...f.hours[day], [field]: value },
      },
    }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.business_name.trim()) { setError("Business name is required."); return; }
    if (!form.city.trim()) { setError("City is required."); return; }
    setError("");
    onNext(form);
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Tell us about your business</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        This information helps your AI assistant answer customer questions accurately.
      </p>

      {error && <div style={{ background: "#dc2626", color: "#fff", padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: "0.9rem" }}>{error}</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <label style={labelStyle}>
          Business Name *
          <input style={inputStyle} value={form.business_name} onChange={set("business_name")} placeholder="Acme Plumbing" required />
        </label>

        <label style={labelStyle}>
          Industry *
          <select style={inputStyle} value={form.business_type} onChange={set("business_type")}>
            {INDUSTRIES.map(i => <option key={i} value={i}>{i.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>)}
          </select>
        </label>

        <label style={labelStyle}>
          City / Service Area *
          <input style={inputStyle} value={form.city} onChange={set("city")} placeholder="Austin, TX" required />
        </label>

        <label style={labelStyle}>
          Phone Number
          <input style={inputStyle} value={form.phone} onChange={set("phone")} placeholder="512-555-0100" type="tel" />
        </label>

        <label style={labelStyle}>
          Website URL
          <input style={inputStyle} value={form.website_url} onChange={set("website_url")} placeholder="https://acmeplumbing.com" type="url" />
        </label>

        {/* Hours grid */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Business Hours</span>
            <select
              style={{ ...inputStyle, width: "auto", padding: "4px 8px", fontSize: "0.8rem" }}
              value={form.hours.timezone}
              onChange={e => setForm(f => ({ ...f, hours: { ...f.hours, timezone: e.target.value } }))}
            >
              {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz.replace("America/", "").replace("Pacific/", "Pacific/")}</option>)}
            </select>
          </div>
          {DAYS.map(day => (
            <div key={day} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, fontSize: "0.85rem" }}>
              <input
                type="checkbox"
                checked={form.hours[day]?.enabled || false}
                onChange={e => setHours(day, "enabled", e.target.checked)}
                style={{ width: 16, height: 16, cursor: "pointer", flexShrink: 0 }}
              />
              <span style={{ width: 80, textTransform: "capitalize", color: form.hours[day]?.enabled ? "inherit" : "rgba(255,255,255,0.3)" }}>{day}</span>
              {form.hours[day]?.enabled && (
                <>
                  <input type="time" value={form.hours[day].open} onChange={e => setHours(day, "open", e.target.value)} style={{ ...inputStyle, width: 100, padding: "4px 8px" }} />
                  <span style={{ color: "rgba(255,255,255,0.4)" }}>to</span>
                  <input type="time" value={form.hours[day].close} onChange={e => setHours(day, "close", e.target.value)} style={{ ...inputStyle, width: 100, padding: "4px 8px" }} />
                </>
              )}
              {!form.hours[day]?.enabled && <span style={{ color: "rgba(255,255,255,0.3)" }}>Closed</span>}
            </div>
          ))}
        </div>
      </div>

      <button type="submit" style={btnStyle}>Continue →</button>
    </form>
  );
}

const labelStyle = { display: "flex", flexDirection: "column", gap: 6, fontSize: "0.9rem", fontWeight: 500 };
const inputStyle = {
  background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box",
};
const btnStyle = {
  marginTop: 32, width: "100%", padding: "14px", background: "#6366f1", color: "#fff",
  border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer",
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepBusiness.jsx
git commit -m "feat: WizardStepBusiness — step 1 business info form"
```

---

## Task 10: Frontend — `WizardStepServices` (Step 2)

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepServices.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/pages/wizard/WizardStepServices.jsx
import { useState } from "react";

// Industry-specific service suggestions
const SUGGESTIONS = {
  plumbing: ["Drain Cleaning", "Water Heater Installation", "Leak Repair", "Pipe Replacement", "Sewer Line Repair"],
  hvac: ["AC Repair", "Furnace Installation", "Duct Cleaning", "Thermostat Installation", "System Tune-up"],
  auto_shop: ["Oil Change", "Tire Rotation", "Brake Service", "Engine Diagnostics", "Transmission Repair"],
  salon: ["Haircut", "Color & Highlights", "Blowout", "Keratin Treatment", "Extensions"],
  dental: ["Teeth Cleaning", "Teeth Whitening", "Dental Implants", "Invisalign", "Emergency Care"],
  restaurant: ["Dine In", "Takeout", "Delivery", "Catering", "Private Events"],
  default: ["Consultation", "Custom Quote", "Emergency Service", "Maintenance", "Installation"],
};

export default function WizardStepServices({ wizardData, onNext, onBack }) {
  const [services, setServices] = useState(wizardData.services || []);
  const [serviceInput, setServiceInput] = useState("");
  const [faqs, setFaqs] = useState(
    wizardData.faqs?.length ? wizardData.faqs : [{ question: "", answer: "" }]
  );

  const suggestions = SUGGESTIONS[wizardData.business_type] || SUGGESTIONS.default;

  function addService(name) {
    const trimmed = name.trim();
    if (!trimmed || services.includes(trimmed) || services.length >= 10) return;
    setServices(s => [...s, trimmed]);
    setServiceInput("");
  }

  function removeService(name) {
    setServices(s => s.filter(x => x !== name));
  }

  function addFaq() {
    if (faqs.length >= 8) return;
    setFaqs(f => [...f, { question: "", answer: "" }]);
  }

  function removeFaq(i) {
    setFaqs(f => f.filter((_, idx) => idx !== i));
  }

  function updateFaq(i, field, value) {
    setFaqs(f => f.map((faq, idx) => idx === i ? { ...faq, [field]: value } : faq));
  }

  function handleNext() {
    const validFaqs = faqs.filter(f => f.question.trim() && f.answer.trim());
    onNext({ services, faqs: validFaqs });
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Services & FAQs</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Tell your AI assistant what you offer and how to answer common questions.
      </p>

      {/* Services */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>What services do you offer?</div>

        {/* Chips */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {services.map(s => (
            <div key={s} style={chipStyle}>
              {s}
              <button onClick={() => removeService(s)} style={chipXStyle}>&times;</button>
            </div>
          ))}
        </div>

        {/* Add service input */}
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={serviceInput}
            onChange={e => setServiceInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addService(serviceInput))}
            placeholder="Type a service and press Enter"
            style={inputStyle}
          />
          <button onClick={() => addService(serviceInput)} style={{ ...btnSmall, flexShrink: 0 }}>Add</button>
        </div>

        {/* Suggestions */}
        <div style={{ marginTop: 10 }}>
          <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)", marginRight: 8 }}>Suggestions:</span>
          {suggestions.filter(s => !services.includes(s)).slice(0, 5).map(s => (
            <button key={s} onClick={() => addService(s)} style={suggStyle}>{s}</button>
          ))}
        </div>
      </div>

      {/* FAQs */}
      <div>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>Common customer questions <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 400, fontSize: "0.85rem" }}>(optional)</span></div>
        {faqs.map((faq, i) => (
          <div key={i} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 10, padding: 16, marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>Q&A #{i + 1}</span>
              {faqs.length > 1 && (
                <button onClick={() => removeFaq(i)} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: "0.85rem" }}>Remove</button>
              )}
            </div>
            <input
              placeholder="Customer question (e.g. Do you offer emergency service?)"
              value={faq.question}
              onChange={e => updateFaq(i, "question", e.target.value)}
              style={{ ...inputStyle, marginBottom: 8 }}
              maxLength={500}
            />
            <textarea
              placeholder="Your answer"
              value={faq.answer}
              onChange={e => updateFaq(i, "answer", e.target.value)}
              rows={2}
              style={{ ...inputStyle, resize: "vertical" }}
              maxLength={2000}
            />
          </div>
        ))}
        {faqs.length < 8 && (
          <button onClick={addFaq} style={{ ...btnSmall, width: "100%", marginBottom: 8 }}>+ Add Question</button>
        )}
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 32 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>← Back</button>
        <button onClick={handleNext} style={{ ...btnStyle, flex: 2 }}>Continue →</button>
      </div>
    </div>
  );
}

const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box" };
const chipStyle = { display: "flex", alignItems: "center", gap: 6, background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.4)", borderRadius: 20, padding: "4px 12px", fontSize: "0.85rem", color: "#a5b4fc" };
const chipXStyle = { background: "none", border: "none", cursor: "pointer", color: "#a5b4fc", fontSize: "1rem", lineHeight: 1, padding: 0 };
const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
const btnSmall = { padding: "8px 16px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer" };
const suggStyle = { marginRight: 6, marginBottom: 4, padding: "4px 10px", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, fontSize: "0.8rem", color: "rgba(255,255,255,0.6)", cursor: "pointer" };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepServices.jsx
git commit -m "feat: WizardStepServices — step 2 services chips and FAQ pairs"
```

---

## Task 11: Frontend — `WizardStepKnowledgeBase` (Step 3)

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx
import { useState, useEffect } from "react";
import { generateKb } from "../../utils/api/onboarding";

export default function WizardStepKnowledgeBase({ wizardData, onNext, onBack, token, tenantId }) {
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [kb, setKb] = useState(wizardData.knowledge_base || null);
  const [editing, setEditing] = useState(false);
  const [editedKb, setEditedKb] = useState("");

  useEffect(() => {
    // Auto-trigger generation if we don't already have a KB
    if (!kb && status === "idle") {
      generate();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function generate() {
    setStatus("loading");
    try {
      const payload = {
        business_name: wizardData.business_name,
        business_type: wizardData.business_type,
        city: wizardData.city,
        phone: wizardData.phone || null,
        website_url: wizardData.website_url || null,
        services: wizardData.services || [],
        faqs: wizardData.faqs || [],
        hours: wizardData.hours || null,
      };
      const res = await generateKb(tenantId, token, payload);
      if (res.generated && res.knowledge_base) {
        setKb(res.knowledge_base);
        setEditedKb(res.knowledge_base);
        setStatus("done");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  }

  function handleNext() {
    const finalKb = editing ? editedKb : kb;
    onNext({ knowledge_base: finalKb });
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Generating your AI knowledge base</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Your answers are being turned into a knowledge base your AI assistant will use to answer customer questions.
      </p>

      {status === "loading" && (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <div style={{ width: 48, height: 48, border: "3px solid rgba(255,255,255,0.1)", borderTopColor: "#6366f1", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ color: "rgba(255,255,255,0.5)" }}>Building knowledge base…</p>
        </div>
      )}

      {status === "error" && (
        <div style={{ background: "rgba(220,38,38,0.1)", border: "1px solid rgba(220,38,38,0.3)", borderRadius: 10, padding: 20, marginBottom: 24 }}>
          <p style={{ color: "#f87171", margin: 0, marginBottom: 12 }}>Generation failed. You can retry or skip and continue.</p>
          <button onClick={generate} style={btnSecondary}>Retry</button>
        </div>
      )}

      {status === "done" && kb && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span style={{ fontWeight: 600, color: "#86efac" }}>✓ Knowledge base ready</span>
            <button onClick={() => { setEditing(!editing); setEditedKb(kb); }} style={btnSecondary}>
              {editing ? "Done editing" : "Edit"}
            </button>
          </div>
          {editing ? (
            <textarea
              value={editedKb}
              onChange={e => setEditedKb(e.target.value)}
              rows={16}
              style={{ ...textareaStyle, fontFamily: "monospace", fontSize: "0.82rem" }}
            />
          ) : (
            <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: 20, maxHeight: 320, overflowY: "auto" }}>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.85rem", color: "rgba(255,255,255,0.8)", fontFamily: "monospace" }}>{kb}</pre>
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>← Back</button>
        <button
          onClick={handleNext}
          disabled={status === "loading"}
          style={{ ...btnStyle, flex: 2, opacity: status === "loading" ? 0.5 : 1 }}
        >
          {status === "idle" || status === "error" ? "Skip →" : "Continue →"}
        </button>
      </div>
    </div>
  );
}

const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
const btnSecondary = { padding: "6px 14px", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer" };
const textareaStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "12px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box", resize: "vertical" };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx
git commit -m "feat: WizardStepKnowledgeBase — step 3 AI knowledge base generation"
```

---

## Task 12: Frontend — `WizardStepCustomize` (Step 4) + preview iframe

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepCustomize.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/pages/wizard/WizardStepCustomize.jsx
import { useState } from "react";

const POSITIONS = [
  { value: "bottom-right", label: "Bottom Right" },
  { value: "bottom-left", label: "Bottom Left" },
];

export default function WizardStepCustomize({ wizardData, onNext, onBack, apiKey }) {
  const [form, setForm] = useState({
    widget_bot_name: wizardData.widget_bot_name || `${wizardData.business_name} Assistant`,
    widget_primary_color: wizardData.widget_primary_color || "#00BFFF",
    widget_greeting_message: wizardData.widget_greeting_message || `Hi! Welcome to ${wizardData.business_name}. How can I help you?`,
    widget_position: wizardData.widget_position || "bottom-right",
  });

  function set(field) {
    return e => setForm(f => ({ ...f, [field]: e.target.value }));
  }

  // Build preview iframe src (widget-preview.html is served from /public)
  const previewSrc = apiKey
    ? `/widget-preview.html?api_key=${encodeURIComponent(apiKey)}`
    : null;

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Customize your widget</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Match it to your brand. The live preview updates as you save.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 32 }}>
        <label style={labelStyle}>
          Bot Name
          <input style={inputStyle} value={form.widget_bot_name} onChange={set("widget_bot_name")} placeholder="Acme Assistant" maxLength={100} />
        </label>

        <label style={labelStyle}>
          Primary Color
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input type="color" value={form.widget_primary_color} onChange={set("widget_primary_color")} style={{ width: 48, height: 40, border: "none", background: "none", cursor: "pointer", padding: 0, borderRadius: 6 }} />
            <input style={{ ...inputStyle, flex: 1 }} value={form.widget_primary_color} onChange={set("widget_primary_color")} placeholder="#00BFFF" />
          </div>
        </label>

        <label style={labelStyle}>
          Greeting Message
          <textarea style={{ ...inputStyle, resize: "vertical" }} value={form.widget_greeting_message} onChange={set("widget_greeting_message")} rows={2} maxLength={500} />
        </label>

        <label style={labelStyle}>
          Position
          <select style={inputStyle} value={form.widget_position} onChange={set("widget_position")}>
            {POSITIONS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>
        </label>
      </div>

      {/* Live preview */}
      {previewSrc && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontWeight: 600, marginBottom: 10 }}>Live Preview</div>
          <div style={{ border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, overflow: "hidden", height: 320, background: "#f0f4f8" }}>
            <iframe
              src={previewSrc}
              style={{ width: "100%", height: "100%", border: "none" }}
              title="Widget Preview"
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
          <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", marginTop: 6 }}>
            Preview uses your live widget config. Changes take up to 5 minutes to appear here.
          </p>
        </div>
      )}

      {/* Color preview patch — show what the color looks like before cache expires */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, background: "rgba(255,255,255,0.04)", borderRadius: 10, marginBottom: 32 }}>
        <div style={{ width: 48, height: 48, borderRadius: "50%", background: form.widget_primary_color, flexShrink: 0, boxShadow: "0 2px 8px rgba(0,0,0,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{form.widget_bot_name}</div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.8rem" }}>{form.widget_greeting_message}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12 }}>
        <button onClick={onBack} style={{ ...btnStyle, background: "rgba(255,255,255,0.08)", flex: 1 }}>← Back</button>
        <button onClick={() => onNext(form)} style={{ ...btnStyle, flex: 2 }}>Continue →</button>
      </div>
    </div>
  );
}

const labelStyle = { display: "flex", flexDirection: "column", gap: 6, fontSize: "0.9rem", fontWeight: 500 };
const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#e2e8f0", fontSize: "0.9rem", width: "100%", boxSizing: "border-box" };
const btnStyle = { padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: 10, fontSize: "1rem", fontWeight: 600, cursor: "pointer" };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepCustomize.jsx
git commit -m "feat: WizardStepCustomize — step 4 widget customization with preview"
```

---

## Task 13: Frontend — `WizardStepPlan` (Step 5)

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepPlan.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/pages/wizard/WizardStepPlan.jsx
import { useState } from "react";
import { completeOnboarding, checkoutForWizard } from "../../utils/api/onboarding";

const PLANS = [
  {
    key: "free",
    name: "Free",
    price: "$0/mo",
    color: "#64748b",
    features: ["AI chat widget", "Up to 50 conversations/mo", "Basic lead capture"],
    cta: "Continue Free",
    highlight: false,
  },
  {
    key: "growth",
    name: "Growth",
    price: "$249/mo",
    color: "#6366f1",
    features: ["Unlimited conversations", "CRM & lead management", "Email sequences", "Priority support"],
    cta: "Start Growth",
    highlight: true,
  },
  {
    key: "professional",
    name: "Professional",
    price: "$499/mo",
    color: "#8b5cf6",
    features: ["Everything in Growth", "AI answering service", "Marketing campaigns", "White-label options"],
    cta: "Start Professional",
    highlight: false,
  },
  {
    key: "autopilot",
    name: "Autopilot",
    price: "$299/mo",
    color: "#0ea5e9",
    features: ["Full automation suite", "Smart lists & targeting", "Document signing", "Dedicated onboarding"],
    cta: "Start Autopilot",
    highlight: false,
  },
];

export default function WizardStepPlan({ wizardData, onNext, onBack, token, tenantId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePlan(plan) {
    setLoading(true);
    setError("");
    try {
      // Always persist wizard data first
      await completeOnboarding(tenantId, token, {
        business_name: wizardData.business_name,
        business_type: wizardData.business_type,
        city: wizardData.city,
        phone: wizardData.phone || null,
        website_url: wizardData.website_url || null,
        hours: wizardData.hours || null,
        services: wizardData.services || null,
        widget_bot_name: wizardData.widget_bot_name || null,
        widget_primary_color: wizardData.widget_primary_color || null,
        widget_greeting_message: wizardData.widget_greeting_message || null,
        widget_position: wizardData.widget_position || null,
        faqs: wizardData.faqs?.length ? wizardData.faqs : null,
      });

      if (plan === "free") {
        onNext({ chosen_plan: "free" });
        return;
      }

      // Paid plan — redirect to Stripe Checkout
      const res = await checkoutForWizard(token, plan);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        setError("Checkout failed. Try again.");
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 8 }}>Choose your plan</h2>
      <p style={{ color: "rgba(255,255,255,0.5)", marginBottom: 32, fontSize: "0.9rem" }}>
        Start free. Upgrade anytime as your business grows.
      </p>

      {error && <div style={{ background: "rgba(220,38,38,0.1)", border: "1px solid rgba(220,38,38,0.3)", borderRadius: 10, padding: 14, marginBottom: 20, color: "#f87171", fontSize: "0.9rem" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
        {PLANS.map(plan => (
          <div
            key={plan.key}
            style={{
              border: `1px solid ${plan.highlight ? plan.color : "rgba(255,255,255,0.12)"}`,
              borderRadius: 12,
              padding: 20,
              background: plan.highlight ? `rgba(99,102,241,0.1)` : "rgba(255,255,255,0.04)",
              position: "relative",
            }}
          >
            {plan.highlight && (
              <div style={{ position: "absolute", top: -10, left: "50%", transform: "translateX(-50%)", background: plan.color, color: "#fff", fontSize: "0.7rem", fontWeight: 700, padding: "3px 10px", borderRadius: 20 }}>POPULAR</div>
            )}
            <div style={{ fontWeight: 700, fontSize: "1rem", marginBottom: 4 }}>{plan.name}</div>
            <div style={{ fontSize: "1.4rem", fontWeight: 800, color: plan.color, marginBottom: 12 }}>{plan.price}</div>
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: "0.82rem", color: "rgba(255,255,255,0.7)", marginBottom: 16 }}>
              {plan.features.map(f => <li key={f} style={{ marginBottom: 4 }}>{f}</li>)}
            </ul>
            <button
              onClick={() => handlePlan(plan.key)}
              disabled={loading}
              style={{
                width: "100%", padding: "10px", background: plan.highlight ? plan.color : "rgba(255,255,255,0.08)",
                color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
                fontSize: "0.85rem", opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "…" : plan.cta}
            </button>
          </div>
        ))}
      </div>

      <button onClick={onBack} style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: "0.85rem" }}>← Back</button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepPlan.jsx
git commit -m "feat: WizardStepPlan — step 5 plan selection with free + Stripe paid flows"
```

---

## Task 14: Frontend — `WizardStepEmbed` (Step 6)

**Files:**
- Create: `frontend/src/pages/wizard/WizardStepEmbed.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/pages/wizard/WizardStepEmbed.jsx
import { useState } from "react";

const CDN_URL = "https://agentnexlify.com/widget/agentnexlify-widget.js";

export default function WizardStepEmbed({ wizardData, apiKey }) {
  const [copied, setCopied] = useState(false);

  const snippet = apiKey
    ? `<script src="${CDN_URL}"\n        data-api-key="${apiKey}"\n        async>\n</script>`
    : "<!-- API key not available — check your dashboard -->";

  function handleCopy() {
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <div style={{ textAlign: "center" }}>
      {/* Success banner */}
      <div style={{ background: "rgba(134,239,172,0.1)", border: "1px solid rgba(134,239,172,0.3)", borderRadius: 14, padding: "28px 20px", marginBottom: 32 }}>
        <div style={{ fontSize: "2.5rem", marginBottom: 8 }}>🎉</div>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#86efac", marginBottom: 6 }}>Your AI assistant is live!</h2>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "0.9rem", margin: 0 }}>
          Paste this code on your website to activate the chat widget.
        </p>
      </div>

      {/* Embed snippet */}
      <div style={{ textAlign: "left", marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <span style={{ fontWeight: 600 }}>Your embed code</span>
          <button onClick={handleCopy} style={copyBtnStyle}>
            {copied ? "✓ Copied!" : "Copy Code"}
          </button>
        </div>
        <pre style={{
          background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
          padding: 20, fontSize: "0.85rem", color: "#86efac", overflowX: "auto", margin: 0, whiteSpace: "pre",
        }}>
          {snippet}
        </pre>
      </div>

      {/* Installation steps */}
      <div style={{ textAlign: "left", background: "rgba(255,255,255,0.04)", borderRadius: 12, padding: 20, marginBottom: 32 }}>
        <div style={{ fontWeight: 600, marginBottom: 14 }}>How to install</div>
        {[
          "Open your website's HTML file or CMS template",
          "Paste the code above just before the closing </body> tag",
          "Save and refresh your page — the chat widget will appear",
        ].map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 14, marginBottom: i < 2 ? 12 : 0, alignItems: "flex-start" }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", background: "#6366f1", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, flexShrink: 0 }}>{i + 1}</div>
            <span style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.9rem", paddingTop: 3 }}>{step}</span>
          </div>
        ))}
      </div>

      {/* CTA buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <a href="/dashboard" style={{ display: "block", padding: "14px", background: "#6366f1", color: "#fff", borderRadius: 10, fontSize: "1rem", fontWeight: 600, textDecoration: "none" }}>
          Go to Dashboard →
        </a>
        {apiKey && (
          <a
            href={`/widget-preview.html?api_key=${encodeURIComponent(apiKey)}`}
            target="_blank"
            rel="noreferrer"
            style={{ display: "block", padding: "12px", background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.8)", borderRadius: 10, fontSize: "0.9rem", fontWeight: 500, textDecoration: "none" }}
          >
            Test your widget ↗
          </a>
        )}
      </div>
    </div>
  );
}

const copyBtnStyle = { padding: "6px 14px", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", border: "1px solid rgba(99,102,241,0.3)", borderRadius: 8, fontSize: "0.85rem", cursor: "pointer", fontWeight: 600 };
```

- [ ] **Step 2: Build to verify all wizard components compile**

```bash
cd /home/aidan/agentnexlify/frontend && npm run build 2>&1 | tail -10
```

Expected: clean build, `✓ built in ...`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/wizard/WizardStepEmbed.jsx
git commit -m "feat: WizardStepEmbed — step 6 embed code with copy button and installation guide"
```

---

## Task 15: End-to-End QA

**Files:**
- Read: `planning/specs/onboarding-wizard_spec.md` (acceptance criteria)

- [ ] **Step 1: Verify backend routes are registered**

```bash
cd /home/aidan/agentnexlify
python -c "
from backend.main import app
routes = [r.path for r in app.routes]
print([r for r in routes if 'onboarding' in r])
"
```

Expected: `['/api/v1/onboarding/{tenant_id}/complete', '/api/v1/onboarding/{tenant_id}/status', '/api/v1/onboarding/{tenant_id}/generate-kb']`

- [ ] **Step 2: Verify `knowledge_base` is in the system prompt when set**

```bash
python -c "
from backend.routers.widget_helpers import _build_system_prompt
tenant = {'business_name': 'Test', 'business_type': 'plumbing', 'city': 'Austin'}
prompt = _build_system_prompt(tenant, [], knowledge_base='## About\nTest business')
assert 'Business Knowledge Base' in prompt
assert 'Test business' in prompt
print('knowledge_base injection: OK')
"
```

- [ ] **Step 3: Verify `generate-kb` endpoint shape**

```bash
python -c "
from backend.routers.onboarding import GenerateKbRequest, GenerateKbResponse
r = GenerateKbRequest(business_name='Test', business_type='plumbing', city='Austin')
print('GenerateKbRequest OK:', r.model_fields.keys())
print('GenerateKbResponse OK:', GenerateKbResponse.model_fields.keys())
"
```

Expected: both print field names without errors.

- [ ] **Step 4: Verify Stripe source param**

```bash
python -c "
import inspect
from backend.routers.auth import billing_checkout
src = inspect.getsource(billing_checkout)
assert 'source' in src
assert 'wizard' in src
assert '/onboarding?step=6' in src
print('Stripe source param: OK')
"
```

- [ ] **Step 5: Verify frontend build is clean**

```bash
cd /home/aidan/agentnexlify/frontend && npm run build 2>&1 | grep -E "^(✓|error|Error)" | head -5
```

Expected: `✓ built in ...`

- [ ] **Step 6: Verify widget files in sync**

```bash
diff /home/aidan/agentnexlify/widget/agentnexlify-widget.js \
     /home/aidan/agentnexlify/frontend/public/widget/agentnexlify-widget.js \
  && echo "Widget files in sync: OK"
```

- [ ] **Step 7: Check acceptance criteria coverage**

Re-read `planning/specs/onboarding-wizard_spec.md` acceptance criteria 1–12. For each, identify which task implements it:

| AC | Covered by |
|----|-----------|
| AC1 — 6 steps in <5 min | Tasks 8–14 (all wizard steps) |
| AC2 — tenant DB fields populated | Task 3 (extend complete endpoint) |
| AC3 — widget_configs populated | Tasks 2–3 (generate-kb + complete) |
| AC4 — embed snippet works | Task 14 (WizardStepEmbed) |
| AC5 — live preview in step 4 | Task 12 (WizardStepCustomize) |
| AC6 — paid plan → Stripe → step 6 | Tasks 4, 13 |
| AC7 — free plan skips Stripe | Task 13 |
| AC8 — KB failure non-blocking | Task 11 (error state + skip) |
| AC9 — multi-tenant isolation | Tasks 2–4 (all use JWT tenant_id) |
| AC10 — unauthenticated → /signup | Task 8 (useEffect redirect) |
| AC11 — refresh resumes correct step | Task 8 (sessionStorage) |
| AC12 — mobile 375px usable | Tasks 9–14 (flex column, 100% width inputs) |

- [ ] **Step 8: Final commit + push**

```bash
cd /home/aidan/agentnexlify
git add -A
git status  # review what's staged
git commit -m "feat: self-serve onboarding wizard — 6-step flow, KB generation, Stripe checkout

- Migration 076: widget_configs.knowledge_base
- Backend: generate-kb endpoint (Claude API), extend onboarding/complete with
  widget + FAQ fields, Stripe success_url source=wizard param, knowledge_base
  injection into system prompt
- Frontend: /onboarding route, 6 wizard steps, sessionStorage persistence,
  widget preview iframe, embed code copy"
git push
```

---

## Open Questions (Resolved)

1. **Stripe success_url conflict** — Resolved: Option A, `source=wizard` param (Task 4).
2. **Preview iframe CSP** — `widget-preview.html` served from Vite public; loads widget from same origin. No CDN dependency, no CSP issue.
3. **sessionStorage cross-origin** — By Step 6, all data is in DB. Embed only needs `api_key` from `useAuth()`, which comes from localStorage (survives Stripe redirect). No issue.
4. **Industry suggestions** — 5 industries pre-loaded (Task 10); others get generic suggestions. Can expand post-launch.
