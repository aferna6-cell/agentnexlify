# Idea 05 — Record Audit Dashboard

**Category:** Operational / Customer Value  
**Effort:** S (1 endpoint + 1 page, ~3 hours)  
**Confidence:** MEDIUM  
**Backend:** record_audit.py exists (council fix #7, 2026-06-24)

---

## The Gap

Council fix #7 shipped `backend/services/record_audit.py`. When leads are deleted via soft-delete or hard-delete through the propose-only record system, a snapshot is written to `activity_log.metadata`.

No admin or operator UI exists to view:
- Which leads were deleted and when
- Who triggered the deletion (tenant, system, automation)
- Rollback snapshot data
- Audit trail for compliance

This matters for businesses that must demonstrate data handling compliance (GDPR, state privacy laws, customer disputes).

---

## What to Build

### Backend (1 endpoint)
`GET /api/admin/audit-log` → returns:
- Recent delete events (last 50)
- Metadata preview (lead name, email, deletion reason)
- Rollback data (if snapshot exists in metadata)

### Frontend (1 page or modal)
`frontend/src/pages/AuditLogPage.jsx` (or audit tab in existing AdminPage)
- Table: timestamp, lead_id, lead_email, action, triggered_by
- Expandable row: full metadata snapshot
- Export to CSV

---

## Debate Considerations

NOT in top 3 this run. Valid future candidate.

SMS Compliance Dashboard outranks because:
- Legal liability is higher (TCPA vs general data hygiene)
- Opt-in/opt-out compliance is time-sensitive (active SMS campaigns)
- Audit log is valuable but not urgent — no business is sending delete-heavy workflows today

Park for run 71 or run 72. Re-evaluate when SMS Dashboard is shipped and usage data exists on how many delete events are actually occurring.
