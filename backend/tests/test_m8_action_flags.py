"""Milestone 8 calendar/CRM flags default off."""

import os

from backend.services.m8_action_flags import (
    CALENDAR_ACTIONS_FLAG,
    CRM_ACTIONS_FLAG,
    calendar_actions_enabled,
    crm_actions_enabled,
)


def test_calendar_crm_flags_default_off(monkeypatch):
    monkeypatch.delenv(CALENDAR_ACTIONS_FLAG, raising=False)
    monkeypatch.delenv(CRM_ACTIONS_FLAG, raising=False)
    assert calendar_actions_enabled() is False
    assert crm_actions_enabled() is False


def test_calendar_crm_flags_truthy(monkeypatch):
    monkeypatch.setenv(CALENDAR_ACTIONS_FLAG, "1")
    monkeypatch.setenv(CRM_ACTIONS_FLAG, "true")
    assert calendar_actions_enabled() is True
    assert crm_actions_enabled() is True
    monkeypatch.setenv(CALENDAR_ACTIONS_FLAG, "0")
    monkeypatch.setenv(CRM_ACTIONS_FLAG, "no")
    assert calendar_actions_enabled() is False
    assert crm_actions_enabled() is False
