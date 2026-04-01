-- Migration 074: Add lead_captured flag to conversations table
-- Tracks whether a lead was captured during a chat conversation.
-- Populated by _capture_leads_from_session background task in widget_helpers.py.

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS lead_captured BOOLEAN NOT NULL DEFAULT false;
