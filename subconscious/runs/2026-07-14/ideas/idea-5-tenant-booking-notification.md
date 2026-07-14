# Idea 5 — Tenant Email Notification on New Appointment Booking

## Category
customer_value

## Effort
S (new email template + appointment_service.py modification)

## Evidence
- 0 real bookings after 22 days; when first booking occurs, tenant has no notification mechanism
- appointment_service.py handles booking creation but sends no alert to the business owner
- Resend is integrated (email to customer works for appointment reminders)
- customer-gaps.md: "business owner notification on new appointment" not listed but is industry-standard
- dental, HVAC, salon verticals: owner expects SMS/email within seconds of booking (missed bookings = missed revenue)

## Action
Modify `backend/services/appointment_service.py`:
After `create_appointment()` succeeds, send Resend transactional email to tenant's configured notification email:
"New appointment booked! [customer name] at [datetime] for [service]. View in dashboard."

## Expected Impact
When the first real booking occurs (Keys Koffee hours → booking), the owner gets immediate notification.
Prevents the common SMB pattern: booking slips through because owner didn't check the dashboard.
Increases perceived product value ("the system notified me instantly").

## Risk
Medium. Requires tenant notification email configuration (may not be set for all tenants). Resend send failure on new booking shouldn't block the booking itself — async or best-effort only.

## Autonomy
Requires nightly-commit-review (production appointment_service.py change). Human review recommended.
