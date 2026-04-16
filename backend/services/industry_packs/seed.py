"""Seed industry pack content into a tenant.

Design:

- Zero new migrations. The pack source tag (`industry_pack:{key}`) is stored
  inside existing JSONB fields:
    forms.settings_json.industry_pack_source
    automation_sequences.trigger_config.industry_pack_source
    smart_lists.filter_json._industry_pack_source
    automation_rules.trigger_config.industry_pack_source

- Idempotent. Re-seeding a pack is a no-op: each insert is preceded by a
  lookup on (tenant_id, industry_pack_source, name). If found, we skip.

- Widget KB: tenant's widget_configs.knowledge_base is a single text column.
  Seed articles are appended inside marker fences so upgrades can replace
  just our fenced block without overwriting tenant customizations:
      <!-- industry_pack:dental BEGIN -->
      ...markdown...
      <!-- industry_pack:dental END -->

- Schema awareness: automation_rules.trigger_type has a CHECK constraint on a
  fixed enum. Rules whose trigger_event falls outside that enum are logged
  to SeedResult.errors and skipped — no silent drop.
"""

import logging
from typing import Any

from backend.services.industry_packs.base import (
    AutomationRuleTemplate,
    FormPreset,
    IndustryPack,
    KBSeedArticle,
    SeedResult,
    SequenceTemplate,
    SmartListTemplate,
)

logger = logging.getLogger(__name__)


# automation_rules.trigger_type CHECK enum from migration 087.
_ALLOWED_TRIGGER_TYPES = frozenset({
    "lead_captured", "tag_added", "tag_removed",
    "form_submitted", "appointment_created", "appointment_completed",
    "pipeline_stage_changed", "lead_score_threshold",
    "email_opened", "email_clicked",
    "scheduled_daily", "scheduled_weekly",
    "website_visit", "smart_list_matched",
})

# Map pack-level trigger_event strings → automation_rules.trigger_type
# (constrained by CHECK enum in migration 087).
_TRIGGER_EVENT_MAP = {
    "weekly_cron": "scheduled_weekly",
    "daily_cron": "scheduled_daily",
    "csat_response": "form_submitted",        # CSAT submissions are forms
    "invoice_overdue": "scheduled_daily",     # evaluated daily via cron
    "appointment_booked": "appointment_created",
    "appointment_created": "appointment_created",
    "appointment_completed": "appointment_completed",
    "new_lead": "lead_captured",
    "lead_stage_change": "pipeline_stage_changed",
}

# automation_sequences.trigger_event is validated by Pydantic at the router
# level (backend/models/schemas.py:VALID_TRIGGER_EVENTS). Bypassing it with
# service-role inserts works, but any future PATCH via the API would 422.
# Remap pack sequences to the allowed set and stash the original event in
# `trigger_config.original_trigger_event` so a future automation engine pass
# can dispatch correctly.
_SEQUENCE_VALID_TRIGGER_EVENTS = frozenset({
    "new_lead",
    "lead_stage_change",
    "no_response_24h",
    "appointment_completed",
})

_SEQUENCE_EVENT_MAP = {
    # "when an appointment is booked" is modeled as a lead stage transition
    # to the "appointment_booked" stage — the existing engine already filters
    # lead_stage_change by trigger_config.target_stage.
    "appointment_booked": ("lead_stage_change", {"target_stage": "appointment_booked"}),
    "appointment_created": ("lead_stage_change", {"target_stage": "appointment_booked"}),
    # Dunning + reactivation are cron-driven; map to new_lead as a safe
    # placeholder and flag the real dispatch event in trigger_config. A
    # future cron job can match on original_trigger_event to enroll leads.
    "invoice_overdue": ("new_lead", {}),
    "lapsed_client_weekly_cron": ("new_lead", {}),
    # Already allowed — pass through.
    "new_lead": ("new_lead", {}),
    "appointment_completed": ("appointment_completed", {}),
    "lead_stage_change": ("lead_stage_change", {}),
    "no_response_24h": ("no_response_24h", {}),
}


def _remap_sequence_trigger(
    original_event: str, original_config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Map a pack sequence trigger to the API-valid set, preserving intent
    in `trigger_config.original_trigger_event` for future dispatch.
    """
    mapped_event, extra_config = _SEQUENCE_EVENT_MAP.get(
        original_event, ("new_lead", {}),
    )
    merged = dict(original_config)
    merged.update(extra_config)
    if mapped_event != original_event:
        merged["original_trigger_event"] = original_event
    if mapped_event not in _SEQUENCE_VALID_TRIGGER_EVENTS:
        # defensive — should never hit this because map is closed over valid set
        mapped_event = "new_lead"
    return mapped_event, merged


# ----------------------------------------------------------------------
# Seeding helpers — each returns (inserted_count, skipped_count)
# ----------------------------------------------------------------------


def _seed_forms(
    db: Any, tenant_id: str, pack: IndustryPack, result: SeedResult, *, dry_run: bool,
) -> None:
    """Seed forms. Reuses forms.py _FORM_PRESETS when preset.preset_key is set."""
    from backend.services.form_defaults import _FORM_PRESETS

    for preset in pack.form_presets:
        try:
            if preset.preset_key and preset.preset_key in _FORM_PRESETS:
                source = _FORM_PRESETS[preset.preset_key]
                fields = source["fields"]
                success_msg = source.get("success_message", preset.success_message)
            else:
                fields = preset.fields
                success_msg = preset.success_message

            settings_json = {"industry_pack_source": pack.source_tag}

            if not dry_run:
                # Idempotency lookup: tenant + source tag + name
                existing = (
                    db.table("forms")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("name", preset.name)
                    .contains("settings_json", {"industry_pack_source": pack.source_tag})
                    .execute()
                )
                if existing.data:
                    result.forms_skipped += 1
                    continue

                db.table("forms").insert({
                    "tenant_id": tenant_id,
                    "name": preset.name,
                    "description": preset.description,
                    "fields_json": fields,
                    "settings_json": settings_json,
                    "success_message": success_msg,
                }).execute()

            result.forms_inserted += 1
        except Exception as exc:
            logger.exception("seed_forms failed for preset=%s", preset.key)
            result.errors.append(f"form[{preset.key}]: {type(exc).__name__}: {exc}")


def _seed_sequences(
    db: Any, tenant_id: str, pack: IndustryPack, result: SeedResult, *, dry_run: bool,
) -> None:
    """Seed automation_sequences + automation_steps."""
    for seq in pack.sequence_templates:
        try:
            # Remap pack event → API-valid event, preserving original in config
            mapped_event, trigger_config = _remap_sequence_trigger(
                seq.trigger_event, seq.trigger_config,
            )
            trigger_config["industry_pack_source"] = pack.source_tag

            if not dry_run:
                existing = (
                    db.table("automation_sequences")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("name", seq.name)
                    .contains("trigger_config", {"industry_pack_source": pack.source_tag})
                    .execute()
                )
                if existing.data:
                    result.sequences_skipped += 1
                    continue

                seq_row = (
                    db.table("automation_sequences")
                    .insert({
                        "tenant_id": tenant_id,
                        "name": seq.name,
                        "trigger_event": mapped_event,
                        "trigger_config": trigger_config,
                    })
                    .execute()
                )
                if not seq_row.data:
                    raise RuntimeError(f"automation_sequences insert returned no rows for {seq.name}")
                sequence_id = seq_row.data[0]["id"]

                steps_payload = [
                    {
                        "sequence_id": sequence_id,
                        "step_order": step.step_order,
                        "delay_minutes": step.delay_minutes,
                        "action_type": step.action_type,
                        "subject_template": step.subject_template,
                        "body_template": step.body_template,
                    }
                    for step in seq.steps
                ]
                if steps_payload:
                    db.table("automation_steps").insert(steps_payload).execute()

            result.sequences_inserted += 1
        except Exception as exc:
            logger.exception("seed_sequences failed for seq=%s", seq.key)
            result.errors.append(f"sequence[{seq.key}]: {type(exc).__name__}: {exc}")


def _seed_smart_lists(
    db: Any, tenant_id: str, pack: IndustryPack, result: SeedResult, *, dry_run: bool,
) -> None:
    """Seed smart_lists. Tag in filter_json._industry_pack_source."""
    for sl in pack.smart_list_templates:
        try:
            filter_json = dict(sl.filter)
            filter_json["_industry_pack_source"] = pack.source_tag

            if not dry_run:
                existing = (
                    db.table("smart_lists")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("name", sl.name)
                    .contains("filter_json", {"_industry_pack_source": pack.source_tag})
                    .execute()
                )
                if existing.data:
                    result.smart_lists_skipped += 1
                    continue

                db.table("smart_lists").insert({
                    "tenant_id": tenant_id,
                    "name": sl.name,
                    "description": sl.description,
                    "filter_json": filter_json,
                }).execute()

            result.smart_lists_inserted += 1
        except Exception as exc:
            logger.exception("seed_smart_lists failed for list=%s", sl.key)
            result.errors.append(f"smart_list[{sl.key}]: {type(exc).__name__}: {exc}")


def _seed_automation_rules(
    db: Any, tenant_id: str, pack: IndustryPack, result: SeedResult, *, dry_run: bool,
) -> None:
    """Seed automation_rules. Remaps trigger_event → trigger_type enum.

    Rules whose trigger_event can't be mapped are recorded as errors and
    skipped, so the operator knows they need a schema extension.
    """
    for rule in pack.automation_rules:
        try:
            trigger_type = _TRIGGER_EVENT_MAP.get(rule.trigger_event, rule.trigger_event)
            if trigger_type not in _ALLOWED_TRIGGER_TYPES:
                msg = (
                    f"rule[{rule.key}]: trigger_event '{rule.trigger_event}' "
                    f"maps to '{trigger_type}' which is not in the allowed CHECK enum. "
                    "Extend migration 087 to add this trigger type."
                )
                logger.warning(msg)
                result.errors.append(msg)
                continue

            trigger_config = {
                "industry_pack_source": pack.source_tag,
                "original_trigger_event": rule.trigger_event,
            }

            conditions = [rule.condition] if rule.condition else []
            actions = [rule.action] if rule.action else []

            if not dry_run:
                existing = (
                    db.table("automation_rules")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("name", rule.name)
                    .contains("trigger_config", {"industry_pack_source": pack.source_tag})
                    .execute()
                )
                if existing.data:
                    result.automation_rules_skipped += 1
                    continue

                db.table("automation_rules").insert({
                    "tenant_id": tenant_id,
                    "name": rule.name,
                    "description": rule.description,
                    "trigger_type": trigger_type,
                    "trigger_config": trigger_config,
                    "conditions": conditions,
                    "actions": actions,
                    "is_active": True,
                }).execute()

            result.automation_rules_inserted += 1
        except Exception as exc:
            logger.exception("seed_automation_rules failed for rule=%s", rule.key)
            result.errors.append(f"rule[{rule.key}]: {type(exc).__name__}: {exc}")


def _seed_kb_articles(
    db: Any, tenant_id: str, pack: IndustryPack, result: SeedResult, *, dry_run: bool,
) -> None:
    """Append KB seed articles into widget_configs.knowledge_base between
    marker fences. Upgrades replace the fenced block idempotently.
    """
    begin_marker = f"<!-- industry_pack:{pack.key} BEGIN v{pack.version} -->"
    end_marker = f"<!-- industry_pack:{pack.key} END -->"

    # Build the markdown payload once.
    md_lines = [begin_marker, ""]
    for article in pack.kb_seed_articles:
        md_lines.append(f"## {article.title}")
        md_lines.append("")
        md_lines.append(article.body)
        md_lines.append("")
    md_lines.append(end_marker)
    payload = "\n".join(md_lines)

    try:
        if dry_run:
            result.kb_articles_inserted += len(pack.kb_seed_articles)
            return

        cfg = (
            db.table("widget_configs")
            .select("knowledge_base")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        existing = (cfg.data[0]["knowledge_base"] if cfg.data else "") or ""

        # Check for any previous version block for this pack.
        old_begin_prefix = f"<!-- industry_pack:{pack.key} BEGIN"
        if old_begin_prefix in existing:
            start = existing.index(old_begin_prefix)
            end_idx = existing.find(end_marker, start)
            if end_idx >= 0:
                end_idx += len(end_marker)
                # If same version, treat as already seeded.
                if begin_marker in existing[start:end_idx]:
                    result.kb_articles_skipped += len(pack.kb_seed_articles)
                    return
                # Upgrade: splice out the old block, keep the rest.
                new_existing = (existing[:start] + existing[end_idx:]).strip()
            else:
                # Malformed block — just leave it, append new below.
                new_existing = existing
        else:
            new_existing = existing

        combined = (new_existing + "\n\n" + payload).strip() if new_existing else payload

        if cfg.data:
            db.table("widget_configs").update({
                "knowledge_base": combined,
            }).eq("tenant_id", tenant_id).execute()
        else:
            db.table("widget_configs").insert({
                "tenant_id": tenant_id,
                "knowledge_base": combined,
            }).execute()

        result.kb_articles_inserted += len(pack.kb_seed_articles)
    except Exception as exc:
        logger.exception("seed_kb_articles failed for pack=%s", pack.key)
        result.errors.append(f"kb: {type(exc).__name__}: {exc}")


# ----------------------------------------------------------------------
# Public entrypoint
# ----------------------------------------------------------------------


def apply_pack_to_tenant(
    db: Any, tenant_id: str, pack: IndustryPack, *, dry_run: bool = False,
) -> SeedResult:
    """Seed an IndustryPack into a tenant. Idempotent.

    Args:
        db: a supabase client (service-role for RLS bypass)
        tenant_id: UUID string
        pack: the IndustryPack to seed
        dry_run: if True, return expected counts without writing

    Returns:
        SeedResult with inserted/skipped counts per component + any errors.
    """
    result = SeedResult(pack_key=pack.key, pack_version=pack.version)

    _seed_forms(db, tenant_id, pack, result, dry_run=dry_run)
    _seed_sequences(db, tenant_id, pack, result, dry_run=dry_run)
    _seed_smart_lists(db, tenant_id, pack, result, dry_run=dry_run)
    _seed_automation_rules(db, tenant_id, pack, result, dry_run=dry_run)
    _seed_kb_articles(db, tenant_id, pack, result, dry_run=dry_run)

    logger.info(
        "apply_pack_to_tenant: pack=%s tenant=%s dry_run=%s inserted=%d errors=%d",
        pack.key, tenant_id, dry_run, result.total_inserted(), len(result.errors),
    )
    return result
