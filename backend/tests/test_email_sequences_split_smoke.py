"""Smoke tests for the email_sequences god-class split (Rule 9).

backend/routers/email_sequences.py (1143 lines) was split into:
- email_crud.py       — sequence/step CRUD endpoints + Pydantic models
- email_enrollment.py — enroll/unenroll/enrollment state + auto-enroll helper
- email_processor.py  — send loop / scheduling / processing

These tests characterize the public surface: the combined route set must be
byte-for-byte identical to the pre-split router (captured 2026-07-23), and
the symbols other modules import must live where the importers now point.
"""

from backend.route_introspection import route_signatures
from backend.routers import email_crud, email_enrollment, email_processor

# (method, path) pairs captured from the pre-split email_sequences.router.
EXPECTED_ROUTES = {
    ("GET", "/api/v1/email-sequences"),
    ("POST", "/api/v1/email-sequences"),
    ("POST", "/api/v1/email-sequences/internal/process-sequences"),
    ("DELETE", "/api/v1/email-sequences/{sequence_id}"),
    ("GET", "/api/v1/email-sequences/{sequence_id}"),
    ("PUT", "/api/v1/email-sequences/{sequence_id}"),
    ("POST", "/api/v1/email-sequences/{sequence_id}/enroll"),
    ("GET", "/api/v1/email-sequences/{sequence_id}/enrollments"),
    ("POST", "/api/v1/email-sequences/{sequence_id}/steps"),
    ("DELETE", "/api/v1/email-sequences/{sequence_id}/steps/{step_id}"),
    ("PUT", "/api/v1/email-sequences/{sequence_id}/steps/{step_id}"),
}


def _routes(router):
    return route_signatures(router)


def test_combined_route_set_matches_pre_split():
    combined = (
        _routes(email_crud.router)
        | _routes(email_enrollment.router)
        | _routes(email_processor.router)
    )
    assert combined == EXPECTED_ROUTES


def test_no_route_duplicated_across_modules():
    total = (
        len(_routes(email_crud.router))
        + len(_routes(email_enrollment.router))
        + len(_routes(email_processor.router))
    )
    assert total == len(EXPECTED_ROUTES)


def test_routers_share_prefix_and_tags():
    for mod in (email_crud, email_enrollment, email_processor):
        assert mod.router.prefix == "/api/v1/email-sequences"
        assert mod.router.tags == ["email-sequences"]


def test_crud_module_public_surface():
    for name in (
        "StepCreate",
        "StepUpdate",
        "SequenceCreate",
        "SequenceUpdate",
        "list_sequences",
        "create_sequence",
        "get_sequence",
        "update_sequence",
        "delete_sequence",
        "add_step",
        "update_step",
        "delete_step",
        "_count_by_sequence_id",
    ):
        assert hasattr(email_crud, name), name


def test_enrollment_module_public_surface():
    # enroll_lead_in_sequences is the widget_lead auto-enroll entry point.
    for name in (
        "EnrollRequest",
        "enroll_lead_in_sequences",
        "_enroll_lead",
        "list_enrollments",
        "enroll_lead",
    ):
        assert hasattr(email_enrollment, name), name


def test_processor_module_public_surface():
    # run_sequence_processor is the automation-loop callable used by main.py.
    for name in (
        "run_sequence_processor",
        "process_sequences",
        "_process_pending_sends",
        "_query_due_sends",
        "_update_send_status",
        "_maybe_complete_enrollment",
        "_increment_runs_total",
    ):
        assert hasattr(email_processor, name), name


def test_main_app_exposes_all_email_sequence_routes():
    import os

    os.environ.setdefault("TESTING", "1")
    from backend.main import app

    app_routes = {
        (method, path)
        for method, path in route_signatures(app)
        if path.startswith("/api/v1/email-sequences")
    }
    assert app_routes == EXPECTED_ROUTES
