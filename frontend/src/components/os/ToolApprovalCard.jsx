/**
 * Agent OS tool approval - the owner's gate on a real external action.
 *
 * A deliverable (DeliverablePanel) is a draft the owner approves and a channel
 * handler then sends. This is different: an AGENT chose an action mid-run -
 * today `send_email` - and it does not happen at all until the owner says so.
 *
 * The whole point of this card is that approval is never blind. Everything the
 * action will do is on screen before the button: which agent asked, what it
 * will do, to whom, with what subject and what words. No "continue" that hides
 * the payload.
 *
 * Approval is idempotent server-side (the row leaves pending_approval with a
 * conditional update), so a double-click cannot send twice - but the button
 * also disables itself while in flight so the owner is never left guessing.
 */
import { useState } from "react";
import {
  approveOsToolExecution,
  rejectOsToolExecution,
} from "../../utils/api/os";

// Plain-language risk, so "level 2" never has to mean anything to an owner.
const RISK_META = {
  0: { label: "Read-only", color: "#9ca3af", bg: "rgba(156,163,175,0.12)" },
  1: { label: "Internal change", color: "var(--accent)", bg: "var(--accent-dim)" },
  2: { label: "Sends outside your business", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  3: { label: "High impact", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

const STATUS_META = {
  pending_approval: { label: "Waiting for your approval", color: "var(--accent)" },
  approved: { label: "Approved", color: "#22c55e" },
  running: { label: "Running", color: "var(--accent)" },
  succeeded: { label: "Done", color: "#22c55e" },
  failed: { label: "Failed - nothing was sent", color: "#ef4444" },
  verification_failed: { label: "Ran, but unconfirmed", color: "#f59e0b" },
  denied: { label: "Rejected - never sent", color: "#9ca3af" },
  cancelled: { label: "Cancelled", color: "#9ca3af" },
};

const TOOL_TITLES = {
  send_email: "Send an email",
  add_customer_note: "Add a note to a customer record",
  get_business_profile: "Read the business profile",
};

export default function ToolApprovalCard({ execution, token, onUpdated }) {
  const [busy, setBusy] = useState(null); // approve | reject
  const [error, setError] = useState(null);

  const status = execution?.status || "pending_approval";
  const pending = status === "pending_approval";
  const input = execution?.input || {};
  const result = execution?.result || null;
  const risk = RISK_META[execution?.risk_level] || RISK_META[3];
  const statusMeta = STATUS_META[status] || STATUS_META.pending_approval;

  async function decide(action) {
    if (busy) return;
    setBusy(action);
    setError(null);
    try {
      const updated =
        action === "approve"
          ? await approveOsToolExecution(token, execution.id)
          : await rejectOsToolExecution(token, execution.id, null);
      onUpdated?.(updated?.execution || updated);
    } catch (err) {
      setError(err?.message || "That didn't go through. Nothing was sent.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="os-tool-approval" data-testid="tool-approval-card">
      <div className="os-tool-approval__head">
        <h3>{TOOL_TITLES[execution?.tool_id] || execution?.tool_id}</h3>
        <span
          className="os-tool-approval__risk"
          style={{ color: risk.color, background: risk.bg }}
        >
          {risk.label}
        </span>
      </div>

      <p className="os-tool-approval__status" style={{ color: statusMeta.color }}>
        {statusMeta.label}
      </p>

      {execution?.agent_id ? (
        <p className="os-tool-approval__asker">
          Requested by your {execution.agent_id.replace(/_/g, " ")} agent
        </p>
      ) : null}

      {/* Everything the action will do, before the button. */}
      <dl className="os-tool-approval__details">
        {input.to ? (
          <>
            <dt>To</dt>
            <dd data-testid="tool-approval-recipient">{input.to}</dd>
          </>
        ) : null}
        {input.subject ? (
          <>
            <dt>Subject</dt>
            <dd data-testid="tool-approval-subject">{input.subject}</dd>
          </>
        ) : null}
        {input.body ? (
          <>
            <dt>Message</dt>
            <dd>
              <pre data-testid="tool-approval-body">{input.body}</pre>
            </dd>
          </>
        ) : null}
        {input.note ? (
          <>
            <dt>Note</dt>
            <dd>{input.note}</dd>
          </>
        ) : null}
      </dl>

      {/* Execution and verification are separate facts and read separately. */}
      {execution?.verification_detail ? (
        <p className="os-tool-approval__verification">
          {execution.verification_state === "passed" ? "Confirmed: " : "Not confirmed: "}
          {execution.verification_detail}
        </p>
      ) : null}

      {execution?.error?.message ? (
        <p className="os-tool-approval__error">{execution.error.message}</p>
      ) : null}

      {result?.deduplicated ? (
        <p className="os-tool-approval__verification">
          This message was already in the mailbox, so it was not sent again.
        </p>
      ) : null}

      {error ? <p className="os-tool-approval__error">{error}</p> : null}

      {pending ? (
        <div className="os-tool-approval__actions">
          <button
            type="button"
            onClick={() => decide("approve")}
            disabled={Boolean(busy)}
          >
            {busy === "approve" ? "Sending…" : "Approve and send"}
          </button>
          <button
            type="button"
            onClick={() => decide("reject")}
            disabled={Boolean(busy)}
          >
            {busy === "reject" ? "Rejecting…" : "Reject"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
