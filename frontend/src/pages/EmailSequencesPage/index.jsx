import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { notify } from "../../utils/notify";
import {
  fetchEmailSequences,
  updateEmailSequence,
  deleteEmailSequence,
} from "../../utils/api/email-sequences";
import { cardStyle, btnPrimary, btnSecondary, btnDanger } from "./styles";
import { TriggerBadge, Toggle } from "./badges";
import { EmptyState, StatCard, LoadingRows } from "./EmptyState";
import { SequenceModal } from "./SequenceModal";
import { SequenceDetail } from "./SequenceDetail";

export default function EmailSequencesPage() {
  const { user, token } = useAuth();

  const [sequences, setSequences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showCreate, setShowCreate] = useState(false);
  const [editSequence, setEditSequence] = useState(null);
  const [detailSequenceId, setDetailSequenceId] = useState(null);

  const loadSequences = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEmailSequences(user.tenantId, token);
      setSequences(res?.sequences || res || []);
    } catch (e) {
      setError(e.message || "Failed to load sequences.");
      setSequences([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadSequences();
  }, [loadSequences]);

  const handleToggleActive = async (seq) => {
    try {
      await updateEmailSequence(seq.id, token, { is_active: !seq.is_active });
      setSequences((prev) =>
        prev.map((s) =>
          s.id === seq.id ? { ...s, is_active: !s.is_active } : s,
        ),
      );
    } catch (e) {
      notify.error("Failed to update: " + (e.message || "Unknown error"));
    }
  };

  const handleDelete = async (seq) => {
    if (
      !confirm(`Delete "${seq.name}"? This will stop all active enrollments.`)
    )
      return;
    try {
      await deleteEmailSequence(seq.id, token);
      setSequences((prev) => prev.filter((s) => s.id !== seq.id));
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  const totalActive = sequences.filter((s) => s.is_active).length;
  const totalEnrollments = sequences.reduce(
    (acc, s) => acc + (s.enrollment_count || 0),
    0,
  );

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 28,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--text-primary)",
            }}
          >
            Email Sequences
          </h1>
          <p
            style={{
              margin: "4px 0 0",
              color: "var(--text-secondary)",
              fontSize: "0.875rem",
            }}
          >
            Automated drip email series triggered by lead events
          </p>
        </div>
        <button style={btnPrimary} onClick={() => setShowCreate(true)}>
          + New Sequence
        </button>
      </div>

      <div
        style={{ display: "flex", gap: 16, marginBottom: 28, flexWrap: "wrap" }}
      >
        <StatCard
          label="Total Sequences"
          value={loading ? "..." : sequences.length}
        />
        <StatCard
          label="Active Sequences"
          value={loading ? "..." : totalActive}
          color="var(--green)"
        />
        <StatCard
          label="Total Enrollments"
          value={loading ? "..." : totalEnrollments}
          color="var(--accent)"
        />
      </div>

      {error && (
        <div
          style={{
            background: "rgba(248,113,113,0.1)",
            border: "1px solid rgba(248,113,113,0.2)",
            borderRadius: 10,
            padding: "14px 18px",
            marginBottom: 20,
            color: "#f87171",
            fontSize: "0.875rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>{error}</span>
          <button
            style={{ ...btnSecondary, fontSize: "0.8rem" }}
            onClick={loadSequences}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && sequences.length === 0 && !error ? (
        <EmptyState onCreateFirst={() => setShowCreate(true)} />
      ) : (
        <div style={cardStyle}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {[
                    "Name",
                    "Trigger",
                    "Active",
                    "Steps",
                    "Enrollments",
                    "Created",
                    "Actions",
                  ].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 16px",
                        textAlign: "left",
                        fontSize: "0.78rem",
                        color: "var(--text-secondary)",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingRows count={4} />
                ) : (
                  sequences.map((seq) => (
                    <tr
                      key={seq.id}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background =
                          "var(--hover-overlay)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "transparent";
                      }}
                    >
                      <td style={{ padding: "14px 16px" }}>
                        <button
                          onClick={() => setDetailSequenceId(seq.id)}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            color: "var(--text-primary)",
                            fontWeight: 600,
                            fontSize: "0.9rem",
                            textAlign: "left",
                            padding: 0,
                          }}
                        >
                          {seq.name}
                        </button>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <TriggerBadge type={seq.trigger_type} />
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <Toggle
                          checked={seq.is_active}
                          onChange={() => handleToggleActive(seq)}
                        />
                      </td>
                      <td
                        style={{
                          padding: "14px 16px",
                          color: "var(--text-secondary)",
                          fontSize: "0.875rem",
                        }}
                      >
                        {seq.step_count ?? "—"}
                      </td>
                      <td
                        style={{
                          padding: "14px 16px",
                          color: "var(--text-secondary)",
                          fontSize: "0.875rem",
                        }}
                      >
                        {seq.enrollment_count ?? 0}
                      </td>
                      <td
                        style={{
                          padding: "14px 16px",
                          color: "var(--text-secondary)",
                          fontSize: "0.8rem",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {seq.created_at
                          ? new Date(seq.created_at).toLocaleDateString(
                              "en-US",
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              },
                            )
                          : "—"}
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            style={btnSecondary}
                            onClick={() => setEditSequence(seq)}
                          >
                            Edit
                          </button>
                          <button
                            style={btnDanger}
                            onClick={() => handleDelete(seq)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreate && (
        <SequenceModal
          sequence={null}
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            loadSequences();
          }}
        />
      )}

      {editSequence && (
        <SequenceModal
          sequence={editSequence}
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setEditSequence(null)}
          onSaved={() => {
            setEditSequence(null);
            loadSequences();
          }}
        />
      )}

      {detailSequenceId && (
        <SequenceDetail
          sequenceId={detailSequenceId}
          token={token}
          onClose={() => setDetailSequenceId(null)}
          onEdit={() => {
            const seq = sequences.find((s) => s.id === detailSequenceId);
            if (seq) {
              setDetailSequenceId(null);
              setEditSequence(seq);
            }
          }}
        />
      )}
    </div>
  );
}
