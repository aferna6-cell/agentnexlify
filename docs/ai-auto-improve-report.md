# AI Auto Improve Report

## Registry
- Total skills: 4
- Repository skills: 4
- Generated skills: 0

## Memory
- Tasks recorded: 3
- Bug patterns: 0
- Architecture patterns: 2
- Refactor patterns: 3

## Generated Skills
- No new skills generated in this run.

## Schema Mismatch Risks
- `backend/services/google_calendar.py`: legacy plan names appear in active code
- `backend/services/lead_scoring.py`: leads table may be queried with tenant_id instead of client_id
- `backend/services/booking.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/analytics.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/sms.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/sequences.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/automations.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/auth.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/widget.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/widget.py`: legacy lead_stage naming is present in active code
- `backend/routers/clients.py`: leads table may be queried with tenant_id instead of client_id
- `backend/routers/leads.py`: leads table may be queried with tenant_id instead of client_id
- `frontend/src/pages/FreeWidget.jsx`: legacy plan names appear in active code
- `frontend/src/components/Sidebar.jsx`: legacy plan names appear in active code
- `frontend/src/components/ComparisonPage.jsx`: legacy plan names appear in active code
- `frontend/src/pages/Dashboard/OverviewCards.jsx`: legacy plan names appear in active code
- `widget/, public/`: multiple widget generations remain in the repository

## Duplicate Code Patterns
- frontend/vercel.json, vercel.json: Review whether these exact duplicates should share a single source of truth.
- frontend/public/widget/preview.html, widget/preview.html: Review whether these exact duplicates should share a single source of truth.
- frontend/public/widget/agentnexlify-widget.js, widget/agentnexlify-widget.js: Review whether these exact duplicates should share a single source of truth.

## Deprecated Or Legacy Surfaces
- `landing-page-v2/`: legacy static marketing pages still exist beside the React frontend
- `public/widget.js`: older standalone widget artifact still exists beside the production widget
- `_archive/`: archived backend and scripts remain available and may be mistaken for active code
