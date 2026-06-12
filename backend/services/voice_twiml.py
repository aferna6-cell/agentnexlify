"""TwiML response builders for the voice call webhooks.

Pure string-building helpers extracted from backend/routers/calls.py
(god-file split, 2026-06). Every user-supplied value is XML-escaped before
interpolation — keep it that way: TwiML is parsed as XML by Twilio and an
unescaped business name or AI reply is an injection vector.
"""

# Max AI conversation rounds before ending the call
MAX_VOICE_ROUNDS = 3


def _xml_escape(text: str) -> str:
    """Escape text for safe inclusion in XML."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _build_twiml_greeting(
    business_name: str,
    recording_callback_url: str,
    transcription_callback_url: str | None = None,
) -> str:
    """Build a TwiML response that greets the caller and records their message.

    If transcription_callback_url is provided, the <Record> verb will include
    transcribe="true" and transcriptionUrl so Twilio sends the transcribed text
    back to our transcription-complete endpoint automatically.
    """
    safe_name = _xml_escape(business_name)
    transcription_attrs = ""
    if transcription_callback_url:
        transcription_attrs = (
            ' transcribe="true"'
            f' transcriptionUrl="{transcription_callback_url}"'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Say voice=\"alice\">"
        f"Thanks for calling {safe_name}! "
        "We're not available right now, but your call is important to us. "
        "Please leave a message after the beep and we'll get back to you as soon as possible."
        "</Say>"
        "<Record"
        ' maxLength="120"'
        ' playBeep="true"'
        f' recordingStatusCallback="{recording_callback_url}"'
        ' recordingStatusCallbackMethod="POST"'
        f"{transcription_attrs}"
        " />"
        "<Say voice=\"alice\">We didn't receive a recording. Goodbye!</Say>"
        "</Response>"
    )


def _build_twiml_error() -> str:
    """Build a TwiML response for when we can't identify the tenant."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Say voice="alice">'
        "We're sorry, we're unable to take your call right now. Please try again later."
        "</Say>"
        "</Response>"
    )


def _build_twiml_gather(say_text: str, respond_url: str, round_num: int) -> str:
    """Build TwiML that speaks text and then gathers speech input.

    Uses <Gather> with speech input and a configurable action URL.
    After the gather timeout, falls back to a goodbye message.
    """
    safe_text = _xml_escape(say_text)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Gather input="speech" timeout="5" speechTimeout="auto"'
        f' action="{respond_url}?round={round_num}" method="POST">'
        f'<Say voice="alice">{safe_text}</Say>'
        "</Gather>"
        '<Say voice="alice">'
        "I didn't hear anything. Thank you for calling! Goodbye."
        "</Say>"
        "</Response>"
    )


def _build_twiml_goodbye(say_text: str) -> str:
    """Build TwiML that speaks a goodbye message and hangs up."""
    safe_text = _xml_escape(say_text)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="alice">{safe_text}</Say>'
        "</Response>"
    )
