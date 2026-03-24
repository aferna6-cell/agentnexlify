# Lessons Learned
_Append-only. Never delete entries. This is institutional memory._

## 2026-03-24
- **API client must handle 204 No Content**: The shared `request()` function in `_client.js` was calling `res.json()` on every response, including 204 No Content from DELETE endpoints. This silently broke delete operations across 20+ modules. Fix: check `res.status === 204` and empty body text before parsing.
- **sms_sender vs twilio_service**: The SMS sending function lives in `backend/services/twilio_service.py` (not `sms_sender.py`). Import path: `from backend.services.twilio_service import send_sms`.
- **Python deps not in requirements.txt**: The project has many pip packages not tracked in a requirements file. When cloning fresh, need to install: fastapi, uvicorn, pydantic, pydantic-settings, supabase, httpx, python-jose, python-multipart, slowapi, anthropic, resend, twilio, stripe, python-json-logger, bcrypt, email-validator, google-auth, google-auth-oauthlib, google-api-python-client, cffi, cryptography, mcp, qrcode, pillow.
- **git branch is `master` locally but remote is `main`**: Push with `git push -u origin master:main`.
- **Conversations table uses `client_id` not `tenant_id`**: Verified in conversation_inbox.py `_find_conversation()`. All queries correctly use `.eq("client_id", tenant_id)`.
