"""Pure helpers extracted from scheduled_jobs_ext.py.

Metrics gathering (DB reads), AI prompt construction, HTML email composition,
and invoice math. Orchestration (send_email, fire_event, dedup writes) stays
in scheduled_jobs_ext.py so tests patching that module's namespace still work.
"""
