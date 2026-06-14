"""Escaping tests for the TwiML builders — the XML-injection defense.

Every user-influenced value (business name, AI reply text) flows through
these builders into XML parsed by Twilio. A failed escape is an injection
vector into live phone calls.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.voice_twiml import (
    _build_twiml_gather,
    _build_twiml_goodbye,
    _build_twiml_greeting,
    _xml_escape,
)


def test_xml_escape_covers_all_metacharacters():
    assert _xml_escape("&") == "&amp;"
    assert _xml_escape("<") == "&lt;"
    assert _xml_escape(">") == "&gt;"
    assert _xml_escape('"') == "&quot;"
    assert _xml_escape("'") == "&apos;"
    # ampersand escaped first — no double-escaping of entities
    assert _xml_escape("<a & 'b'>") == "&lt;a &amp; &apos;b&apos;&gt;"


def test_malicious_business_name_cannot_break_out_of_say():
    evil = 'Bob\'s "Shop" </Say><Dial>+15551234567</Dial><Say>'
    twiml = _build_twiml_greeting(evil, "https://x/cb")
    # The raw injection payload must not survive into the XML
    assert "<Dial>" not in twiml
    assert "</Say><Dial>" not in twiml
    assert "&lt;Dial&gt;" in twiml
    assert "&apos;" in twiml and "&quot;" in twiml


def test_gather_and_goodbye_escape_ai_reply_text():
    evil = "Press 1 </Say></Gather><Redirect>https://evil.example</Redirect>"
    gather = _build_twiml_gather(evil, "https://x/respond", 1)
    goodbye = _build_twiml_goodbye(evil)
    for twiml in (gather, goodbye):
        assert "<Redirect>" not in twiml
        assert "&lt;Redirect&gt;" in twiml
