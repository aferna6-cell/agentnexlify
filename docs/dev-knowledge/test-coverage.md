# Test Coverage — AgentNexLiFy

191 tests across 13 test files. All use FastAPI TestClient with mocked Supabase.

## Test Files

| File | Tests | Coverage Area |
|------|-------|---------------|
| test_calls.py | 31 | AI Answering Service — voice webhooks, transcription, AI summary, call CRUD, stats |
| test_lead_extraction.py | 26 | Widget lead capture — name/email/phone extraction, dedup, partial info |
| test_business_page.py | 26 | Business page — valid/invalid slugs, special chars, team invite validation |
| test_webhook_delivery.py | 20 | Outbound webhooks — delivery, retry logic, event types |
| test_local_seo.py | 19 | Local SEO — profile analysis, scoring, keywords, dashboard widget |
| test_booking_overlap.py | 16 | Appointments — overlapping time slots, booking conflicts |
| test_client_portal.py | 15 | Client Portal — service records CRUD, portal token generation, public portal |
| test_login_and_chat.py | 10 | Auth + chat — login flow, chat edge cases, lead capture edge cases |
| test_stripe_webhook.py | 7 | Stripe — webhook signature verification, event routing |
| test_cors_and_rate_limit.py | 7 | CORS headers, rate limit decorators, automation sequences |
| test_auth_endpoints.py | 6 | Registration — duplicate email, successful register, validation |
| test_appointments.py | 5 | Appointments — create, past date, list, status update, cancel |
| test_google_calendar.py | 3 | Google Calendar OAuth — status, disconnect, connected |

## What's Tested

- Auth: signup, login, duplicate detection, password validation
- Widget: chat endpoint, lead extraction, config, offline mode, CORS
- Leads: extraction, dedup, partial info, international phone, malformed email
- Appointments: CRUD, overlap detection, status transitions, recurring
- Webhooks: delivery, retry, Stripe signature verification
- Integrations: Google Calendar OAuth status
- Calls: voice webhooks, transcription, AI summary, action items from calls
- Local SEO: profile scoring, keyword generation
- Client Portal: service records, portal tokens, public portal
- Rate limiting: decorator verification on public endpoints
- Automation: sequence creation from templates, stats aggregation

## What's NOT Tested (Known Gaps)

- Widget file upload (Supabase Storage mock complexity)
- SMS delivery (Twilio API mock — would need httpx mock)
- Email delivery (Resend API mock)
- Claude AI response quality (mocked in tests, not integration-tested)
- Frontend React components (no Vitest/Jest setup)
- MCP server tools (need MCP test client)
- Chrome Extension (needs browser test framework)
- Performance under load (no k6/locust tests)
- Cross-worker automation dedup (needs multi-process test)

## Running Tests

```bash
cd /home/aidan/agentnexlify
python3 -m pytest tests/ -q --timeout=30

# Run specific file
python3 -m pytest tests/test_calls.py -v --timeout=30

# Run specific test
python3 -m pytest tests/test_auth_endpoints.py::TestRegister::test_successful_register -v
```

## Test Patterns

All tests follow the same pattern:
1. `os.environ["TESTING"] = "1"` to skip automation loop
2. `mock_settings` fixture for config
3. `test_client` fixture with patched `get_supabase` in all relevant modules
4. `_setup_table_mock()` helper for configurable mock responses
5. `_cache.clear()` in fixture teardown for widget cache isolation
6. JWT tokens generated via `jose.jwt.encode` with test secret

## Adding Tests

1. Create `tests/test_<module>.py`
2. Copy fixture pattern from `test_auth_endpoints.py`
3. Patch `get_supabase` in every module your endpoint imports from
4. Clear widget `_cache` in fixture teardown
5. Run full suite to check for cross-test contamination
