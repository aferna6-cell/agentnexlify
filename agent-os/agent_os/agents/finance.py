"""Finance bucket (library §7).

* ``quote_generator`` — itemized quote/estimate documents (email or report).
* ``invoice_reminder`` — friendly first-touch invoice nudges (email or SMS).
* ``payment_follow_up`` — 3-touch escalating overdue-payment sequence, kept
  firm-but-fair (never legal threats, always owner approval).
"""

from __future__ import annotations

from agent_os.base import BaseAgent
from agent_os.channels import CHANNEL_SOFT_MAX_CHARS
from agent_os.context import SharedContext
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import (
    Bucket,
    Channel,
    Example,
    PermissionScope,
    Priority,
    SendCaps,
    Status,
)
from agent_os.trace import ReasoningTrace

from ._helpers import build_spec, field_input, money, sms_optout, topic_from, touch_label


class QuoteGeneratorAgent(BaseAgent):
    spec = build_spec(
        agent_id="quote_generator",
        display_name="Quote Generator",
        bucket=Bucket.finance,
        status=Status.new,
        build_priority=Priority.P2,
        purpose=(
            "Drafts an itemized quote/estimate with line items, total, terms, "
            "and a validity window. Always owner-approved before it goes out."
        ),
        routes_here_when=(
            "Owner asks to write up a quote or estimate for a customer",
            "Owner lists work items and wants them priced into a document",
        ),
        channel=Channel.email,
        secondary_channels=(Channel.report,),
        inputs=(
            field_input("customer_name", required=True, description="Who the quote is for."),
            field_input("line_items", description="List of work + prices."),
            field_input("total", "number", description="Total (computed if line items priced)."),
            field_input("scope", description="Plain-language scope summary."),
            field_input("validity_days", "number", description="Days the quote holds (default 30)."),
            field_input("terms", description="Payment/scheduling terms."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            notes="Quotes are money documents — owner approval is never bypassed.",
        ),
        title_format="Quote for {customer_name} — {total}",
        body_format="Itemized quote: header, line items, total, terms, validity. Markdown OK (email/report).",
        reasoning_trace_steps=("Business profile", "Quote inputs", "Drafted quote"),
        routing_keywords=(
            "quote",
            "estimate",
            "write up a quote",
            "price out",
            "proposal",
            "bid",
            "how much would it be",
        ),
        example_interactions=(
            Example(
                owner_ask=(
                    "Write up a quote for Dana: $400 deep clean, $150 carpet, total $550."
                ),
                expected_route="quote_generator",
                expected_output_excerpt="Total",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        line_items = ask.param("line_items") or []
        total = ask.param("total")
        scope = ask.param("scope") or "the work discussed"
        validity_days = int(ask.param("validity_days", 30) or 30)
        terms = ask.param("terms")
        # Real business name only — never "[Shop Name]".
        biz = profile.value("business_name") or "us"
        signoff = profile.signoff()

        trace.record_load(
            "Quote inputs",
            line_items or total,
            describe=lambda _: (
                f"{len(line_items)} line item(s), total {money(total)}"
                if line_items
                else f"total {money(total)}"
            ),
            skip_if_empty=True,
        )

        # Build an itemized table deterministically (markdown allowed on email/report).
        rows: list[str] = []
        computed = 0.0
        for item in line_items:
            if isinstance(item, dict):
                label = item.get("label") or item.get("name") or "Item"
                price = item.get("price")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                label, price = item
            else:
                label, price = str(item), None
            if price is not None:
                try:
                    computed += float(price)
                except (TypeError, ValueError):
                    pass
            rows.append(f"| {label} | {money(price) if price is not None else '—'} |")

        if total is None and computed:
            total = computed
        total_str = money(total) if total is not None else "(to be confirmed)"

        lines = [f"Quote from {biz} for {customer_name}", "", f"Scope: {scope}", ""]
        if rows:
            lines += ["| Item | Price |", "| --- | --- |", *rows, ""]
        lines += [f"**Total: {total_str}**", ""]
        if terms:
            lines.append(f"Terms: {terms}")
        lines.append(f"This quote is valid for {validity_days} days.")
        if signoff:
            lines += ["", f"— {signoff}, {biz}"]
        fallback = "\n".join(lines).strip()

        system = (
            "You write a clear itemized quote for a small business customer. "
            "Include the line items, a clear total, payment/scheduling terms if "
            "given, and a validity window. Use the real business name — never a "
            "bracketed placeholder. Markdown table is fine for email/report."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nScope: {scope}\n"
            f"Line items: {line_items or '(none itemized)'}\n"
            f"Total: {total_str}\nValidity: {validity_days} days\n"
            f"Terms: {terms or '(none given)'}\nDraft the quote."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted quote", max_tokens=1536,
        )

        title = f"Quote for {customer_name} — {total_str}"
        return AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"total": total, "validity_days": validity_days},
        )


class InvoiceReminderAgent(BaseAgent):
    spec = build_spec(
        agent_id="invoice_reminder",
        display_name="Invoice Reminder",
        bucket=Bucket.finance,
        status=Status.new,
        build_priority=Priority.P3,
        purpose=(
            "Drafts a friendly first-touch reminder for an outstanding invoice. "
            "Warm, never threatening — mentions the invoice date and amount."
        ),
        routes_here_when=(
            "Owner asks to remind a customer about an unpaid invoice",
            "Owner asks to nudge someone who hasn't paid yet",
        ),
        channel=Channel.email,
        secondary_channels=(Channel.sms,),
        inputs=(
            field_input("customer_name", required=True, description="Who owes."),
            field_input("amount", "number", required=True, description="Invoice amount."),
            field_input("invoice_date", "date", description="When the invoice was issued."),
            field_input("invoice_number", description="Reference number."),
            field_input("due_date", "date", description="When it was/is due."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            send_caps=SendCaps(per_day=None),
            notes="1 reminder per invoice per 7 days (hardcoded). No threatening language.",
        ),
        title_format="Invoice reminder — {customer_name}, {amount}",
        body_format="Friendly first-touch reminder. Plain text on SMS, markdown OK on email.",
        reasoning_trace_steps=("Business profile", "Invoice details", "Drafted reminder"),
        routing_keywords=(
            "invoice",
            "unpaid",
            "hasn't paid",
            "outstanding balance",
            "payment due",
            "remind about payment",
            "send a bill",
        ),
        example_interactions=(
            Example(
                owner_ask="Remind Mike his $550 invoice from last week is still open.",
                expected_route="invoice_reminder",
                expected_output_excerpt="invoice",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        amount = ask.param("amount")
        amount_str = money(amount) if amount is not None else ""
        invoice_date = ask.param("invoice_date")
        invoice_number = ask.param("invoice_number")
        biz = profile.value("business_name") or "us"
        signoff = profile.signoff()

        trace.record_load(
            "Invoice details",
            amount or invoice_number,
            describe=lambda _: (
                f"invoice {invoice_number or '—'} for {amount_str or 'unknown amount'}"
            ),
            skip_if_empty=True,
        )

        # Payment link only if it's a real profile field — never invented.
        pay_msgs: list[str] = []
        pay_link = self.value_or_gap(
            profile, "payment_link", pay_msgs, human_label="payment link"
        )

        ref = f"invoice {invoice_number}" if invoice_number else "your invoice"
        dated = f" from {invoice_date}" if invoice_date else ""
        amount_clause = f" for {amount_str}" if amount_str else ""
        pay_clause = f" You can pay here: {pay_link}." if pay_link else ""

        fallback = (
            f"Hi {customer_name}, just a friendly reminder that {ref}{dated}"
            f"{amount_clause} is still open. No rush if it's on the way — "
            f"just wanted to make sure it didn't slip through.{pay_clause} "
            f"Thanks so much!"
        )
        if signoff:
            fallback += f"\n\n— {signoff}, {biz}"

        if channel == Channel.sms:
            fallback = (
                f"Hi {customer_name}, friendly reminder that {ref}{amount_clause} "
                f"is still open. Thanks!{pay_clause} {sms_optout()}"
            )
            cap = CHANNEL_SOFT_MAX_CHARS[Channel.sms]
            if len(fallback) > cap:
                fallback = fallback[: cap - 1].rstrip() + "…"

        system = (
            "You write a warm, friendly first-touch invoice reminder for a small "
            "business. Mention the invoice and amount, assume good faith, never "
            "threaten or mention legal action. Use the real business name and "
            "never a bracketed placeholder. Plain text on SMS, light markdown OK "
            "on email."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nInvoice: {ref}{dated}\n"
            f"Amount: {amount_str or '(unknown)'}\nChannel: {channel.value}\n"
            f"Payment link: {pay_link or '(none on file)'}\nDraft the reminder."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted reminder",
        )

        title = f"Invoice reminder — {customer_name}, {amount_str}".strip()
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"amount": amount, "invoice_number": invoice_number},
        )
        for msg in pay_msgs:
            result.add_orchestrator_message(msg)
        return result


class PaymentFollowUpAgent(BaseAgent):
    spec = build_spec(
        agent_id="payment_follow_up",
        display_name="Payment Follow-up",
        bucket=Bucket.finance,
        status=Status.new,
        build_priority=Priority.P3,
        purpose=(
            "Drafts a 3-touch escalating sequence for an overdue invoice: "
            "firm-but-friendly, then formal, then a final notice. Stays "
            "professional — general 'next steps' only, never specific legal threats."
        ),
        routes_here_when=(
            "Owner asks for an escalating sequence on an overdue payment",
            "An invoice stays unpaid past its reminder window (Phase 4 event)",
        ),
        channel=Channel.sequence,
        inputs=(
            field_input("customer_name", required=True, description="Who owes."),
            field_input("amount", "number", required=True, description="Overdue amount."),
            field_input("invoice_number", description="Reference number."),
            field_input("days_overdue", "number", description="How overdue."),
            field_input("touch_count", "number", description="Touches (default 3)."),
        ),
        permission_scope=PermissionScope(
            require_owner_approval=True,
            notes="Always owner-approved. No specific legal threats — general next-steps language only.",
        ),
        title_format="Payment follow-up sequence — {customer_name}, {amount}",
        body_format="Escalating sequence: L1 firm-friendly, L2 formal, L3 final notice. Plain text per touch.",
        reasoning_trace_steps=("Business profile", "Overdue invoice", "Drafted sequence"),
        routing_keywords=(
            "overdue",
            "still hasn't paid",
            "chase payment",
            "escalate the invoice",
            "past due",
            "collections",
            "final notice",
        ),
        example_interactions=(
            Example(
                owner_ask="Mike still hasn't paid the $550 invoice, 30 days overdue. Escalate it.",
                expected_route="payment_follow_up",
                expected_output_excerpt="Touch 1",
            ),
        ),
    )

    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:
        profile = context.business_profile
        channel = self.channel_for(ask)

        customer_name = ask.param("customer_name") or topic_from(ask.text, default="there")
        amount = ask.param("amount")
        amount_str = money(amount) if amount is not None else ""
        invoice_number = ask.param("invoice_number")
        touch_count = int(ask.param("touch_count", 3) or 3)
        touch_count = max(2, min(3, touch_count))
        biz = profile.value("business_name") or "us"
        signoff = profile.signoff()

        trace.record_load(
            "Overdue invoice",
            amount or invoice_number,
            describe=lambda _: (
                f"invoice {invoice_number or '—'} for {amount_str or 'unknown amount'}"
            ),
            skip_if_empty=True,
        )

        ref = f"invoice {invoice_number}" if invoice_number else "your invoice"
        amount_clause = f" of {amount_str}" if amount_str else ""

        pay_msgs: list[str] = []
        pay_link = self.value_or_gap(
            profile, "payment_link", pay_msgs, human_label="payment link"
        )
        pay_clause = f" You can settle it here: {pay_link}." if pay_link else ""

        # Escalation tone ladder. General "next steps" only — never specific
        # legal threats (no court, no collections-agency naming, no interest math).
        bodies = [
            (
                f"Hi {customer_name}, following up on {ref}{amount_clause}, which is "
                f"now past due. I'm sure it just slipped — could you take care of it "
                f"this week?{pay_clause} Appreciate it."
            ),
            (
                f"Hi {customer_name}, a second notice on {ref}{amount_clause}. The "
                f"balance remains outstanding and we'd like to get it resolved. "
                f"Please arrange payment at your earliest convenience.{pay_clause} "
                f"If there's an issue with the invoice, let me know and we'll sort it out."
            ),
            (
                f"Hi {customer_name}, this is a final notice regarding {ref}"
                f"{amount_clause}, which remains unpaid. Please settle the balance "
                f"within the next few days so we can close this out.{pay_clause} If we "
                f"don't hear from you, we'll need to discuss next steps for the account."
            ),
        ]
        plan = [(0, "Email"), (7, "Email"), (14, "Email")][:touch_count]
        lines: list[str] = []
        for i, (offset, ch) in enumerate(plan):
            lines.append(touch_label(i + 1, offset, ch))
            lines.append(bodies[i])
            if signoff:
                lines.append(f"— {signoff}, {biz}")
            lines.append("")
        fallback = "\n".join(lines).strip()

        system = (
            "You draft an escalating overdue-payment sequence for a small business: "
            "touch 1 firm but friendly, touch 2 formal, touch 3 a final notice. Stay "
            "professional throughout. Use only general 'next steps' language — never "
            "specific legal threats, court, collections agencies, or interest "
            "calculations. Use the real business name, no bracketed placeholders. "
            "Plain text per touch with relative-date labels."
        )
        prompt = (
            f"Business: {profile.loaded_summary() or 'unknown'}\n"
            f"Customer: {customer_name}\nOverdue: {ref}{amount_clause}\n"
            f"Touches: {touch_count}\nDraft the escalating sequence."
        )
        body, _ = self.draft(
            trace=trace, system=system, prompt=prompt, fallback=fallback,
            step_name="Drafted sequence", max_tokens=1536,
        )

        title = f"Payment follow-up sequence — {customer_name}, {amount_str}".strip()
        result = AgentResult(
            agent_id=self.spec.agent_id,
            channel=channel,
            title=title,
            body=body,
            trace=trace,
            metadata={"amount": amount, "touch_count": touch_count},
        )
        for msg in pay_msgs:
            result.add_orchestrator_message(msg)
        return result
