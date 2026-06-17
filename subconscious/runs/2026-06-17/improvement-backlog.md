# Improvement Backlog — 2026-06-17

## Active
- Fix GH #308 — webhook idempotency retry-drop bug in billing.py + stripe_webhooks.py (AUTONOMOUS-EXECUTABLE, ~8 lines, 2 files + test)

## Parking Lot (survived debate, not chosen)

- **email_sequences N+1 fix (GH #112, ROI 2.3)** — bulk `.in_()` queries for list_enrollments + list_sequences. WEAKENED: run 41 email split pending supersedes this; fix N+1 AFTER split so work isn't duplicated. Promote after split complete.
- **AI-to-Human Handoff v1** — explicit trigger in widget_chat.py → SMS via os_outbound_mirror. WEAKENED: (1) moratorium pending ~9 human-required items; (2) widget_chat.py 1307L prerequisite split not done. Block: promote after widget_chat split complete AND moratorium pending ≤ 5.
- **widget_chat.py god-class split (1307L)** — extract widget_session.py + widget_lead_capture.py. WEAKENED: active PR traffic (3 PRs in 3 days touching widget ecosystem); email_sequences split mechanism unproven. Block: promote when PR rate on widget drops below 1/week AND email_sequences split completes as proof-of-mechanism.
- **Fix kb-autopopulate.sh** — replace agent-browser CLI with WebFetch/curl or add guard. ROI 1.8, operational. Promote when other higher-ROI items clear.

## Rejected This Run
- None promoted to rejected_paths (all ideas survived debate at some level).

## Questions for Next Run
1. Was GH #308 idempotency fix implemented by nightly? Check billing.py:235 for the `_cached is not None` guard.
2. Has email_sequences.py split (run 41) been implemented? If yes, fix N+1 queries and consider widget_chat split.
3. What is the current moratorium pending count after run 58/59 governance corrections? If ≤ 5, AI-to-Human Handoff becomes viable.
4. Has any new god-class file exceeded 600L since the last check? (Currently: widget_chat 1307L, email_sequences 1143L, invoices 1243L, onboarding 1206L, leads 1176L — all pending split.)
