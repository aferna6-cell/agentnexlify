"""Tests for confidence-gated retrieval with human escalation (widget chat).

Covers `is_low_confidence_turn` in backend.routers.widget_chat_helpers — the
signal that decides whether a widget chat turn should be routed to human
handoff instead of returned as the model's (possibly hallucinated) answer.

Two independent signals must BOTH hold before a turn is treated as
low-confidence (conservative by design — see the docstring block above
`is_low_confidence_turn` in widget_chat_helpers.py for the full rationale):

1. Retrieval is thin — the per-message KB article search
   (`_query_kb_articles`) returned nothing, or its best "similarity" score
   is below `KB_CONFIDENCE_THRESHOLD`.
2. The model's own answer reads uncertain (hedges — "I don't know",
   "I'm not sure", etc.).

The gate only evaluates messages that read like real informational
questions — chit-chat is skipped so it is never misrouted to a
human-handoff reply just because it has no relevant KB article match.

Two test classes:
- TestIsLowConfidenceTurn — direct unit tests on the production gating
  function (retrieval is mocked via the kb_article_refs argument, the LLM
  output is mocked via the assistant_text argument).
- TestWidgetChatConfidenceGateWiring — mirrors the widget_chat.py step 9bb
  wiring (same pattern used by backend/tests/test_widget_kb_retrieval.py's
  `_simulate_chat_path`) to prove the endpoint-level behavior: low
  confidence swaps in the escalation fallback, high confidence leaves the
  answer untouched, and an exception in the confidence check falls back to
  the model's answer unchanged.
"""

import os

os.environ.setdefault("TESTING", "1")

from unittest.mock import patch

import pytest

from backend.routers.widget_chat_helpers import (
    KB_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_FALLBACK_TEXT,
    is_low_confidence_turn,
)


# ---------------------------------------------------------------------------
# Fixtures — mocked retrieval results
# ---------------------------------------------------------------------------

_LOW_SCORE_REFS = [
    {"id": "art-1", "title": "Unrelated Article", "summary": "n/a", "similarity": 0.02},
]

_HIGH_SCORE_REFS = [
    {
        "id": "art-2",
        "title": "Refund Policy",
        "summary": "Refunds processed within 5 business days.",
        "similarity": 0.91,
    },
]

_HEDGING_ANSWER = "I'm not sure about that — I don't have that information handy."
_CONFIDENT_ANSWER = "Refunds are processed within 5 business days of the request."


# ---------------------------------------------------------------------------
# Unit tests — is_low_confidence_turn
# ---------------------------------------------------------------------------


class TestIsLowConfidenceTurn:
    def test_low_score_plus_hedging_answer_is_low_confidence(self):
        assert is_low_confidence_turn(
            message="What is your refund policy for custom orders?",
            kb_article_refs=_LOW_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is True

    def test_empty_retrieval_plus_hedging_answer_is_low_confidence(self):
        assert is_low_confidence_turn(
            message="Do you offer emergency service on weekends?",
            kb_article_refs=[],
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is True
        assert is_low_confidence_turn(
            message="Do you offer emergency service on weekends?",
            kb_article_refs=None,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is True

    def test_high_score_is_not_low_confidence_even_with_hedging_answer(self):
        """A strong KB article match means the retrieval signal alone clears
        the gate — thin retrieval is required, so a hedging answer with good
        context does not trigger escalation."""
        assert is_low_confidence_turn(
            message="What is your refund policy?",
            kb_article_refs=_HIGH_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is False

    def test_low_score_but_confident_answer_is_not_low_confidence(self):
        """Thin KB article match alone is not enough — the tenant's answer
        may be grounded in FAQ/knowledge_base/custom_instructions, none of
        which factor into the KB article search score. Only escalate when
        the model's own answer ALSO hedges."""
        assert is_low_confidence_turn(
            message="What is your refund policy?",
            kb_article_refs=_LOW_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_CONFIDENT_ANSWER,
        ) is False

    def test_retrieval_not_attempted_never_triggers(self):
        """kb_retrieval_attempted=False (feature disabled this turn) must
        never be treated as thin retrieval."""
        assert is_low_confidence_turn(
            message="What is your refund policy?",
            kb_article_refs=[],
            kb_retrieval_attempted=False,
            assistant_text=_HEDGING_ANSWER,
        ) is False

    def test_chitchat_message_never_triggers(self):
        """Chit-chat has no relevant KB article match by definition — that's
        expected, not a confidence problem, so the gate must skip it."""
        for message in ("thanks!", "ok sounds good", "great, thank you"):
            assert is_low_confidence_turn(
                message=message,
                kb_article_refs=[],
                kb_retrieval_attempted=True,
                assistant_text=_HEDGING_ANSWER,
            ) is False

    def test_question_lead_word_without_question_mark_counts(self):
        """'how much does it cost' (no '?') still reads as informational."""
        assert is_low_confidence_turn(
            message="how much does it cost",
            kb_article_refs=[],
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is True

    def test_threshold_boundary(self):
        """Score exactly at KB_CONFIDENCE_THRESHOLD clears the gate (>=, not >)."""
        boundary_refs = [{"id": "x", "similarity": KB_CONFIDENCE_THRESHOLD}]
        assert is_low_confidence_turn(
            message="What are your hours?",
            kb_article_refs=boundary_refs,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
        ) is False


# ---------------------------------------------------------------------------
# Wiring tests — mirrors widget_chat.py step 9bb
# ---------------------------------------------------------------------------
#
# Same approach as backend/tests/test_widget_kb_retrieval.py's
# `_simulate_chat_path`: reimplement the small wiring block from
# widget_chat.py against the REAL production function
# (`widget_chat.is_low_confidence_turn`, imported into the widget_chat
# module) so a patch on that name exercises the exact call site used in
# production, without needing a full FastAPI/DB/Anthropic-mocked endpoint
# call.


def _simulate_confidence_gate_step(
    *,
    message: str,
    kb_article_refs,
    kb_retrieval_attempted: bool,
    assistant_text: str,
    ai_fallback_fired: bool,
):
    """Mirrors widget_chat.py step 9bb exactly."""
    from backend.routers import widget_chat

    if not ai_fallback_fired and "HANDOFF_REQUESTED" not in assistant_text:
        try:
            if widget_chat.is_low_confidence_turn(
                message=message,
                kb_article_refs=kb_article_refs,
                kb_retrieval_attempted=kb_retrieval_attempted,
                assistant_text=assistant_text,
            ):
                assistant_text = LOW_CONFIDENCE_FALLBACK_TEXT
        except Exception:
            pass  # non-fatal — keep assistant_text unchanged, mirrors production
    return assistant_text


class TestWidgetChatConfidenceGateWiring:
    def test_low_confidence_swaps_in_escalation_fallback(self):
        """Mocked retrieval (thin) + mocked LLM output (hedging) → the
        response is the graceful escalation fallback, not the model's
        possibly-hallucinated answer, and it ends in HANDOFF_REQUESTED so
        the existing handoff pipeline (tag/notify/webhook) fires."""
        result = _simulate_confidence_gate_step(
            message="What is your refund policy for custom orders?",
            kb_article_refs=_LOW_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
            ai_fallback_fired=False,
        )
        assert result == LOW_CONFIDENCE_FALLBACK_TEXT
        assert result.endswith("HANDOFF_REQUESTED")
        assert _HEDGING_ANSWER not in result

    def test_high_confidence_leaves_answer_unchanged(self):
        """Mocked retrieval (strong match) + mocked LLM output → the
        high-confidence answer path is untouched (backward compatible)."""
        result = _simulate_confidence_gate_step(
            message="What is your refund policy?",
            kb_article_refs=_HIGH_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_CONFIDENT_ANSWER,
            ai_fallback_fired=False,
        )
        assert result == _CONFIDENT_ANSWER
        assert "HANDOFF_REQUESTED" not in result

    def test_confidence_check_exception_falls_back_to_model_answer(self):
        """If is_low_confidence_turn raises, the model's answer is returned
        unchanged — the confidence gate must never break the chat response."""
        with patch(
            "backend.routers.widget_chat.is_low_confidence_turn",
            side_effect=RuntimeError("simulated failure"),
        ):
            result = _simulate_confidence_gate_step(
                message="What is your refund policy for custom orders?",
                kb_article_refs=_LOW_SCORE_REFS,
                kb_retrieval_attempted=True,
                assistant_text=_CONFIDENT_ANSWER,
                ai_fallback_fired=False,
            )
        assert result == _CONFIDENT_ANSWER
        assert "HANDOFF_REQUESTED" not in result

    def test_skipped_when_ai_fallback_already_fired(self):
        """The managed-agent fallback (step 9ba) already handled this turn —
        the confidence gate must not run a second time on top of it."""
        result = _simulate_confidence_gate_step(
            message="What is your refund policy for custom orders?",
            kb_article_refs=_LOW_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=_HEDGING_ANSWER,
            ai_fallback_fired=True,
        )
        assert result == _HEDGING_ANSWER

    def test_skipped_when_handoff_marker_already_present(self):
        """The model already asked for a human itself — no need to swap in
        the confidence-gate fallback on top of an existing handoff."""
        already_handoff = "Let me get someone for you.\nHANDOFF_REQUESTED"
        result = _simulate_confidence_gate_step(
            message="What is your refund policy for custom orders?",
            kb_article_refs=_LOW_SCORE_REFS,
            kb_retrieval_attempted=True,
            assistant_text=already_handoff,
            ai_fallback_fired=False,
        )
        assert result == already_handoff


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
