---
name: industry-content
description: "Use when adding support for a new business type or industry to ensure all industry-specific content is created consistently."
version: 1.0.0
origin: claude
triggers: ["new business type", "new industry", "industry FAQs", "pipeline preset", "form preset", "reminder extras", "aftercare template", "rebook interval"]
effort: medium
---

# Industry Content — Adding a New Business Type

## When to Use
- Adding support for a new industry/business type
- Expanding content for an existing business type
- Running a customer simulation that reveals content gaps

## When NOT to Use
- Modifying existing industry content (just edit the files directly)
- Debugging industry-specific bugs (use debugging skills instead)
- Making schema changes (use migration-workflow skill)

## Checklist

When adding a new business type (e.g., "veterinary"), ensure ALL of these are created:

### 1. Industry FAQs (backend/routers/auth.py)
- [ ] Add entry to `_INDUSTRY_FAQS` dict
- [ ] Minimum 5 FAQs per industry
- [ ] Categories: Services, Pricing, Policy, About, Booking
- [ ] Tone: friendly, non-technical, ready-to-use answers

### 2. Pipeline Preset (backend/routers/pipeline.py)
- [ ] Add entry to `_INDUSTRY_STAGES` dict
- [ ] Include: New Lead → industry-specific stages → Won/Completed → Lost/Inactive
- [ ] Each stage needs: name, sort_order, color, is_won, is_lost
- [ ] If the business type uses a different name in the frontend dropdown, add to `_TYPE_ALIASES`

### 3. Form Preset (backend/routers/forms.py)
- [ ] Add entry to `_FORM_PRESETS` dict (if the industry has a unique intake process)
- [ ] Include fields: name, email, phone + industry-specific fields
- [ ] Add a consent checkbox if handling sensitive data
- [ ] Set appropriate success_message

### 4. Reminder Extras (backend/services/automation_engine.py)
- [ ] Add entry to `_REMINDER_EXTRAS` dict
- [ ] List 2-3 items to bring/prepare for appointments
- [ ] Consider service-specific sub-items (like dental has root_canal extras)

### 5. Aftercare Templates (backend/services/automation_engine.py)
- [ ] Add entry to `_AFTERCARE_TEMPLATES` dict
- [ ] Include a "default" template
- [ ] Add service-specific variants if applicable (keyed by keyword in notes)

### 6. Rebook Interval (backend/services/automation_engine.py)
- [ ] Add entry to `_REBOOK_INTERVALS` dict (if the industry has a natural revisit cycle)
- [ ] Format: (days, "description of next visit")

### 7. HIPAA/Privacy (backend/routers/widget_helpers.py)
- [ ] If healthcare-related, add to the HIPAA business type check in `_build_system_prompt()`

### 8. Simulation Document (docs/dev-knowledge/)
- [ ] Create `simulation-{industry}.md` documenting the walkthrough and gaps

## Files to Modify

| File | What to Add |
|------|-------------|
| `backend/routers/auth.py` | FAQs in `_INDUSTRY_FAQS` |
| `backend/routers/pipeline.py` | Stages in `_INDUSTRY_STAGES` + alias in `_TYPE_ALIASES` |
| `backend/routers/forms.py` | Preset in `_FORM_PRESETS` (optional) |
| `backend/services/automation_engine.py` | `_REMINDER_EXTRAS`, `_AFTERCARE_TEMPLATES`, `_REBOOK_INTERVALS` |
| `backend/routers/widget_helpers.py` | HIPAA check (if healthcare) |
| `docs/dev-knowledge/simulation-{type}.md` | Simulation results |

## Currently Supported Industries

| Industry | FAQs | Pipeline | Form | Reminders | Aftercare | Rebook |
|----------|------|----------|------|-----------|-----------|--------|
| Plumbing | 8 | contractor | contractor | Yes | auto_shop | No |
| Dental | 8 | dental | dental_intake | Yes | Yes (4 variants) | 180d |
| Real Estate | 8 | realestate | No | realestate | No | No |
| Salon | 6 | salon | No | Yes | Yes | 42d |
| Legal | 6 | legal | legal_intake | legal | No | No |
| Restaurant | 4 | restaurant | No | No | No | No |
| Auto Shop | 5 | No (uses generic) | No | auto_shop | Yes | No |
| Medical | 5 | No (alias→dental) | medical_intake | medical | Yes | 365d |
| Fitness | 5 | No (uses generic) | No | Yes | Yes | 30d |

## Quality Checklist
- [ ] All FAQs are non-generic (mention specific services, not "contact us for details")
- [ ] Pipeline stages match the actual customer journey for that industry
- [ ] Form fields collect what the business actually needs (not generic fields)
- [ ] Reminder items are practical ("bring insurance card" not "bring documents")
- [ ] Aftercare instructions are medically/professionally accurate
- [ ] Rebook interval matches industry norms (dental: 6mo, salon: 6wk, etc.)
