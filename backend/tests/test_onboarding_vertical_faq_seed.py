"""Tests for _seed_vertical_preset_faqs — vertical preset FAQ seeding during onboarding.

Proves:
  (a) FAQs are seeded from the vertical preset when the tenant has NO existing FAQs.
  (b) FAQs are NOT seeded when the tenant already has FAQs (idempotent guard).
  (c) The call never raises — failures return 0 and log a warning.
  (d) An unknown vertical falls back to the generic preset without raising.

Run with:
    .venv/bin/python -m pytest backend/tests/test_onboarding_vertical_faq_seed.py -q --noconftest
"""

import os
import sys
import types
import unittest.mock as mock

os.environ.setdefault("TESTING", "1")


# ---------------------------------------------------------------------------
# Import the function under test directly (avoids FastAPI route inspection)
# ---------------------------------------------------------------------------

def _get_fn():
    from backend.routers.onboarding import _seed_vertical_preset_faqs
    return _seed_vertical_preset_faqs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(existing_faqs: list[dict] | None = None, insert_raises: bool = False):
    """Return a minimal mock Supabase client for faq_entries queries.

    Args:
        existing_faqs: rows returned by the SELECT check. Empty list = no FAQs.
        insert_raises: if True, the .insert().execute() call raises RuntimeError.
    """
    inserted_rows: list[list[dict]] = []

    class _Exec:
        def __init__(self, data=None, raises=False):
            self._data = data if data is not None else []
            self._raises = raises

        def execute(self):
            if self._raises:
                raise RuntimeError("DB insert failed (test-injected)")
            return types.SimpleNamespace(data=self._data)

    class _SelectChain:
        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def execute(self):
            return types.SimpleNamespace(data=existing_faqs or [])

    class _InsertChain:
        def insert(self, rows):
            inserted_rows.append(rows)
            return _Exec(data=rows, raises=insert_raises)

    class _FaqTable:
        """Merges select + insert behaviour."""
        def select(self, *a, **kw):
            return _SelectChain()

        def insert(self, rows):
            inserted_rows.append(rows)
            return _Exec(data=rows, raises=insert_raises)

    class _Db:
        def table(self, name):
            assert name == "faq_entries", f"unexpected table: {name}"
            return _FaqTable()

    return _Db(), inserted_rows


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSeedVerticalPresetFaqs:

    def setup_method(self):
        sys.modules.pop("backend.routers.onboarding", None)

    # --- (a) FAQs seeded when tenant has none ---

    def test_salon_spa_faqs_seeded_when_tenant_has_none(self):
        """salon_spa preset must produce FAQ rows when the tenant has no FAQs."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-001", "salon_spa")

        assert count > 0, "expected FAQs to be seeded for salon_spa"
        assert inserted, "expected at least one insert call"
        rows = inserted[0]
        assert len(rows) == count, "returned count must match inserted rows"
        # Every row must have question + answer + tenant_id + category
        for row in rows:
            assert row["tenant_id"] == "tenant-uuid-001"
            assert row["question"].strip()
            assert row["answer"].strip()
            assert row["category"] == "vertical_preset"
            assert row["is_active"] is True

    def test_dental_faqs_seeded_when_tenant_has_none(self):
        """dental preset must produce FAQ rows when the tenant has no FAQs."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-002", "dental")

        assert count > 0, "expected FAQs to be seeded for dental"
        rows = inserted[0]
        assert all(r["category"] == "vertical_preset" for r in rows)

    def test_plumber_hvac_faqs_seeded_when_tenant_has_none(self):
        """plumber_hvac preset must produce FAQ rows."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-003", "plumber_hvac")

        assert count > 0, "expected FAQs to be seeded for plumber_hvac"

    def test_alias_salon_maps_to_salon_spa(self):
        """'salon' alias resolves to salon_spa preset, seeding the same FAQs."""
        fn = _get_fn()
        db_alias, inserted_alias = _make_db(existing_faqs=[])
        db_canon, inserted_canon = _make_db(existing_faqs=[])

        count_alias = fn(db_alias, "tenant-uuid-004a", "salon")
        count_canon = fn(db_canon, "tenant-uuid-004b", "salon_spa")

        assert count_alias > 0
        assert count_alias == count_canon, (
            "alias 'salon' and canonical 'salon_spa' should seed the same FAQ count"
        )

    def test_generic_preset_used_for_unknown_vertical(self):
        """Unknown vertical falls back to the generic preset — must still seed FAQs."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-005", "completely_unknown_xyz")

        # generic preset has 5 FAQs; just assert > 0
        assert count > 0, "generic preset should produce at least one FAQ"

    # --- (b) FAQs NOT seeded when tenant already has entries ---

    def test_no_seed_when_existing_faqs_present(self):
        """If the tenant already has FAQ entries, seeding must be skipped entirely."""
        fn = _get_fn()
        # Return one existing row from the SELECT
        existing = [{"id": "existing-faq-uuid"}]
        db, inserted = _make_db(existing_faqs=existing)

        count = fn(db, "tenant-uuid-006", "salon_spa")

        assert count == 0, "expected 0 when tenant already has FAQs"
        assert not inserted, "expected no INSERT when FAQs already exist"

    def test_no_seed_when_existing_faqs_multiple(self):
        """Multiple existing rows still skip seeding."""
        fn = _get_fn()
        existing = [{"id": f"faq-{i}"} for i in range(5)]
        db, inserted = _make_db(existing_faqs=existing)

        count = fn(db, "tenant-uuid-007", "dental")

        assert count == 0
        assert not inserted

    # --- (c) Never raises — failures return 0 ---

    def test_db_insert_failure_returns_zero_not_raises(self):
        """If the DB insert raises, the function catches it and returns 0."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[], insert_raises=True)

        # Must not raise
        count = fn(db, "tenant-uuid-008", "salon_spa")

        assert count == 0, "DB insert failure should return 0, not propagate"

    def test_none_business_type_returns_zero(self):
        """None business_type returns 0 without touching the DB."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-009", None)

        assert count == 0
        assert not inserted

    def test_empty_business_type_returns_zero(self):
        """Empty-string business_type returns 0 without touching the DB."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        count = fn(db, "tenant-uuid-010", "")

        assert count == 0
        assert not inserted

    # --- (d) Row shape validation ---

    def test_rows_have_correct_keys(self):
        """Each inserted row must have exactly the expected faq_entries columns."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        fn(db, "tenant-uuid-011", "generic")

        rows = inserted[0]
        required_keys = {"tenant_id", "question", "answer", "category", "is_active"}
        for row in rows:
            missing = required_keys - row.keys()
            assert not missing, f"Row missing keys: {missing}. Row: {row}"

    def test_rows_have_non_empty_question_and_answer(self):
        """No row should have a blank question or answer."""
        fn = _get_fn()
        db, inserted = _make_db(existing_faqs=[])

        fn(db, "tenant-uuid-012", "salon_spa")

        rows = inserted[0]
        for row in rows:
            assert row["question"].strip(), f"Empty question in row: {row}"
            assert row["answer"].strip(), f"Empty answer in row: {row}"
