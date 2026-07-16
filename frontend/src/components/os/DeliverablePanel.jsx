/**
 * Agent OS deliverable panel - P0.
 *
 * Side panel for the approval-gated draft a worker run produces. The
 * deliverable lives on os_agent_runs.deliverable (JSONB). While the run's
 * deliverable_status is pending_approval the owner can edit the title/body
 * and then approve or reject. After a decision the panel is read-only.
 */
import { useState, useEffect, useRef } from "react";
import {
  editOsDeliverable,
  approveOsDeliverable,
  rejectOsDeliverable,
  reportOsRunBug,
  getOsActionRun,
  retryOsActionRun,
} from "../../utils/api/os";
import useIsMobile from "../../hooks/useIsMobile";

// os_action_runs.status -> how the send outcome reads to the owner. Approval
// only means "the owner said go"; whether the SMS/email/widget action actually
// fired lives here. Without this the panel showed a green "Approved" even when
// the real send failed.
const SEND_META = {
  queued: { label: "Sending…", color: "var(--accent)", bg: "var(--accent-dim)" },
  running: { label: "Sending…", color: "var(--accent)", bg: "var(--accent-dim)" },
  succeeded: { label: "Sent", color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  failed: { label: "Send failed", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};
const TERMINAL_SEND = new Set(["succeeded", "failed"]);
const POLL_MS = 2500;
const MAX_POLLS = 12;

const DECISION_META = {
  approved: { label: "Approved", color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  rejected: { label: "Rejected", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  pending_approval: {
    label: "Pending approval",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
};

// Send actions that need a recipient the draft text usually doesn't contain.
// Prod's only real send failed with "missing recipient" - the owner had no
// way to say who the message goes to. This input is that way.
const RECIPIENT_ACTIONS = {
  "sms.send": "Recipient phone (e.g. +1 555-555-0123)",
  "email.send": "Recipient email (e.g. sam@example.com)",
};

export default function DeliverablePanel({ run, token, onClose, onUpdated }) {
  const deliverable = run?.deliverable || null;
  const status = run?.deliverable_status || "pending_approval";
  const pending = status === "pending_approval";
  const meta = DECISION_META[status] || DECISION_META.pending_approval;
  const isMobile = useIsMobile();
  const recipientPlaceholder = RECIPIENT_ACTIONS[run?.action_type] || null;

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [recipient, setRecipient] = useState("");
  const [busy, setBusy] = useState(null); // save | approve | reject | bug | retry
  const [error, setError] = useState(null);
  const [bugReported, setBugReported] = useState(Boolean(run?.bug_reported_at));
  const [actionRun, setActionRun] = useState(null);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Poll one action run until it reaches a terminal state (or the cap), so the
  // owner sees the real send outcome, not just "approved".
  const pollActionRun = async (actionRunId, attempt = 0) => {
    if (!actionRunId || !mountedRef.current) return;
    let row;
    try {
      row = await getOsActionRun(token, actionRunId);
    } catch {
      return; // best-effort; leave the last known state
    }
    if (!mountedRef.current) return;
    setActionRun(row);
    if (!TERMINAL_SEND.has(row?.status) && attempt < MAX_POLLS) {
      setTimeout(() => pollActionRun(actionRunId, attempt + 1), POLL_MS);
    }
  };

  useEffect(() => {
    setTitle(run?.deliverable?.title || "");
    setBody(run?.deliverable?.body || "");
    setRecipient(run?.deliverable?.recipient || "");
    setError(null);
    setBugReported(Boolean(run?.bug_reported_at));
    setActionRun(null);
    // Re-opening an already-approved deliverable: fetch its send outcome so a
    // past failure is visible, not hidden behind a green "Approved" badge.
    if (run?.deliverable_status === "approved" && run?.action_run_id) {
      pollActionRun(run.action_run_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.id]);

  if (!run || !deliverable) return null;

  const recipientDirty =
    recipientPlaceholder !== null &&
    recipient.trim() !== (deliverable.recipient || "");
  const dirty =
    title !== (deliverable.title || "") ||
    body !== (deliverable.body || "") ||
    recipientDirty;

  const runAction = async (kind, fn) => {
    setBusy(kind);
    setError(null);
    try {
      const updated = await fn();
      if (updated && onUpdated) onUpdated(updated);
      return updated;
    } catch (err) {
      setError(err.message || "Action failed");
      return null;
    } finally {
      setBusy(null);
    }
  };

  const handleSave = () => {
    const payload = { title: title.trim(), body };
    if (recipientPlaceholder) payload.recipient = recipient.trim();
    return runAction("save", () => editOsDeliverable(token, run.id, payload));
  };

  const handleApprove = async () => {
    const updated = await runAction("approve", async () => {
      // Persist an unsaved recipient first so the send knows who it goes to.
      if (recipientDirty) {
        await editOsDeliverable(token, run.id, {
          recipient: recipient.trim(),
        });
      }
      return approveOsDeliverable(token, run.id);
    });
    // Approval scheduled the real send in the background - poll its outcome.
    if (updated?.action_run_id) pollActionRun(updated.action_run_id);
  };

  const handleRetrySend = async () => {
    const id = actionRun?.id || run?.action_run_id;
    if (!id) return;
    // Only send-action drafts carry a recipient; display-only retries keep
    // the original two-argument call shape.
    const fresh = await runAction("retry", () =>
      recipientPlaceholder
        ? retryOsActionRun(token, id, { recipient: recipient.trim() })
        : retryOsActionRun(token, id),
    );
    if (fresh?.id) {
      setActionRun(fresh);
      pollActionRun(fresh.id);
    }
  };

  const handleReject = () =>
    runAction("reject", () => rejectOsDeliverable(token, run.id));

  const handleReportBug = async () => {
    const updated = await runAction("bug", () => reportOsRunBug(token, run.id));
    if (updated) setBugReported(true);
  };

  return (
    <aside
      style={
        isMobile
          ? {
              position: "fixed",
              inset: 0,
              width: "100%",
              zIndex: 70,
              background: "var(--bg-primary)",
              display: "flex",
              flexDirection: "column",
              height: "100%",
            }
          : {
              width: 440,
              maxWidth: "100%",
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              background: "var(--bg-primary)",
              display: "flex",
              flexDirection: "column",
              height: "100%",
            }
      }
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            minWidth: 0,
          }}
        >
          <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Draft</span>
          <span
            style={{
              padding: "2px 9px",
              borderRadius: 999,
              fontSize: "0.7rem",
              fontWeight: 600,
              color: meta.color,
              background: meta.bg,
              whiteSpace: "nowrap",
            }}
          >
            {meta.label}
          </span>
          {status === "approved" && actionRun && SEND_META[actionRun.status] && (
            <span
              data-testid="send-status"
              style={{
                padding: "2px 9px",
                borderRadius: 999,
                fontSize: "0.7rem",
                fontWeight: 600,
                color: SEND_META[actionRun.status].color,
                background: SEND_META[actionRun.status].bg,
                whiteSpace: "nowrap",
              }}
            >
              {SEND_META[actionRun.status].label}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          aria-label="Close draft panel"
          style={{
            background: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "4px 10px",
            color: "var(--text-secondary)",
            cursor: "pointer",
            fontSize: "0.8rem",
          }}
        >
          Close
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {error && (
          <div
            style={{
              marginBottom: 14,
              padding: "8px 12px",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 8,
              color: "#ef4444",
              fontSize: "0.8rem",
            }}
          >
            {error}
          </div>
        )}

        <label
          style={{
            display: "block",
            fontSize: "0.75rem",
            marginBottom: 4,
            color: "var(--text-secondary)",
          }}
        >
          Title
        </label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={!pending}
          placeholder="Draft title"
          style={{ width: "100%", marginBottom: 14 }}
        />

        {recipientPlaceholder && pending && (
          <>
            <label
              style={{
                display: "block",
                fontSize: "0.75rem",
                marginBottom: 4,
                color: "var(--text-secondary)",
              }}
            >
              Send to
            </label>
            <input
              data-testid="recipient-input"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder={recipientPlaceholder}
              style={{ width: "100%", marginBottom: 14 }}
            />
          </>
        )}

        <label
          style={{
            display: "block",
            fontSize: "0.75rem",
            marginBottom: 4,
            color: "var(--text-secondary)",
          }}
        >
          Body
        </label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={!pending}
          rows={16}
          placeholder="Draft content"
          style={{
            width: "100%",
            resize: "vertical",
            fontFamily: "var(--font-mono, monospace)",
            fontSize: "0.83rem",
            lineHeight: 1.6,
          }}
        />

        {pending && (
          <button
            onClick={handleSave}
            disabled={!dirty || busy !== null}
            style={{
              marginTop: 10,
              minHeight: 44,
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 16px",
              color: dirty ? "var(--text-primary)" : "var(--text-muted)",
              cursor: dirty && busy === null ? "pointer" : "not-allowed",
              fontSize: "0.83rem",
            }}
          >
            {busy === "save" ? "Saving..." : "Save edits"}
          </button>
        )}
      </div>

      <div
        style={{
          borderTop: "1px solid var(--border)",
          padding: 16,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {pending ? (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              data-tour="approve-button"
              className="btn-primary"
              onClick={handleApprove}
              disabled={busy !== null}
              style={{ flex: 1, minHeight: 44 }}
            >
              {busy === "approve" ? "Approving..." : "Approve"}
            </button>
            <button
              onClick={handleReject}
              disabled={busy !== null}
              style={{
                flex: 1,
                minHeight: 44,
                background: "transparent",
                border: "1px solid rgba(239,68,68,0.4)",
                borderRadius: 8,
                padding: "8px 16px",
                color: "#ef4444",
                cursor: busy === null ? "pointer" : "not-allowed",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              {busy === "reject" ? "Rejecting..." : "Reject"}
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              This draft was {meta.label.toLowerCase()}. It can no longer be
              edited.
            </div>
            {actionRun?.status === "failed" && (
              <div
                data-testid="send-failed-banner"
                style={{
                  fontSize: "0.8rem",
                  color: "#ef4444",
                  border: "1px solid rgba(239,68,68,0.4)",
                  borderRadius: 8,
                  padding: "10px 12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <span>
                  The send did not go through
                  {actionRun?.error_detail?.message
                    ? `: ${actionRun.error_detail.message}`
                    : "."}
                </span>
                {recipientPlaceholder && (
                  <input
                    data-testid="retry-recipient-input"
                    value={recipient}
                    onChange={(e) => setRecipient(e.target.value)}
                    placeholder={recipientPlaceholder}
                    aria-label="Send to"
                    style={{ width: "100%" }}
                  />
                )}
                <button
                  onClick={handleRetrySend}
                  disabled={busy !== null}
                  style={{
                    minHeight: 40,
                    alignSelf: "flex-start",
                    background: "transparent",
                    border: "1px solid rgba(239,68,68,0.5)",
                    borderRadius: 8,
                    padding: "6px 14px",
                    color: "#ef4444",
                    cursor: busy === null ? "pointer" : "not-allowed",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                  }}
                >
                  {busy === "retry" ? "Retrying..." : "Retry send"}
                </button>
              </div>
            )}
          </div>
        )}

        <button
          onClick={handleReportBug}
          disabled={busy !== null || bugReported}
          style={{
            background: "none",
            border: "none",
            color: bugReported ? "var(--text-muted)" : "var(--text-secondary)",
            cursor: busy === null && !bugReported ? "pointer" : "default",
            fontSize: "0.78rem",
            textDecoration: bugReported ? "none" : "underline",
            alignSelf: "flex-start",
            padding: 0,
          }}
        >
          {bugReported
            ? "Bug reported - thanks"
            : busy === "bug"
              ? "Reporting..."
              : "Report a problem with this run"}
        </button>
      </div>
    </aside>
  );
}
