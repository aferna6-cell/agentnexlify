import { useState, useEffect } from "react";
import {
  getEmailSequence,
  fetchEmailSequenceEnrollments,
} from "../../utils/api/email-sequences";
import { cardStyle, btnSecondary, overlayStyle, modalStyle } from "./styles";
import { TriggerBadge, StatusBadge } from "./badges";

export function SequenceDetail({ sequenceId, token, onClose, onEdit }) {
  const [detail, setDetail] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("steps");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [detailRes, enrollRes] = await Promise.all([
          getEmailSequence(sequenceId, token).catch((e) => {
            console.warn("Failed to load email sequence:", e?.message);
            return null;
          }),
          fetchEmailSequenceEnrollments(sequenceId, token).catch((e) => {
            console.warn("Failed to load enrollments:", e?.message);
            return [];
          }),
        ]);
        setDetail(detailRes);
        setEnrollments(enrollRes?.enrollments || enrollRes || []);
      } catch {
        // non-critical, leave as empty
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [sequenceId, token]);

  const tabStyle = (active) => ({
    padding: "8px 18px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.85rem",
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-secondary)",
  });

  return (
    <div
      style={overlayStyle}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ ...modalStyle, maxWidth: 760 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: "1.15rem",
              color: "var(--text-primary)",
            }}
          >
            {loading ? "Loading..." : detail?.name || "Sequence Detail"}
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button style={btnSecondary} onClick={onEdit}>
              Edit
            </button>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-secondary)",
                fontSize: "1.4rem",
                lineHeight: 1,
              }}
            >
              &times;
            </button>
          </div>
        </div>

        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: 40,
              color: "var(--text-secondary)",
            }}
          >
            Loading sequence details...
          </div>
        ) : !detail ? (
          <div
            style={{
              textAlign: "center",
              padding: 40,
              color: "var(--text-secondary)",
            }}
          >
            Could not load sequence details.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                gap: 16,
                marginBottom: 20,
                flexWrap: "wrap",
              }}
            >
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  Trigger
                </div>
                <TriggerBadge type={detail.trigger_type} />
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  Steps
                </div>
                <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                  {detail.step_count ?? detail.steps?.length ?? 0}
                </span>
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  Enrollments
                </div>
                <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                  {detail.enrollment_count ?? enrollments.length}
                </span>
              </div>
              <div style={{ ...cardStyle, padding: "12px 18px", flex: "none" }}>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    marginBottom: 4,
                  }}
                >
                  Status
                </div>
                <span
                  style={{
                    fontWeight: 700,
                    color: detail.is_active
                      ? "var(--green)"
                      : "var(--text-secondary)",
                  }}
                >
                  {detail.is_active ? "Active" : "Paused"}
                </span>
              </div>
            </div>

            <div
              style={{
                display: "flex",
                gap: 4,
                marginBottom: 20,
                borderBottom: "1px solid var(--border)",
                paddingBottom: 12,
              }}
            >
              <button
                style={tabStyle(activeTab === "steps")}
                onClick={() => setActiveTab("steps")}
              >
                Steps
              </button>
              <button
                style={tabStyle(activeTab === "enrollments")}
                onClick={() => setActiveTab("enrollments")}
              >
                Enrollments ({enrollments.length})
              </button>
            </div>

            {activeTab === "steps" && (
              <div>
                {!detail.steps || detail.steps.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      padding: "32px",
                      color: "var(--text-secondary)",
                      fontSize: "0.875rem",
                    }}
                  >
                    No steps configured. Click Edit to add steps.
                  </div>
                ) : (
                  detail.steps.map((step, i) => (
                    <div
                      key={step.id || i}
                      style={{
                        background: "var(--bg-primary)",
                        border: "1px solid var(--border)",
                        borderRadius: 10,
                        padding: "14px 18px",
                        marginBottom: 10,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          marginBottom: 10,
                        }}
                      >
                        <div
                          style={{
                            width: 26,
                            height: 26,
                            borderRadius: "50%",
                            background: "var(--accent-dim)",
                            color: "var(--accent)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: "0.8rem",
                            flexShrink: 0,
                          }}
                        >
                          {i + 1}
                        </div>
                        <span
                          style={{
                            fontWeight: 600,
                            fontSize: "0.9rem",
                            color: "var(--text-primary)",
                            flex: 1,
                          }}
                        >
                          {step.email_type === "sms" ? "SMS" : "Email"} - Step{" "}
                          {i + 1}
                        </span>
                        <span
                          style={{
                            fontSize: "0.8rem",
                            color: "var(--text-secondary)",
                          }}
                        >
                          Delay: {step.delay_days || 0}d {step.delay_hours || 0}
                          h
                        </span>
                        <span
                          style={{
                            padding: "2px 8px",
                            borderRadius: 10,
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            background:
                              step.is_active !== false
                                ? "var(--green-dim)"
                                : "var(--hover-overlay)",
                            color:
                              step.is_active !== false
                                ? "var(--green)"
                                : "var(--text-secondary)",
                          }}
                        >
                          {step.is_active !== false ? "Active" : "Inactive"}
                        </span>
                      </div>
                      {step.subject && (
                        <div
                          style={{
                            fontSize: "0.85rem",
                            color: "var(--text-secondary)",
                            marginBottom: 6,
                          }}
                        >
                          <strong style={{ color: "var(--text-primary)" }}>
                            Subject:
                          </strong>{" "}
                          {step.subject}
                        </div>
                      )}
                      {step.body && (
                        <div
                          style={{
                            fontSize: "0.82rem",
                            color: "var(--text-secondary)",
                            background: "var(--bg-secondary)",
                            borderRadius: 6,
                            padding: "8px 12px",
                            whiteSpace: "pre-wrap",
                            maxHeight: 100,
                            overflowY: "auto",
                          }}
                        >
                          {step.body}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "enrollments" && (
              <div>
                {enrollments.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      padding: "32px",
                      color: "var(--text-secondary)",
                      fontSize: "0.875rem",
                    }}
                  >
                    No leads enrolled yet. Leads are enrolled automatically when
                    the trigger fires, or manually from the Clients page.
                  </div>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table
                      style={{ width: "100%", borderCollapse: "collapse" }}
                    >
                      <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          {["Lead", "Email", "Status", "Step", "Enrolled"].map(
                            (h) => (
                              <th
                                key={h}
                                style={{
                                  padding: "10px 12px",
                                  textAlign: "left",
                                  fontSize: "0.78rem",
                                  color: "var(--text-secondary)",
                                  fontWeight: 600,
                                  textTransform: "uppercase",
                                  letterSpacing: "0.05em",
                                }}
                              >
                                {h}
                              </th>
                            ),
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {enrollments.map((e) => (
                          <tr
                            key={e.id}
                            style={{ borderBottom: "1px solid var(--border)" }}
                          >
                            <td
                              style={{
                                padding: "12px",
                                fontSize: "0.875rem",
                                color: "var(--text-primary)",
                                fontWeight: 500,
                              }}
                            >
                              {e.lead_name || "—"}
                            </td>
                            <td
                              style={{
                                padding: "12px",
                                fontSize: "0.875rem",
                                color: "var(--text-secondary)",
                              }}
                            >
                              {e.lead_email || "—"}
                            </td>
                            <td style={{ padding: "12px" }}>
                              <StatusBadge status={e.status} />
                            </td>
                            <td
                              style={{
                                padding: "12px",
                                fontSize: "0.875rem",
                                color: "var(--text-secondary)",
                              }}
                            >
                              Step {e.current_step ?? "—"}
                            </td>
                            <td
                              style={{
                                padding: "12px",
                                fontSize: "0.8rem",
                                color: "var(--text-secondary)",
                              }}
                            >
                              {e.enrolled_at
                                ? new Date(e.enrolled_at).toLocaleDateString(
                                    "en-US",
                                    {
                                      month: "short",
                                      day: "numeric",
                                      year: "numeric",
                                    },
                                  )
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
