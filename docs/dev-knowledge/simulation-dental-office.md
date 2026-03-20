# Customer Simulation: Dental Office
Date: 2026-03-19

## Persona
Dr. Sarah Chen, DDS. Runs a small dental practice (2 dentists, 3 hygienists). Tech-comfortable but not a developer. Uses Instagram and Google My Business. Pain points: high no-show rate, slow insurance verification, patients leaving after cleanings without scheduling next visit.

## Journey
1. **Signup** — Business name, type "dental" selected. Phone + website collected. FAQs auto-generated (4 dental-specific). Works well.
2. **Onboarding** — Widget configured, colors set, business hours set. Services added ("Cleaning", "Exam", "Filling", "Root Canal"). Missing: no HIPAA acknowledgment step.
3. **Widget chat** — AI answers dental questions using FAQ knowledge. Can recommend booking. Works well for general inquiries.
4. **Booking** — Patients can book slots. "Reason for visit" field added (Cycle 108). But no service-specific slot duration or provider filtering.
5. **Reminders** — Generic "Your appointment is tomorrow" messages. Don't mention service type or pre-appointment instructions.
6. **Follow-up** — Welcome email sequence works. No dental-specific aftercare or rebook-in-6-months automation.
7. **Reviews** — One-click review request works. Generic messaging, not dental-specific.

## Gaps Found (Priority Order)
1. **Service type in appointments** → Cleaning (30min) vs root canal (90min) need different durations. Added to backlog.
2. **Patient intake forms** → Health history, insurance info, consent. Form builder exists but no dental preset. Added to backlog.
3. **Insurance fields in leads** → carrier, member ID, group number. Added to backlog.
4. **Dental-aware reminders** → "Bring insurance card", "Don't eat before procedure". Added to backlog.
5. **HIPAA compliance messaging** → Legal requirement for healthcare businesses. Added to backlog.
6. **Post-appointment care instructions** → Aftercare based on service performed. Added to backlog.
7. **Rebook automation** → "Schedule your next cleaning in 6 months". Added to backlog.
8. **More dental FAQs** → Cancellation policy, payment plans, new patient process, costs.

## Strengths
- AI chat handles dental questions well with auto-generated FAQs
- Booking flow works (basic)
- Lead capture + scoring works
- Review request system works
- Invoice system with deposits works (patient deposits for big procedures)

## Verdict
A dental office would pay for the product TODAY for basic appointment booking + lead capture + follow-up sequences. But they'd switch to a dental-specific tool within 3 months unless we add: service-based scheduling, patient forms, insurance tracking, and HIPAA compliance messaging. The most impactful quick win is dental-aware appointment reminders (mention what to bring, service type).
