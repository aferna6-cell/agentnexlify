/**
 * Agent OS deliverable panel - P0.
 *
 * Side panel for the approval-gated draft a worker run produces. The
 * deliverable lives on os_agent_runs.deliverable (JSONB). While the run's
 * deliverable_status is pending_approval the owner can edit the title/body
 * and then approve or reject. After a decision the panel is read-only.
 */
import { useState, useEffect } from "react";
import {
  editOsDeliverable,
  approveOsDeliverable,
  rejectOsDeliverable,
  reportOsRunBug,
} from "../../utils/api/os";
import useIsMobile from "../../hooks/useIsMobile";

const DECISION_META = {
  approved: { label: "Approved", color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  rejected: { label: "Rejected", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  pending_approval: {
    label: "Pending approval",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
};

export default function DeliverablePanel({ run, token, onClose, onUpdated }) {
  const deliverable = run?.deliverable || null;
  const status = run?.deliverable_status || "pending_approval";
  const pending = status === "pending_approval";
  const meta = DECISION_META[status] || DECISION_META.pending_approval;
  const isMobile = useIsMobile();

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(null); // save | approve | reject | bug
  const [error, setError] = useState(null);
  const [bugReported, setBugReported] = useState(Boolean(run?.bug_reported_at));

  useEffect(() => {
    setTitle(run?.deliverable?.title || "");
    setBody(run?.deliverable?.body || "");
    setError(null);
    setBugReported(Boolean(run?.bug_reported_at));
  }, [run?.id]);

  if (!run || !deliverable) return null;

  const dirty =
    title !== (deliverable.title || "") || body !== (deliverable.body || "");

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

  const handleSave = () =>
    runAction("save", () =>
      editOsDeliverable(token, run.id, { title: title.trim(), body }),
    );

  const handleApprove = () =>
    runAction("approve", () => approveOsDeliverable(token, run.id));

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
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            This draft was {meta.label.toLowerCase()}. It can no longer be
            edited.
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
