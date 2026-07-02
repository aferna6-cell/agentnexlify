# Idea 3: Custom Automation Templates (Cross-Industry)

**Category:** customer_value  
**Effort:** Medium  
**AUTONOMOUS-EXECUTABLE:** NO  

## Evidence

`docs/dev-knowledge/customer-gaps.md` lists "Custom automation templates" as open, cross-industry gap affecting all 6 simulation verticals. "Custom birthday messages, post-service follow-ups" cited. Agent OS `os_outbound_mirror.py` shipped with SMS/email/FB infrastructure (152 tests, PR #188, 2026-05-27).

## Action

Add a template library concept to the dashboard:
1. Pre-built automation sequences (birthday reminder → thank you, post-service follow-up at 48h, re-engagement at 30-day silence)
2. One-click activation per tenant from Automations dashboard page
3. Backend: `automation_templates` table + `POST /api/v1/automations/templates/{id}/activate`
4. Frontend: new tab in AutomationsPage.jsx listing templates with preview + activate button

## Expected Impact

- Cross-industry upsell — applies to all 6 verticals
- Differentiates from GoHighLevel's manual workflow builder with "one-click"
- Leverages shipped Agent OS infrastructure

## Why Not Winner

Moratorium active. Medium effort adds to human approval queue (true pending already at threshold). Re-evaluate after moratorium lifts.
