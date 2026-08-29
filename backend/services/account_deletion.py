"""GDPR account deletion — full purge of one tenant's data (Art. 17).

One call removes every tenant-scoped row across the data plane, best-effort
closes the Stripe customer (which cancels any subscriptions), and finally
deletes the ``tenants`` row itself. Built for the launch-readiness rubric
criterion 1.3 ("GDPR / CCPA data deletion endpoint works").

Design choices:
- Explicit table list, curated from the live production schema (see
  ``docs/dev-knowledge/schema-log.md``). A table missing in some environment
  is skipped, never fatal — deletion proceeds table by table and reports
  per-table results so a partial failure is visible, not silent.
- Children before parents where FKs exist; ``tenants`` is always last so a
  crash mid-purge leaves the account locked-out-able and re-runnable.
- Tenant column per table resolves through ``tenant_scope`` — the same
  client_id/tenant_id mapping every query in the codebase uses.
- JWTs are stateless: an already-issued token stays valid until expiry, but
  every data read after the purge returns nothing and ``/auth/me`` 401s once
  the tenants row is gone.
"""

import logging
from dataclasses import dataclass, field

from backend.services.tenant_scope import tenant_delete

logger = logging.getLogger(__name__)

# Children first, parents last; tenants is deleted separately at the end.
# Curated from live prod schema 2026-06-10 (113 public tables, tenant-scoped
# subset). New tenant-scoped tables MUST be added here — checked in tests
# against tenant_scope overrides so os_* additions are not forgotten.
TENANT_DATA_TABLES: tuple[str, ...] = (
    # Agent OS runtime (graph edges cascade from nodes, listed for clarity)
    "os_graph_edges",
    "os_graph_nodes",
    "os_model_call_log",
    "os_routing_decision",
    "os_action_runs",
    # Agent tool executions (migration 195): input/result payloads can carry a
    # customer's email, subject line and note text, so they purge with the rest.
    # Ordered before os_agent_runs, which it references.
    "os_tool_executions",
    "os_outbound_log",
    "os_backlog_requests",
    "os_memory_entries",
    "os_agent_runs",
    "os_messages",
    "os_threads",
    "os_sync_state",
    "os_tenant_usage",
    "os_uploads",
    "os_scheduled_tasks",
    "os_project_steps",
    "os_projects",
    # Communications + CRM
    "chat_messages",
    "conversations",
    "conversation_notes",
    "escalations",
    "prospects",
    "messages",
    "response_metrics",
    "ai_feedback",
    "leads",
    "client_notes",
    "action_items",
    "calls",
    "missed_call_texts",
    # Scheduling + commerce
    "appointments",
    "business_hours",
    "service_records",
    "service_types",
    "invoices",
    "invoice_item_templates",
    "orders",
    "menu_items",
    "bids",
    "bid_templates",
    "quote_requests",
    "tenant_quote_usage",
    "tenant_pricing_rules",
    # Documents + content
    "documents",
    "document_templates",
    "content_items",
    "website_content",
    "kb_articles",
    "kb_sources",
    "kb_section_hashes",
    "repurpose_jobs",
    "faq_entries",
    "snippets",
    # Marketing + sequences (children -> parents)
    "campaign_sends",
    "campaign_analytics_aggregates",
    "marketing_campaigns",
    "email_sequence_sends",
    "email_sequence_enrollments",
    "email_sequence_steps",
    "email_sequences",
    "email_templates",
    "email_events",
    "tenant_email_daily_sends",
    "ab_test_sends",
    "ab_test_variants",
    "ab_tests",
    "social_posts",
    "seo_profiles",
    "seo_audits",
    "geo_scores",
    "keyword_rankings",
    "reviews",
    "csat_responses",
    # Automations (children -> parents)
    "automation_rule_executions",
    "automation_rules",
    "automation_logs",
    "automation_executions",
    "automation_steps",
    "automation_sequences",
    "automations",
    "automation_locks",
    "pipeline_automations",
    "pipeline_stages",
    "trigger_logs",
    "scheduled_jobs",
    # Workspace + access
    "team_members",
    "client_accounts",
    "portal_tokens",
    "tenant_api_keys",
    "tenant_tag_definitions",
    "custom_field_definitions",
    "scoring_configs",
    "smart_lists",
    "forms",
    "form_submissions",
    "waitlist_entries",
    "jobs",
    "job_applications",
    "chat_flows",
    "widget_configs",
    "wizard_events",
    # Integrations + billing artifacts
    "tenant_integrations",
    "integration_sync_log",
    "integrations",
    "webhooks",
    "webhook_logs",
    "oauth_states",
    "tenant_ai_usage_monthly",
    "billing_refunds",
    "billing_dunning_events",
    "tenant_cancellation_events",
    "activity_log",
)


@dataclass
class DeletionReport:
    rows_deleted: int = 0
    tables_purged: int = 0
    tables_skipped: list[str] = field(default_factory=list)
    stripe_closed: bool = False
    tenant_row_deleted: bool = False

    def as_dict(self) -> dict:
        return {
            "rows_deleted": self.rows_deleted,
            "tables_purged": self.tables_purged,
            "tables_skipped": self.tables_skipped,
            "stripe_closed": self.stripe_closed,
            "tenant_row_deleted": self.tenant_row_deleted,
        }


def _close_stripe_customer(stripe_customer_id: str | None) -> bool:
    """Best-effort: deleting the customer cancels its subscriptions too."""
    if not stripe_customer_id:
        return False
    try:
        import stripe

        stripe.Customer.delete(stripe_customer_id)
        return True
    except Exception:
        logger.warning(
            "account_deletion: stripe customer close failed id=%s",
            stripe_customer_id,
            exc_info=True,
        )
        return False


def delete_tenant_account(db, client_id: str) -> DeletionReport:
    """Purge one tenant. Per-table failures are recorded, never fatal.

    Re-runnable: a second call deletes whatever the first missed.
    """
    report = DeletionReport()

    tenant_rows = (
        db.table("tenants")
        .select("id, stripe_customer_id, business_name")
        .eq("id", client_id)
        .limit(1)
        .execute()
    ).data or []
    tenant = tenant_rows[0] if tenant_rows else {}

    report.stripe_closed = _close_stripe_customer(tenant.get("stripe_customer_id"))

    for table in TENANT_DATA_TABLES:
        try:
            result = tenant_delete(db, table, client_id).execute()
            deleted = len(getattr(result, "data", None) or [])
            report.rows_deleted += deleted
            report.tables_purged += 1
        except Exception:
            # Missing table/column in this environment, or transient error —
            # visible in the report and the log, and a re-run picks it up.
            report.tables_skipped.append(table)
            logger.warning(
                "account_deletion: purge failed table=%s client_id=%s",
                table,
                client_id,
                exc_info=True,
            )

    try:
        result = db.table("tenants").delete().eq("id", client_id).execute()
        report.tenant_row_deleted = bool(getattr(result, "data", None))
    except Exception:
        logger.exception("account_deletion: tenants row delete failed id=%s", client_id)

    logger.info(
        "account_deletion: client_id=%s rows=%d tables=%d skipped=%d stripe=%s tenant_deleted=%s",
        client_id,
        report.rows_deleted,
        report.tables_purged,
        len(report.tables_skipped),
        report.stripe_closed,
        report.tenant_row_deleted,
    )
    return report
