"""Tests for the photo-quote default-pricing seed (#43).

Data-file validation + faked-DB seed behavior. No real DB/network; the seed
module imports its Supabase client lazily so this loads standalone:
    python3 -m pytest backend/tests/test_seed_photo_quote_pricing.py -v --noconftest
"""

from backend.scripts import seed_photo_quote_pricing as seed


# --------------------------------------------------------------------------- #
# Data-file validation                                                         #
# --------------------------------------------------------------------------- #
def test_all_six_verticals_present_and_valid():
    defaults = seed.load_defaults()
    assert set(defaults) == set(seed.VERTICALS)
    assert len(defaults) == 6


def test_each_vertical_has_at_least_six_damage_types_with_ranges():
    defaults = seed.load_defaults()
    for industry, doc in defaults.items():
        damage = doc["damage_types"]
        assert len(damage) >= 6, industry
        for dtype, tiers in damage.items():
            for sev in ("minor", "major"):
                rng = tiers[sev]
                assert rng["low"] <= rng["high"], (industry, dtype, sev)
                assert rng["low"] >= 0


def test_each_file_documents_a_source_url():
    defaults = seed.load_defaults()
    for industry, doc in defaults.items():
        urls = doc["_meta"]["source_urls"]
        assert urls and all(u.startswith("http") for u in urls), industry


# --------------------------------------------------------------------------- #
# Seed behavior (faked DB)                                                      #
# --------------------------------------------------------------------------- #
class FakeQuery:
    def __init__(self, sink, tenants):
        self._sink = sink
        self._tenants = tenants
        self._table = None
        self._is_select = False

    # read side
    def select(self, *a, **k):
        self._is_select = True
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def upsert(self, row, on_conflict=None):
        self._sink.append({"row": row, "on_conflict": on_conflict})
        return self

    def execute(self):
        if self._is_select:
            return type("R", (), {"data": self._tenants})()
        return type("R", (), {"data": []})()


class FakeDB:
    def __init__(self, tenants):
        self.upserts = []
        self._tenants = tenants

    def table(self, name):
        q = FakeQuery(self.upserts, self._tenants if name == "tenants" else [])
        q._table = name
        return q


def test_seed_upserts_one_row_per_tenant_per_vertical():
    db = FakeDB([{"id": "t1", "plan": "agent_os"}, {"id": "t2", "plan": "chatbot"}])
    result = seed.seed(db=db)
    # 2 tenants × 6 verticals
    assert result["tenants"] == 2
    assert result["rows_upserted"] == 12
    assert len(db.upserts) == 12
    # every upsert targets the unique constraint (idempotent)
    assert all(u["on_conflict"] == "client_id,industry" for u in db.upserts)
    # rows carry client_id (leads/pricing use client_id, not tenant_id)
    assert all("client_id" in u["row"] for u in db.upserts)


def test_seed_dry_run_writes_nothing():
    db = FakeDB([{"id": "t1", "plan": "agent_os"}])
    result = seed.seed(dry_run=True, db=db)
    assert result["dry_run"] is True
    assert result["rows_upserted"] == 0
    assert db.upserts == []
    # counted as skipped (would-be writes): 1 tenant × 6 verticals
    assert result["skipped"] == 6


def test_seed_is_idempotent_on_rerun():
    db = FakeDB([{"id": "t1", "plan": "agent_os"}])
    first = seed.seed(db=db)
    db.upserts.clear()
    second = seed.seed(db=db)
    # same op count both runs; upsert (not insert) makes re-run a refresh
    assert first["rows_upserted"] == second["rows_upserted"] == 6


def test_seed_no_eligible_tenants_is_a_noop():
    db = FakeDB([])
    result = seed.seed(db=db)
    assert result == {"tenants": 0, "rows_upserted": 0, "skipped": 0, "dry_run": False}
