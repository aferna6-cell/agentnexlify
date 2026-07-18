"""Admin voice test call - close the voice-stack E2E loop without a human.

The voice stack is verified to Twilio's edge (signature gate 403s unsigned
requests, webhook sync points numbers at /voice/incoming, 75 local tests),
but zero real calls have ever exercised it because "make a phone call" was
an operator-only step. This endpoint uses our own Twilio credentials to
place a REAL call from one of our numbers to another: Twilio dials the
target, the target number's voice webhook (our /voice/incoming) answers
with real signed traffic, and the caller leg speaks a test question so the
Gather/respond loop runs. Result: a calls row + genuine end-to-end proof,
triggered by automation.

Admin-secret gated (same guard as /admin/loop-health). Both numbers must
be E.164; the call is real and bills normal Twilio rates (~$0.02).
"""

import logging
import re

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.routers.admin_health import _verify_admin_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")

_DEFAULT_SAY = (
    "Hello, this is an automated end to end test of the AgentNexLiFy "
    "voice stack. What are your business hours?"
)


class VoiceTestCallRequest(BaseModel):
    from_number: str = Field(..., max_length=20)
    to_number: str = Field(..., max_length=20)
    say: str = Field(default=_DEFAULT_SAY, max_length=500)


@router.post("/voice-test-call")
@limiter.limit("10/minute")
async def voice_test_call(
    request: Request,
    req: VoiceTestCallRequest,
    x_api_secret: str | None = Header(None),
):
    """Place a Twilio call from one of our numbers to another."""
    _verify_admin_secret(x_api_secret)

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise HTTPException(status_code=503, detail="Twilio is not configured")

    if not _E164.match(req.from_number) or not _E164.match(req.to_number):
        raise HTTPException(status_code=422, detail="Numbers must be E.164 (+1...)")
    if req.from_number == req.to_number:
        raise HTTPException(status_code=422, detail="from and to must differ")

    # The TwiML runs on the OUTBOUND leg once the callee answers: pause so
    # the callee's greeting starts, ask the test question, then stay on the
    # line long enough for the AI to respond before hanging up.
    safe_say = re.sub(r"[<>&]", " ", req.say)
    twiml = (
        "<Response>"
        '<Pause length="2"/>'
        f"<Say>{safe_say}</Say>"
        '<Pause length="20"/>'
        "</Response>"
    )

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Calls.json"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                data={
                    "From": req.from_number,
                    "To": req.to_number,
                    "Twiml": twiml,
                },
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
    except Exception:
        logger.exception("voice-test-call: Twilio request failed")
        raise HTTPException(status_code=502, detail="Twilio request failed")

    if resp.status_code >= 400:
        logger.error(
            "voice-test-call: Twilio rejected call (%s): %s",
            resp.status_code,
            resp.text[:300],
        )
        raise HTTPException(
            status_code=502, detail=f"Twilio rejected the call ({resp.status_code})"
        )

    body = resp.json()
    logger.info(
        "voice-test-call: placed %s -> %s sid=%s",
        req.from_number,
        req.to_number,
        body.get("sid"),
    )
    return {
        "call_sid": body.get("sid"),
        "status": body.get("status"),
        "from_number": req.from_number,
        "to_number": req.to_number,
        "verify": "check GET /api/v1/admin/loop-health and the calls table in ~60s",
    }
