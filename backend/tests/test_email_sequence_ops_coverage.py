"""Service-level coverage for the extracted email_sequence ops modules.

The router (`backend/routers/email_sequences.py`) was split into three
service modules. Router-level mocks bypass them, so changed-lines
coverage (>=85%) needed direct service tests. These exercise:

- backend/services/email_sequence_enrollment_ops.py
- backend/services/email_sequence_sequence_ops.py
- backend/services/email_sequence_step_ops.py

Each public function gets happy-path + key error-path (404 / 500 / 400)
coverage using ``FakeSupabase`` so the real service code runs.
"""

import pytest
from fastapi import HTTPException

from backend.services.email_sequence_enrollment_ops import (
    _verify_sequence_for_listing,
    list_enrollments_for_sequence,
    manual_enroll_lead,
)
from backend.services.email_sequence_schemas import (
    SequenceCreate,
    SequenceUpdate,
    StepCreate,
    StepUpdate,
)
from backend.services.email_sequence_sequence_ops import (
    _enrich_sequence_counts,
    create_sequence_for_tenant,
    get_sequence_for_tenant,
    list_sequences_for_tenant,
    soft_delete_sequence,
    update_sequence_for_tenant,
)
from backend.services.email_sequence_step_ops import (
    add_step_to_sequence,
    delete_step_from_sequence,
    update_step_in_sequence,
    verify_sequence_ownership,
)
from backend.tests._fake_supabase import FakeSupabase


# ---------------------------------------------------------------------------
# email_sequence_enrollment_ops
# ---------------------------------------------------------------------------


def test_verify_sequence_for_listing_ok():
    db = FakeSupabase().configure(
        "email_sequences", data=[{"id": "s1", "name": "Welcome"}]
    )
    # no exception = pass
    _verify_sequence_for_listing(db, "tenant-1", "s1")


def test_verify_sequence_for_listing_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        _verify_sequence_for_listing(db, "tenant-1", "missing")
    assert exc.value.status_code == 404


def test_verify_sequence_for_listing_500_on_db_error():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        _verify_sequence_for_listing(db, "tenant-1", "s1")
    assert exc.value.status_code == 500


def test_list_enrollments_for_sequence_happy_path_with_lead():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome"}])
        .configure(
            "email_sequence_enrollments",
            data=[
                {"id": "e1", "lead_id": "l1", "sequence_id": "s1", "status": "active"},
            ],
        )
        .configure(
            "leads",
            data=[{"id": "l1", "name": "Alice", "email": "a@x.com", "phone": None, "status": "new"}],
        )
    )
    res = list_enrollments_for_sequence(db, "tenant-1", "s1")
    assert res["total"] == 1
    assert res["enrollments"][0]["lead"]["name"] == "Alice"


def test_list_enrollments_for_sequence_lead_lookup_failure_returns_none():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome"}])
        .configure(
            "email_sequence_enrollments",
            data=[{"id": "e1", "lead_id": "l1", "sequence_id": "s1", "status": "active"}],
        )
        .raise_on("leads")
    )
    res = list_enrollments_for_sequence(db, "tenant-1", "s1")
    assert res["total"] == 1
    assert res["enrollments"][0]["lead"] is None


def test_list_enrollments_for_sequence_empty_lead_data_returns_none():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome"}])
        .configure(
            "email_sequence_enrollments",
            data=[{"id": "e1", "lead_id": "l1", "sequence_id": "s1", "status": "active"}],
        )
        .configure("leads", data=[])
    )
    res = list_enrollments_for_sequence(db, "tenant-1", "s1")
    assert res["enrollments"][0]["lead"] is None


def test_list_enrollments_for_sequence_enrollment_query_fails_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome"}])
        .raise_on("email_sequence_enrollments")
    )
    with pytest.raises(HTTPException) as exc:
        list_enrollments_for_sequence(db, "tenant-1", "s1")
    assert exc.value.status_code == 500


def test_list_enrollments_for_sequence_sequence_missing_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        list_enrollments_for_sequence(db, "tenant-1", "missing")
    assert exc.value.status_code == 404


def test_manual_enroll_lead_sequence_not_found_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "missing", "l1")
    assert exc.value.status_code == 404


def test_manual_enroll_lead_sequence_query_fails_500():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "s1", "l1")
    assert exc.value.status_code == 500


def test_manual_enroll_lead_lead_not_found_404():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome", "is_active": True}])
        .configure("leads", data=[])
    )
    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "s1", "missing")
    assert exc.value.status_code == 404


def test_manual_enroll_lead_lead_query_fails_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome", "is_active": True}])
        .raise_on("leads")
    )
    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "s1", "l1")
    assert exc.value.status_code == 500


def test_manual_enroll_lead_steps_query_fails_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome", "is_active": True}])
        .configure("leads", data=[{"id": "l1", "name": "Alice", "email": "a@x.com"}])
        .raise_on("email_sequence_steps")
    )
    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "s1", "l1")
    assert exc.value.status_code == 500


def test_manual_enroll_lead_happy_path(monkeypatch):
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome", "is_active": True}])
        .configure("leads", data=[{"id": "l1", "name": "Alice", "email": "a@x.com"}])
        .configure(
            "email_sequence_steps",
            data=[
                {"id": "st1", "step_order": 1, "is_active": True},
                {"id": "st2", "step_order": 2, "is_active": True},
                {"id": "st3", "step_order": 3, "is_active": False},
            ],
        )
    )

    def fake_enroll(db_arg, sequence_id, steps, lead_id, tenant_id):
        return "enroll-123"

    monkeypatch.setattr(
        "backend.services.email_sequence_enrollment_ops.enroll_lead_in_sequence",
        fake_enroll,
    )

    res = manual_enroll_lead(db, "tenant-1", "s1", "l1")
    assert res["enrollment_id"] == "enroll-123"
    assert res["sequence_id"] == "s1"
    assert res["lead_id"] == "l1"
    assert res["steps_scheduled"] == 2  # two is_active=True out of three


def test_manual_enroll_lead_enrollment_failure_500(monkeypatch):
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1", "name": "Welcome", "is_active": True}])
        .configure("leads", data=[{"id": "l1", "name": "Alice", "email": "a@x.com"}])
        .configure("email_sequence_steps", data=[])
    )
    monkeypatch.setattr(
        "backend.services.email_sequence_enrollment_ops.enroll_lead_in_sequence",
        lambda *a, **kw: None,
    )

    with pytest.raises(HTTPException) as exc:
        manual_enroll_lead(db, "tenant-1", "s1", "l1")
    assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# email_sequence_sequence_ops
# ---------------------------------------------------------------------------


def test_enrich_sequence_counts_attaches_counts():
    db = (
        FakeSupabase()
        .configure("email_sequence_steps", data=[], count=4)
        .configure("email_sequence_enrollments", data=[], count=7)
    )
    res = _enrich_sequence_counts(db, [{"id": "s1"}])
    assert res[0]["step_count"] == 4
    assert res[0]["enrollment_count"] == 7


def test_enrich_sequence_counts_handles_none_counts():
    db = (
        FakeSupabase()
        .configure("email_sequence_steps", data=[], count=None)
        .configure("email_sequence_enrollments", data=[], count=None)
    )
    res = _enrich_sequence_counts(db, [{"id": "s1"}])
    assert res[0]["step_count"] == 0
    assert res[0]["enrollment_count"] == 0


def test_enrich_sequence_counts_handles_step_query_failure():
    db = (
        FakeSupabase()
        .raise_on("email_sequence_steps")
        .configure("email_sequence_enrollments", data=[], count=3)
    )
    res = _enrich_sequence_counts(db, [{"id": "s1"}])
    assert res[0]["step_count"] == 0
    assert res[0]["enrollment_count"] == 3


def test_enrich_sequence_counts_handles_enrollment_query_failure():
    db = (
        FakeSupabase()
        .configure("email_sequence_steps", data=[], count=2)
        .raise_on("email_sequence_enrollments")
    )
    res = _enrich_sequence_counts(db, [{"id": "s1"}])
    assert res[0]["step_count"] == 2
    assert res[0]["enrollment_count"] == 0


def test_list_sequences_for_tenant_happy_path():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences", data=[{"id": "s1", "name": "Welcome"}, {"id": "s2", "name": "Drip"}]
        )
        .configure("email_sequence_steps", data=[], count=3)
        .configure("email_sequence_enrollments", data=[], count=10)
    )
    res = list_sequences_for_tenant(db, "tenant-1")
    assert res["total"] == 2
    assert res["sequences"][0]["step_count"] == 3
    assert res["sequences"][0]["enrollment_count"] == 10


def test_list_sequences_for_tenant_query_failure_500():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        list_sequences_for_tenant(db, "tenant-1")
    assert exc.value.status_code == 500


def test_create_sequence_for_tenant_happy_path_no_steps():
    db = FakeSupabase().configure(
        "email_sequences",
        data=[{"id": "s-new", "name": "New", "tenant_id": "tenant-1"}],
    )
    req = SequenceCreate(name="New")
    res = create_sequence_for_tenant(db, "tenant-1", req)
    assert res["id"] == "s-new"
    assert res["steps"] == []


def test_create_sequence_for_tenant_with_steps():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s-new", "name": "New", "tenant_id": "tenant-1"}],
        )
        .configure_op("email_sequence_steps", "insert", echo_payload=True)
    )
    req = SequenceCreate(
        name="New",
        steps=[
            StepCreate(step_order=1, subject="Hello", body="Body 1"),
            StepCreate(step_order=2, subject="Follow-up", body="Body 2"),
        ],
    )
    res = create_sequence_for_tenant(db, "tenant-1", req)
    assert res["id"] == "s-new"
    assert len(res["steps"]) == 2


def test_create_sequence_for_tenant_step_insert_failure_swallowed():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s-new", "name": "New", "tenant_id": "tenant-1"}],
        )
        .raise_on("email_sequence_steps")
    )
    req = SequenceCreate(
        name="New",
        steps=[StepCreate(step_order=1, subject="Hello", body="Body")],
    )
    # Step insert failure logs but doesn't kill the create
    res = create_sequence_for_tenant(db, "tenant-1", req)
    assert res["id"] == "s-new"
    assert res["steps"] == []


def test_create_sequence_for_tenant_no_data_returned_500():
    db = FakeSupabase().configure("email_sequences", data=[])
    req = SequenceCreate(name="New")
    with pytest.raises(HTTPException) as exc:
        create_sequence_for_tenant(db, "tenant-1", req)
    assert exc.value.status_code == 500


def test_create_sequence_for_tenant_db_exception_500():
    db = FakeSupabase().raise_on("email_sequences")
    req = SequenceCreate(name="New")
    with pytest.raises(HTTPException) as exc:
        create_sequence_for_tenant(db, "tenant-1", req)
    assert exc.value.status_code == 500


def test_get_sequence_for_tenant_happy_path():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s1", "name": "Welcome", "tenant_id": "tenant-1"}],
        )
        .configure(
            "email_sequence_steps",
            data=[{"id": "st1", "step_order": 1, "subject": "Hi"}],
        )
        .configure(
            "email_sequence_enrollments",
            data=[
                {"status": "active"},
                {"status": "active"},
                {"status": "completed"},
            ],
        )
    )
    res = get_sequence_for_tenant(db, "tenant-1", "s1")
    assert res["id"] == "s1"
    assert len(res["steps"]) == 1
    assert res["enrollment_stats"]["total"] == 3
    assert res["enrollment_stats"]["by_status"]["active"] == 2
    assert res["enrollment_stats"]["by_status"]["completed"] == 1


def test_get_sequence_for_tenant_not_found_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        get_sequence_for_tenant(db, "tenant-1", "missing")
    assert exc.value.status_code == 404


def test_get_sequence_for_tenant_db_exception_500():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        get_sequence_for_tenant(db, "tenant-1", "s1")
    assert exc.value.status_code == 500


def test_get_sequence_for_tenant_steps_failure_returns_empty():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s1", "name": "Welcome", "tenant_id": "tenant-1"}],
        )
        .raise_on("email_sequence_steps")
        .configure("email_sequence_enrollments", data=[])
    )
    res = get_sequence_for_tenant(db, "tenant-1", "s1")
    assert res["steps"] == []


def test_get_sequence_for_tenant_stats_failure_returns_zeros():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s1", "name": "Welcome", "tenant_id": "tenant-1"}],
        )
        .configure("email_sequence_steps", data=[])
        .raise_on("email_sequence_enrollments")
    )
    res = get_sequence_for_tenant(db, "tenant-1", "s1")
    assert res["enrollment_stats"]["total"] == 0
    assert res["enrollment_stats"]["by_status"] == {}


def test_update_sequence_for_tenant_no_fields_400():
    db = FakeSupabase()
    req = SequenceUpdate()
    with pytest.raises(HTTPException) as exc:
        update_sequence_for_tenant(db, "tenant-1", "s1", req)
    assert exc.value.status_code == 400


def test_update_sequence_for_tenant_field_update_happy_path():
    db = FakeSupabase().configure(
        "email_sequences",
        data=[{"id": "s1", "name": "Renamed", "tenant_id": "tenant-1"}],
    )
    req = SequenceUpdate(name="Renamed")
    res = update_sequence_for_tenant(db, "tenant-1", "s1", req)
    assert res["id"] == "s1"


def test_update_sequence_for_tenant_field_update_not_found_404():
    db = FakeSupabase().configure_op("email_sequences", "update", data=[])
    req = SequenceUpdate(name="Renamed")
    with pytest.raises(HTTPException) as exc:
        update_sequence_for_tenant(db, "tenant-1", "missing", req)
    assert exc.value.status_code == 404


def test_update_sequence_for_tenant_only_steps_replaces():
    db = (
        FakeSupabase()
        .configure(
            "email_sequences",
            data=[{"id": "s1", "name": "Welcome", "tenant_id": "tenant-1"}],
        )
        .configure_op("email_sequence_steps", "delete", data=[])
        .configure_op("email_sequence_steps", "insert", echo_payload=True)
    )
    req = SequenceUpdate(
        steps=[StepCreate(step_order=1, subject="New", body="New body")]
    )
    res = update_sequence_for_tenant(db, "tenant-1", "s1", req)
    assert res["id"] == "s1"


def test_update_sequence_for_tenant_only_steps_select_not_found_404():
    db = FakeSupabase().configure_op("email_sequences", "select", data=[])
    req = SequenceUpdate(
        steps=[StepCreate(step_order=1, subject="New", body="New body")]
    )
    with pytest.raises(HTTPException) as exc:
        update_sequence_for_tenant(db, "tenant-1", "missing", req)
    assert exc.value.status_code == 404


def test_update_sequence_for_tenant_db_exception_500():
    db = FakeSupabase().raise_on("email_sequences")
    req = SequenceUpdate(name="Renamed")
    with pytest.raises(HTTPException) as exc:
        update_sequence_for_tenant(db, "tenant-1", "s1", req)
    assert exc.value.status_code == 500


def test_soft_delete_sequence_happy_path():
    db = FakeSupabase().configure(
        "email_sequences",
        data=[{"id": "s1", "is_active": False}],
    )
    soft_delete_sequence(db, "tenant-1", "s1")  # no exception


def test_soft_delete_sequence_not_found_404():
    db = FakeSupabase().configure_op("email_sequences", "update", data=[])
    with pytest.raises(HTTPException) as exc:
        soft_delete_sequence(db, "tenant-1", "missing")
    assert exc.value.status_code == 404


def test_soft_delete_sequence_db_exception_500():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        soft_delete_sequence(db, "tenant-1", "s1")
    assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# email_sequence_step_ops
# ---------------------------------------------------------------------------


def test_verify_sequence_ownership_ok():
    db = FakeSupabase().configure("email_sequences", data=[{"id": "s1"}])
    verify_sequence_ownership(db, "tenant-1", "s1", "Failed to add step")


def test_verify_sequence_ownership_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        verify_sequence_ownership(db, "tenant-1", "missing", "Failed to add step")
    assert exc.value.status_code == 404


def test_verify_sequence_ownership_500_passes_failure_detail():
    db = FakeSupabase().raise_on("email_sequences")
    with pytest.raises(HTTPException) as exc:
        verify_sequence_ownership(db, "tenant-1", "s1", "Custom failure detail")
    assert exc.value.status_code == 500
    assert exc.value.detail == "Custom failure detail"


def test_add_step_to_sequence_happy_path():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op(
            "email_sequence_steps",
            "insert",
            data=[{"id": "st-new", "step_order": 1, "subject": "Hi"}],
        )
    )
    req = StepCreate(step_order=1, subject="Hi", body="Body")
    res = add_step_to_sequence(db, "tenant-1", "s1", req)
    assert res["id"] == "st-new"


def test_add_step_to_sequence_insert_returns_empty_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op("email_sequence_steps", "insert", data=[])
    )
    req = StepCreate(step_order=1, subject="Hi", body="Body")
    with pytest.raises(HTTPException) as exc:
        add_step_to_sequence(db, "tenant-1", "s1", req)
    assert exc.value.status_code == 500


def test_add_step_to_sequence_ownership_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    req = StepCreate(step_order=1, subject="Hi", body="Body")
    with pytest.raises(HTTPException) as exc:
        add_step_to_sequence(db, "tenant-1", "missing", req)
    assert exc.value.status_code == 404


def test_add_step_to_sequence_insert_db_failure_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .raise_on("email_sequence_steps", op="insert")
    )
    req = StepCreate(step_order=1, subject="Hi", body="Body")
    with pytest.raises(HTTPException) as exc:
        add_step_to_sequence(db, "tenant-1", "s1", req)
    assert exc.value.status_code == 500


def test_update_step_in_sequence_no_fields_400():
    db = FakeSupabase().configure("email_sequences", data=[{"id": "s1"}])
    req = StepUpdate()
    with pytest.raises(HTTPException) as exc:
        update_step_in_sequence(db, "tenant-1", "s1", "st1", req)
    assert exc.value.status_code == 400


def test_update_step_in_sequence_happy_path():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op(
            "email_sequence_steps",
            "update",
            data=[{"id": "st1", "subject": "New subject"}],
        )
    )
    req = StepUpdate(subject="New subject")
    res = update_step_in_sequence(db, "tenant-1", "s1", "st1", req)
    assert res["subject"] == "New subject"


def test_update_step_in_sequence_not_found_404():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op("email_sequence_steps", "update", data=[])
    )
    req = StepUpdate(subject="New")
    with pytest.raises(HTTPException) as exc:
        update_step_in_sequence(db, "tenant-1", "s1", "missing", req)
    assert exc.value.status_code == 404


def test_update_step_in_sequence_ownership_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    req = StepUpdate(subject="New")
    with pytest.raises(HTTPException) as exc:
        update_step_in_sequence(db, "tenant-1", "missing-seq", "st1", req)
    assert exc.value.status_code == 404


def test_update_step_in_sequence_db_failure_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .raise_on("email_sequence_steps", op="update")
    )
    req = StepUpdate(subject="New")
    with pytest.raises(HTTPException) as exc:
        update_step_in_sequence(db, "tenant-1", "s1", "st1", req)
    assert exc.value.status_code == 500


def test_delete_step_from_sequence_happy_path():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op("email_sequence_steps", "delete", data=[{"id": "st1"}])
    )
    delete_step_from_sequence(db, "tenant-1", "s1", "st1")  # no exception


def test_delete_step_from_sequence_not_found_404():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .configure_op("email_sequence_steps", "delete", data=[])
    )
    with pytest.raises(HTTPException) as exc:
        delete_step_from_sequence(db, "tenant-1", "s1", "missing")
    assert exc.value.status_code == 404


def test_delete_step_from_sequence_ownership_404():
    db = FakeSupabase().configure("email_sequences", data=[])
    with pytest.raises(HTTPException) as exc:
        delete_step_from_sequence(db, "tenant-1", "missing-seq", "st1")
    assert exc.value.status_code == 404


def test_delete_step_from_sequence_db_failure_500():
    db = (
        FakeSupabase()
        .configure("email_sequences", data=[{"id": "s1"}])
        .raise_on("email_sequence_steps", op="delete")
    )
    with pytest.raises(HTTPException) as exc:
        delete_step_from_sequence(db, "tenant-1", "s1", "st1")
    assert exc.value.status_code == 500
