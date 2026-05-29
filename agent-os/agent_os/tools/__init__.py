"""Agent OS tools — small, offline-safe utilities agents call out to.

Each tool degrades honestly when it can't run (no network, missing input) so
the agents that use it never fabricate a result.
"""
