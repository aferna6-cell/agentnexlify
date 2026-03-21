# Customer Simulation: Law Firm
Date: 2026-03-21

## Persona
Jennifer Park, managing partner at a 3-attorney family law firm. Handles divorce, custody, estate planning. Tech-savvy but busy. Pain points: screening unqualified inquiries, managing client document signing, tracking case progress.

## Journey
1. **Signup** — "legal" type selected. 6 FAQs auto-generated (practice areas, consultations, confidentiality, what to bring, fees, timeline). Good coverage.
2. **Widget chat** — AI answers basic questions about the firm. Directs to consultation booking. Confidentiality FAQ establishes trust.
3. **Consultation booking** — Service types allow "Free Consultation (30min)" vs "Case Review (60min)". Reminder says "Bring relevant documents." Works.
4. **Client intake** — Form presets don't include a legal intake form. Would need: case type, opposing party, court jurisdiction, deadline, retainer agreement consent.
5. **Documents** — Can send retainer agreements, engagement letters for e-signature. Works for basic contract signing.
6. **Pipeline** — Auto-seeds legal stages: Inquiry → Consultation → Retained → Active Case → Resolved → Declined. Good match.
7. **Follow-up** — Welcome email sequence works. No legal-specific sequences.
8. **Invoicing** — Can create invoices for legal fees with deposit required. Partial payments work.

## Gaps Found
1. **No legal intake form preset** — Need case type, opposing party, jurisdiction fields. Minor (can use form builder).
2. **No conflict check** — When a new lead comes in, should check if opposing party is already a client. Feature gap.
3. **No matter/case number tracking** — Custom fields exist but no dedicated case management. Could use pipeline + custom fields.
4. **No billable hours tracking** — Lawyers track time per task. Would need a time tracking module.
5. **No retainer balance tracking** — Track how much of the retainer has been used. Could extend invoicing.

## Strengths
- Confidentiality FAQ establishes trust immediately
- Consultation booking with service types works perfectly
- Document e-signatures for retainer agreements
- Legal pipeline preset matches case workflow
- Invoice deposits work for retainers
- "What to bring" reminder is contextually appropriate
- Professional tone in all communications

## Verdict
A small law firm would pay for this TODAY for consultation booking + document signing + client communication. The platform handles the front-end client acquisition well. For ongoing case management, they'd need a dedicated legal practice management tool — but AgentNexLiFy covers the intake-to-retained pipeline effectively. Missing: legal intake form preset, conflict check, billable hours.
