"""Scheduled jobs — lead-related automations."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from backend.models.database import get_service_supabase
from backend.services.tenant_scope import tenant_table
from backend.services.automation.trigger import BATCH_LIMIT, trigger_sequence
from backend.services.automation.scheduled_jobs._common import logger


async def check_no_response_leads() -> int:
    """Find leads with status 'new' that have had no chat activity in 24+ hours and trigger
    the no_response_24h automation sequence for each.

    Strategy (batched — <=5 DB round-trips for the read/check phase regardless of lead count):
      Q1. Load 'new' leads created more than 24h ago (batch, BATCH_LIMIT).
      Q2. Batch fetch automation_executions for all lead IDs where status is active or
          in_progress, then fetch those sequences' trigger_events. Build a set of lead IDs
          already enrolled in a no_response_24h sequence.
      Q3. Batch fetch conversations for all conversation IDs to get session_id mapping.
      Q4. Batch fetch latest chat_messages for all session IDs; deduplicate in Python to
          get the most recent timestamp per session_id.
      Then loop in Python to decide which leads to trigger.

    Returns count of sequences triggered.
    """
    db = get_service_supabase()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    triggered = 0

    # Q1: fetch candidate leads
    try:
        leads_result = (
            db.table("leads")
            .select("id, client_id, conversation_id, created_at")
            .eq("status", "new")
            .lte("created_at", cutoff.isoformat())
            .limit(BATCH_LIMIT)
            .execute()
        )
    except Exception:
        logger.exception("check_no_response_leads: failed to query leads")
        return 0

    leads = leads_result.data or []
    if not leads:
        return 0

    all_lead_ids = [lead["id"] for lead in leads]
    all_conv_ids = [
        lead["conversation_id"] for lead in leads if lead.get("conversation_id")
    ]

    # Q2a: batch fetch active/in_progress executions for all leads
    already_enrolled_lead_ids: set[str] = set()
    try:
        exec_result = (
            db.table("automation_executions")
            .select("lead_id, sequence_id")
            .in_("lead_id", all_lead_ids)
            .in_("status", ["active", "in_progress"])
            .execute()
        )
        exec_rows = exec_result.data or []
    except Exception:
        logger.warning(
            "check_no_response_leads: batch enrollment check failed, proceeding without dedup",
            exc_info=True,
        )
        exec_rows = []

    if exec_rows:
        # Q2b: fetch trigger_events for the sequences referenced by those executions
        enrolled_seq_ids = list({row["sequence_id"] for row in exec_rows})
        try:
            seq_result = (
                db.table("automation_sequences")
                .select("id, trigger_event")
                .in_("id", enrolled_seq_ids)
                .execute()
            )
            no_response_seq_ids: set[str] = {
                s["id"]
                for s in (seq_result.data or [])
                if s.get("trigger_event") == "no_response_24h"
            }
        except Exception:
            logger.warning(
                "check_no_response_leads: batch sequence trigger_event check failed",
                exc_info=True,
            )
            no_response_seq_ids = set()

        for row in exec_rows:
            if row["sequence_id"] in no_response_seq_ids:
                already_enrolled_lead_ids.add(row["lead_id"])

    # Q3: batch fetch conversations to build conv_id -> session_id mapping
    conv_to_session: dict[str, str] = {}
    if all_conv_ids:
        try:
            conv_result = (
                db.table("conversations")
                .select("id, session_id")
                .in_("id", all_conv_ids)
                .execute()
            )
            for row in conv_result.data or []:
                if row.get("session_id"):
                    conv_to_session[row["id"]] = row["session_id"]
        except Exception:
            logger.warning(
                "check_no_response_leads: batch conversations lookup failed",
                exc_info=True,
            )

    # Q4: batch fetch latest chat_messages per session_id
    # Supabase returns rows in order; we take the first occurrence per session_id (latest).
    all_session_ids = list(set(conv_to_session.values()))
    session_last_message: dict[str, datetime] = {}
    if all_session_ids:
        try:
            msg_result = (
                db.table("chat_messages")
                .select("session_id, created_at")
                .in_("session_id", all_session_ids)
                .order("created_at", desc=True)
                .limit(len(all_session_ids) * 10)  # generous; deduplicated in Python
                .execute()
            )
            for row in msg_result.data or []:
                sid = row["session_id"]
                if sid not in session_last_message:
                    raw_ts = row["created_at"]
                    session_last_message[sid] = datetime.fromisoformat(
                        raw_ts.replace("Z", "+00:00")
                    )
        except Exception:
            logger.warning(
                "check_no_response_leads: batch chat_messages lookup failed",
                exc_info=True,
            )

    # Evaluate each lead in Python and collect (tenant_id, lead_id) pairs to trigger.
    # No DB calls here — all guard data was fetched in Q1-Q4 above.
    leads_to_trigger: list[tuple[str, str]] = []
    for lead in leads:
        lead_id = lead["id"]
        tenant_id = lead["client_id"]

        # Skip if already enrolled in a no_response_24h sequence
        if lead_id in already_enrolled_lead_ids:
            continue

        # Determine last message timestamp for this lead
        last_message_at = None
        conv_id = lead.get("conversation_id")
        if conv_id:
            session_id = conv_to_session.get(conv_id)
            if session_id:
                last_message_at = session_last_message.get(session_id)

        # Skip if there has been recent activity within 24h
        if last_message_at is not None and last_message_at > cutoff:
            continue  # Recent activity — skip

        leads_to_trigger.append((tenant_id, lead_id))

    if not leads_to_trigger:
        return 0

    # Batch-trigger phase: group leads by tenant so we make ONE sequences query
    # and ONE steps query per tenant, then ONE bulk insert per tenant.
    # Before this change: O(3 * leads) DB round-trips.
    # After this change: O(3 * tenants) DB round-trips (tenants << leads in practice).

    leads_by_tenant: dict[str, list[str]] = defaultdict(list)
    for tenant_id, lead_id in leads_to_trigger:
        leads_by_tenant[tenant_id].append(lead_id)

    for tenant_id, lead_ids in leads_by_tenant.items():
        # Fetch active no_response_24h sequences for this tenant (1 query)
        try:
            seq_result = (
                tenant_table(db, "automation_sequences", tenant_id)
                .select("id, trigger_config")
                .eq("trigger_event", "no_response_24h")
                .eq("is_active", True)
                .execute()
            )
        except Exception:
            logger.exception(
                "check_no_response_leads: sequences query failed for tenant %s", tenant_id
            )
            continue

        sequences = seq_result.data or []
        if not sequences:
            continue

        # Fetch first active step for each sequence (1 query per tenant)
        seq_ids = [s["id"] for s in sequences]
        try:
            steps_result = (
                db.table("automation_steps")
                .select("sequence_id, step_order, delay_minutes")
                .in_("sequence_id", seq_ids)
                .eq("is_active", True)
                .order("step_order")
                .limit(len(seq_ids) * 20)
                .execute()
            )
        except Exception:
            logger.exception(
                "check_no_response_leads: steps query failed for tenant %s", tenant_id
            )
            continue

        first_step_by_seq: dict[str, dict] = {}
        for step in steps_result.data or []:
            sid = step["sequence_id"]
            if sid not in first_step_by_seq:
                first_step_by_seq[sid] = step

        # Build bulk enrollment records for all leads x all eligible sequences
        now_utc = datetime.now(timezone.utc)
        enrollment_records: list[dict] = []
        for seq in sequences:
            first_step = first_step_by_seq.get(seq["id"])
            if not first_step:
                continue
            next_run = now_utc + timedelta(minutes=first_step["delay_minutes"])
            for lead_id in lead_ids:
                enrollment_records.append(
                    {
                        "sequence_id": seq["id"],
                        "lead_id": lead_id,
                        "tenant_id": tenant_id,
                        "current_step": 1,
                        "status": "in_progress",
                        "next_run_at": next_run.isoformat(),
                    }
                )

        if not enrollment_records:
            continue

        # Single bulk insert for all (lead, sequence) pairs in this tenant
        try:
            tenant_table(db, "automation_executions", tenant_id).insert(
                enrollment_records
            ).execute()
            triggered += len(enrollment_records)
            logger.info(
                "check_no_response_leads: bulk enrolled %d executions for tenant %s "
                "(leads: %s)",
                len(enrollment_records),
                tenant_id,
                lead_ids,
            )
        except Exception as _bulk_exc:
            err_str = str(_bulk_exc).lower()
            if "unique" in err_str or "duplicate" in err_str:
                # Some leads already enrolled — fall back to per-record inserts
                logger.debug(
                    "check_no_response_leads: bulk insert hit unique constraint for tenant %s, "
                    "falling back to per-record inserts",
                    tenant_id,
                )
                for record in enrollment_records:
                    try:
                        tenant_table(db, "automation_executions", tenant_id).insert(
                            record
                        ).execute()
                        triggered += 1
                    except Exception as _rec_exc:
                        rec_err = str(_rec_exc).lower()
                        if "unique" in rec_err or "duplicate" in rec_err:
                            logger.debug(
                                "Lead %s already enrolled in sequence %s",
                                record["lead_id"],
                                record["sequence_id"],
                            )
                        else:
                            logger.warning(
                                "check_no_response_leads: failed to enroll lead %s in "
                                "sequence %s: %s",
                                record["lead_id"],
                                record["sequence_id"],
                                _rec_exc,
                                exc_info=True,
                            )
            else:
                logger.exception(
                    "check_no_response_leads: bulk insert failed for tenant %s", tenant_id
                )

    return triggered
