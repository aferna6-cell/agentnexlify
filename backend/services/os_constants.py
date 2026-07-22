"""Shared Agent OS constants (audit 2026-07-22 M3).

INBOUND_THREAD_SOURCES was defined identically in os_thread_runner.py and
os_chat_projects.py; adding the "voice" channel meant remembering both
copies. One definition, imported by both. Threads originating from these
channels are customer-facing - the person typing cannot connect the
owner's integrations or start owner projects (os_inbound_bridge sources).
"""

INBOUND_THREAD_SOURCES = frozenset(
    {"widget", "email", "sms", "facebook", "instagram", "voice"}
)
