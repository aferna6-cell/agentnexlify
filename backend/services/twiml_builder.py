"""Pure TwiML response builders for Twilio voice webhooks.

XML-escape + greeting + error + gather + goodbye. No side effects, no I/O.
"""


def xml_escape(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_twiml_greeting(
    business_name: str,
    recording_callback_url: str,
    transcription_callback_url: str | None = None,
) -> str:
    """Greeting + Record verb. Optional transcription callback."""
    safe_name = xml_escape(business_name)
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


def build_twiml_error() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        '<Say voice="alice">'
        "We're sorry, we're unable to take your call right now. Please try again later."
        "</Say>"
        "</Response>"
    )


def build_twiml_gather(say_text: str, respond_url: str, round_num: int) -> str:
    """Speak text + <Gather> speech input. Falls back to goodbye on timeout."""
    safe_text = xml_escape(say_text)
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


def build_twiml_goodbye(say_text: str) -> str:
    safe_text = xml_escape(say_text)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="alice">{safe_text}</Say>'
        "</Response>"
    )
