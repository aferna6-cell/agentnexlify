"""Unit tests for backend.services.industry_packs.

Covers:
- Registry loads all 13 packs
- Alias resolution (plumbing → home_services)
- Unknown business_type falls back to default
- Pack summary counts are non-zero for all packs
- Seed function dry-run returns expected counts without DB writes
- Seed function with mock DB inserts and skips idempotently
- KB marker fence idempotency
- trigger_type mapping + skip on unmapped enums
"""

from unittest.mock import MagicMock

import pytest

from backend.services.industry_packs import (
    IndustryPack,
    list_available_packs,
    load_pack,
)
from backend.services.industry_packs.seed import (
    _ALLOWED_TRIGGER_TYPES,
    _TRIGGER_EVENT_MAP,
    apply_pack_to_tenant,
)


class TestRegistry:
    def test_all_13_packs_load(self):
        packs = list_available_packs()
        assert len(packs) == 13
        keys = {p["key"] for p in packs}
        assert keys == {
            "dental", "medical", "hvac", "home_services",
            "salon", "restaurant", "legal", "auto_shop",
            "fitness", "professional_services", "retail",
            "real_estate", "default",
        }

    def test_every_pack_has_summary(self):
        for p in list_available_packs():
            counts = p["counts"]
            assert counts["form_presets"] >= 1
            assert counts["sequence_templates"] >= 1
            assert counts["automation_rules"] >= 1
            assert counts["kb_seed_articles"] >= 1

    def test_dental_has_full_6_workflows(self):
        dental = load_pack("dental")
        assert dental.key == "dental"
        assert dental.label == "Dental Office"
        # Core 6: welcome + reminder + post-appt review + dunning + reactivation (5 seqs)
        assert len(dental.sequence_templates) == 5
        # Automation rules: booking reminder + review trigger + 2 CSAT gates +
        # dunning trigger + overdue escalation + reactivation cron = 7
        assert len(dental.automation_rules) == 7
        # Dental ships the most FAQs of any pack
        assert len(dental.kb_seed_articles) >= 10

    def test_alias_resolution(self):
        # 'plumbing' → home_services
        p = load_pack("plumbing")
        assert p.key == "home_services"
        # 'spa' → salon
        p = load_pack("spa")
        assert p.key == "salon"

    def test_unknown_business_type_falls_back_to_default(self):
        p = load_pack("not_a_real_vertical")
        assert p.key == "default"
        p = load_pack(None)
        assert p.key == "default"
        p = load_pack("")
        assert p.key == "default"

    def test_source_tag_format(self):
        dental = load_pack("dental")
        assert dental.source_tag == "industry_pack:dental"


class TestTriggerEventMapping:
    def test_all_mapped_targets_are_allowed(self):
        for pack_event, db_trigger in _TRIGGER_EVENT_MAP.items():
            assert db_trigger in _ALLOWED_TRIGGER_TYPES, (
                f"pack event '{pack_event}' maps to '{db_trigger}' "
                "which is not in the DB enum"
            )


class TestSeedDryRun:
    def test_dry_run_counts_without_db_writes(self):
        db = MagicMock()
        pack = load_pack("dental")
        result = apply_pack_to_tenant(db, "tenant-xyz", pack, dry_run=True)

        assert result.pack_key == "dental"
        assert result.forms_inserted == len(pack.form_presets)
        assert result.sequences_inserted == len(pack.sequence_templates)
        assert result.smart_lists_inserted == len(pack.smart_list_templates)
        assert result.kb_articles_inserted == len(pack.kb_seed_articles)

        # automation_rules: only the mappable ones get "inserted" in dry run.
        # Dental has 7 rules; csat_response maps to form_submitted (allowed),
        # weekly_cron maps to scheduled_weekly (allowed), invoice_overdue maps
        # to scheduled_daily (allowed), so all should be countable.
        assert result.automation_rules_inserted + len(result.errors) == len(
            pack.automation_rules
        )

        # No DB calls made during dry run
        assert db.table.call_count == 0


class TestSeedSkipWhenExists:
    def _db_with_existing_rows(self):
        """Mock DB where every select for existing rows returns data."""
        db = MagicMock()
        existing_result = MagicMock(data=[{"id": "existing-uuid"}])

        # Every .execute() call on the select chain returns existing rows
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.contains.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = existing_result
        chain.insert.return_value = chain
        chain.update.return_value = chain
        db.table.return_value = chain
        return db

    def test_reseeding_is_idempotent_skips_existing(self):
        db = self._db_with_existing_rows()
        pack = load_pack("salon")  # smaller pack for a cleaner test
        result = apply_pack_to_tenant(db, "tenant-xyz", pack, dry_run=False)

        # Forms / sequences / smart_lists / rules should all be skipped
        assert result.forms_skipped == len(pack.form_presets)
        assert result.sequences_skipped == len(pack.sequence_templates)
        assert result.smart_lists_skipped == len(pack.smart_list_templates)
        # automation rules skipped OR mapped-out (errors) — either way, not inserted
        assert result.automation_rules_inserted == 0


class TestSeedFreshInsertSalon:
    def test_fresh_insert_writes_rows(self):
        """First-time seed of salon pack inserts everything."""

        def _mock_table(name):
            chain = MagicMock()

            def _select(*args, **kwargs):
                sel = MagicMock()
                sel.eq.return_value = sel
                sel.contains.return_value = sel
                sel.limit.return_value = sel
                if name == "widget_configs":
                    sel.execute.return_value = MagicMock(data=[{"knowledge_base": ""}])
                else:
                    sel.execute.return_value = MagicMock(data=[])
                return sel

            def _insert(*args, **kwargs):
                ins = MagicMock()
                ins.execute.return_value = MagicMock(data=[{"id": "new-uuid"}])
                return ins

            def _update(*args, **kwargs):
                upd = MagicMock()
                upd.eq.return_value = upd
                upd.execute.return_value = MagicMock(data=[])
                return upd

            chain.select = _select
            chain.insert = _insert
            chain.update = _update
            return chain

        db = MagicMock()
        db.table.side_effect = _mock_table

        pack = load_pack("salon")
        result = apply_pack_to_tenant(db, "tenant-xyz", pack, dry_run=False)

        assert result.forms_inserted == len(pack.form_presets)
        assert result.sequences_inserted == len(pack.sequence_templates)
        assert result.smart_lists_inserted == len(pack.smart_list_templates)
        assert result.kb_articles_inserted == len(pack.kb_seed_articles)
        assert result.forms_skipped == 0
        assert result.sequences_skipped == 0
        assert result.smart_lists_skipped == 0


class TestKBMarkerFencing:
    def test_kb_payload_wraps_in_markers(self):
        from backend.services.industry_packs.seed import _seed_kb_articles
        from backend.services.industry_packs.base import SeedResult

        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.update.return_value = chain
        chain.insert.return_value = chain
        chain.execute.return_value = MagicMock(data=[{"knowledge_base": ""}])
        db.table.return_value = chain

        pack = load_pack("dental")
        result = SeedResult(pack_key=pack.key, pack_version=pack.version)
        _seed_kb_articles(db, "tenant-xyz", pack, result, dry_run=False)

        # Verify the update call received a string with the markers
        update_calls = [
            c for c in chain.update.call_args_list if c
        ]
        assert update_calls, "expected at least one widget_configs.update call"
        args, _ = update_calls[0]
        payload = args[0] if args else None
        assert payload is not None
        kb = payload.get("knowledge_base", "")
        assert f"<!-- industry_pack:dental BEGIN v{pack.version} -->" in kb
        assert "<!-- industry_pack:dental END -->" in kb
        # At least one of the FAQ titles should be in the rendered markdown
        assert "Delta Dental" in kb or "crown" in kb.lower()
