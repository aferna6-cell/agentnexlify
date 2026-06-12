"""Integrity checks for industry FAQ seed packs.

Home-services depth pass (2026-06): plumbing/hvac grew to 8 questions and
home_services to 8, matching the dental/realestate depth bar. These tests
pin pack sizes, uniqueness, and required fields so future edits can't
silently shrink or duplicate a pack.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.industry_faqs import INDUSTRY_FAQS

_DEPTH_BAR = {"plumbing": 8, "hvac": 8, "home_services": 8, "dental": 8, "realestate": 8, "salon": 8}


def test_home_trades_meet_depth_bar():
    for industry, minimum in _DEPTH_BAR.items():
        assert len(INDUSTRY_FAQS[industry]) >= minimum, industry


def test_no_duplicate_questions_within_any_pack():
    for industry, faqs in INDUSTRY_FAQS.items():
        questions = [f["question"].strip().lower() for f in faqs]
        assert len(questions) == len(set(questions)), industry


def test_every_faq_has_required_fields():
    for industry, faqs in INDUSTRY_FAQS.items():
        for faq in faqs:
            assert faq.get("question"), industry
            assert faq.get("answer"), industry
            assert faq.get("category"), industry
