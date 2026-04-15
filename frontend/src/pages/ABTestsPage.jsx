import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { BASE } from "../utils/api/_client";
import SkeletonLoader from "../components/SkeletonLoader";
import { notify } from "../utils/notify";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

const btnSecondary = {
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "90%",
  maxWidth: 900,
  maxHeight: "90vh",
  overflowY: "auto",
  border: "1px solid var(--border)",
};

const TEST_TYPES = [
  {
    key: "subject_line",
    label: "Subject Line",
    desc: "Test different email subject lines",
  },
  {
    key: "send_time",
    label: "Send Time",
    desc: "Test different send times for same content",
  },
  {
    key: "body_content",
    label: "Body Content",
    desc: "Test different email body copy",
  },
  {
    key: "campaign_variant",
    label: "Campaign Variant",
    desc: "Fully different campaigns",
  },
];

const STATUS_STYLES = {
  draft: {
    label: "Draft",
    color: "var(--text-secondary)",
    bg: "var(--hover-overlay)",
  },
  running: {
    label: "Running",
    color: "var(--accent)",
    bg: "var(--accent-dim)",
  },
  completed: {
    label: "Completed",
    color: "var(--green)",
    bg: "var(--green-dim)",
  },
  paused: {
    label: "Paused",
    color: "var(--yellow, #f59e0b)",
    bg: "rgba(245,158,11,0.15)",
  },
};

const API_BASE = `${BASE}/api/v1`;

async function apiFetch(path, token, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.draft;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: s.color,
        background: s.bg,
      }}
    >
      {s.label}
    </span>
  );
}

function formatDate(d) {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function EmptyState({ message, icon }) {
  return (
    <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>
        {icon || "\ud83d\udd14"}
      </div>
      <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
        {message}
      </h3>
      <p style={{ color: "var(--text-secondary)", margin: 0 }}>
        Create your first A/B test to get started
      </p>
    </div>
  );
}

function CreateTestModal({ tenantId, token, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [testType, setTestType] = useState("subject_line");
  const [variants, setVariants] = useState([
    {
      name: "Variant A",
      subject: "",
      body: "",
      send_time_override: "",
      allocation_percent: 50,
    },
    {
      name: "Variant B",
      subject: "",
      body: "",
      send_time_override: "",
      allocation_percent: 50,
    },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const addVariant = () => {
    if (variants.length >= 4) return;
    const nextLetter = String.fromCharCode(65 + variants.length);
    setVariants((prev) => [
      ...prev,
      {
        name: `Variant ${nextLetter}`,
        subject: "",
        body: "",
        send_time_override: "",
        allocation_percent: Math.floor(100 / (variants.length + 1)),
      },
    ]);
    setVariants((prev) =>
      prev.map((v, i) => ({
        ...v,
        allocation_percent:
          i < prev.length - 1
            ? Math.floor(100 / prev.length)
            : 100 -
              prev
                .slice(0, prev.length - 1)
                .reduce((s, x) => s + x.allocation_percent, 0),
      })),
    );
  };

  const removeVariant = (idx) => {
    if (variants.length <= 2) return;
    setVariants((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateVariant = (idx, field, value) => {
    setVariants((prev) =>
      prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)),
    );
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Test name is required");
      return;
    }
    if (variants.length < 2) {
      setError("At least 2 variants required");
      return;
    }
    const totalAllocation = variants.reduce(
      (s, v) => s + (v.allocation_percent || 0),
      0,
    );
    if (totalAllocation !== 100) {
      setError("Variant allocations must sum to 100%");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch(`/ab-tests/${tenantId}`, token, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
          test_type: testType,
          variants: variants.map((v) => ({
            name: v.name,
            subject: v.subject || null,
            body: v.body || null,
            send_time_override: v.send_time_override || null,
            allocation_percent: v.allocation_percent,
          })),
        }),
      });
      onCreated();
    } catch (e) {
      setError(e.message || "Failed to create A/B test");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={modalStyle}>
        <h2
          style={{
            margin: "0 0 20px",
            color: "var(--text-primary)",
            fontSize: "1.2rem",
          }}
        >
          Create A/B Test
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            marginBottom: 16,
          }}
        >
          <div>
            <label style={labelStyle}>Test Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Summer Subject Line Test"
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Test Type</label>
            <select
              value={testType}
              onChange={(e) => setTestType(e.target.value)}
              style={inputStyle}
            >
              {TEST_TYPES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Description (optional)</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What are you testing and why?"
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: 8 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <label style={{ ...labelStyle, margin: 0 }}>
              Variants ({variants.length}/4)
            </label>
            {variants.length < 4 && (
              <button
                onClick={addVariant}
                style={{
                  ...btnSecondary,
                  padding: "4px 12px",
                  fontSize: "0.8rem",
                }}
              >
                + Add Variant
              </button>
            )}
          </div>
        </div>

        {variants.map((v, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--bg-primary)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                {v.name}
              </span>
              {variants.length > 2 && (
                <button
                  onClick={() => removeVariant(idx)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                  }}
                >
                  Remove
                </button>
              )}
            </div>

            {testType === "subject_line" && (
              <input
                type="text"
                value={v.subject}
                onChange={(e) => updateVariant(idx, "subject", e.target.value)}
                placeholder="Subject line for this variant"
                style={{ ...inputStyle, marginBottom: 8 }}
              />
            )}

            {testType === "body_content" && (
              <textarea
                value={v.body}
                onChange={(e) => updateVariant(idx, "body", e.target.value)}
                placeholder="Email body for this variant"
                rows={4}
                style={{ ...inputStyle, resize: "vertical", marginBottom: 8 }}
              />
            )}

            {testType === "send_time" && (
              <input
                type="time"
                value={v.send_time_override}
                onChange={(e) =>
                  updateVariant(idx, "send_time_override", e.target.value)
                }
                style={inputStyle}
              />
            )}

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 8,
              }}
            >
              <label
                style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}
              >
                Allocation:
              </label>
              <input
                type="number"
                value={v.allocation_percent}
                min={1}
                max={99}
                onChange={(e) =>
                  updateVariant(
                    idx,
                    "allocation_percent",
                    parseInt(e.target.value) || 0,
                  )
                }
                style={{ ...inputStyle, width: 80 }}
              />
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                %
              </span>
            </div>
          </div>
        ))}

        <div style={{ marginBottom: 16 }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Total allocation:{" "}
            {variants.reduce((s, v) => s + (v.allocation_percent || 0), 0)}%
            {variants.reduce((s, v) => s + (v.allocation_percent || 0), 0) !==
              100 && (
              <span style={{ color: "#f87171", marginLeft: 8 }}>
                (must equal 100%)
              </span>
            )}
          </span>
        </div>

        {error && (
          <div
            style={{ color: "#f87171", fontSize: "0.85rem", marginBottom: 12 }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={btnSecondary}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{ ...btnPrimary, opacity: submitting ? 0.6 : 1 }}
          >
            {submitting ? "Creating..." : "Create A/B Test"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ResultsPanel({ test, onClose }) {
  const { user, token } = useAuth();
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.tenantId || !token || !test?.id) return;
    setLoading(true);
    apiFetch(`/ab-tests/${user.tenantId}/${test.id}/results`, token)
      .then(setResults)
      .catch(() => setResults(null))
      .finally(() => setLoading(false));
  }, [user?.tenantId, token, test?.id]);

  const chartData = results?.variants?.map((v) => ({
    name: v.variant?.name || v.name || "Unknown",
    open_rate: v.metrics?.open_rate ?? v.open_rate ?? 0,
    click_rate: v.metrics?.click_rate ?? v.click_rate ?? 0,
    sent: v.metrics?.sent ?? v.sent ?? 0,
  })) || [];

  return (
    <div style={{ ...cardStyle, marginTop: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 20,
        }}
      >
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: "1.2rem",
              color: "var(--text-primary)",
            }}
          >
            Results: {test.name}
          </h2>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--text-secondary)",
              margin: "4px 0 0",
            }}
          >
            {test.test_type?.replace("_", " ")} Test
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: "1.2rem",
          }}
        >
          &#x2715;
        </button>
      </div>

      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "var(--text-secondary)",
          }}
        >
          Loading results...
        </div>
      ) : results ? (
        <>
          {results.winner && (
            <div
              style={{
                background: "var(--green-dim)",
                border: "1px solid var(--green)",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 20,
                color: "var(--green)",
                fontWeight: 600,
              }}
            >
              Winner: {results.winner.name} (confidence:{" "}
              {results.winner.confidence
                ? `${(results.winner.confidence * 100).toFixed(1)}%`
                : "N/A"}
              )
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 12,
              marginBottom: 20,
            }}
          >
            {(results.variants || []).map((v) => {
              const metrics = v.metrics || {};
              const variant = v.variant || {};
              const isWinner = v.is_winner || variant.is_winner || false;
              return (
                <div
                  key={v.variant?.id || v.id}
                  style={{
                    background: isWinner
                      ? "var(--green-dim)"
                      : "var(--bg-primary)",
                    border: `1px solid ${isWinner ? "var(--green)" : "var(--border)"}`,
                    borderRadius: 8,
                    padding: "16px 20px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 8,
                    }}
                  >
                    <span
                      style={{ fontWeight: 700, color: "var(--text-primary)" }}
                    >
                      {variant.name || v.name || "Unknown"}
                    </span>
                    {isWinner && (
                      <span
                        style={{
                          color: "var(--green)",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                        }}
                      >
                        WINNER
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 1fr",
                      gap: 8,
                      fontSize: "0.85rem",
                    }}
                  >
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Sent
                      </div>
                      <div
                        style={{
                          fontWeight: 600,
                          color: "var(--text-primary)",
                        }}
                      >
                        {metrics.sent ?? 0}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Open Rate
                      </div>
                      <div style={{ fontWeight: 600, color: "var(--accent)" }}>
                        {metrics.open_rate != null
                          ? `${metrics.open_rate.toFixed(1)}%`
                          : "--"}
                      </div>
                    </div>
                    <div>
                      <div
                        style={{ color: "var(--text-muted)", marginBottom: 2 }}
                      >
                        Click Rate
                      </div>
                      <div style={{ fontWeight: 600, color: "var(--green)" }}>
                        {metrics.click_rate != null
                          ? `${metrics.click_rate.toFixed(1)}%`
                          : "--"}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {chartData.length > 0 && (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v.toFixed(0)}%`}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--text-primary)",
                  }}
                  formatter={(v) => [`${v.toFixed(1)}%`]}
                />
                <Legend
                  wrapperStyle={{
                    color: "var(--text-secondary)",
                    fontSize: "0.8rem",
                  }}
                />
                <Bar
                  dataKey="open_rate"
                  fill="var(--accent)"
                  radius={[4, 4, 0, 0]}
                  name="Open Rate"
                />
                <Bar
                  dataKey="click_rate"
                  fill="var(--green)"
                  radius={[4, 4, 0, 0]}
                  name="Click Rate"
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </>
      ) : (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "var(--text-secondary)",
          }}
        >
          No results data available yet
        </div>
      )}
    </div>
  );
}

export default function ABTestsPage() {
  const { user, token } = useAuth();
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTest, setSelectedTest] = useState(null);

  const loadTests = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/ab-tests/${user.tenantId}`, token);
      setTests(Array.isArray(res) ? res : (res.ab_tests || res.tests || []));
    } catch {
      setTests([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadTests();
  }, [loadTests]);

  const handleStartTest = async (testId) => {
    try {
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}/start`, token, {
        method: "POST",
      });
      loadTests();
    } catch (e) {
      notify.error("Failed to start: " + (e.message || "Unknown error"));
    }
  };

  const handleCompleteTest = async (testId) => {
    if (!confirm("Complete this test and select a winner?")) return;
    try {
      // Fetch test details to get variants
      const testRes = await apiFetch(
        `/ab-tests/${user.tenantId}/${testId}`,
        token,
      );
      const variants = testRes.variants || [];
      if (variants.length === 0) {
        notify.error("No variants found for this test");
        return;
      }
      // Show variant selection prompt
      const options = variants.map((v, i) => `${i + 1}. ${v.name}`).join("\n");
      const choice = prompt(`Select winner:\n${options}\n\nEnter number:`);
      const idx = parseInt(choice) - 1;
      if (isNaN(idx) || idx < 0 || idx >= variants.length) {
        notify.error("Invalid selection");
        return;
      }
      const winnerVariantId = variants[idx].id;
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}/complete`, token, {
        method: "POST",
        body: JSON.stringify({ variant_id: winnerVariantId }),
      });
      loadTests();
      if (selectedTest?.id === testId) {
        setSelectedTest((prev) => ({ ...prev, status: "completed" }));
      }
    } catch (e) {
      notify.error("Failed to complete: " + (e.message || "Unknown error"));
    }
  };

  const handleDelete = async (testId) => {
    if (!confirm("Delete this A/B test?")) return;
    try {
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}`, token, {
        method: "DELETE",
      });
      setTests((prev) => prev.filter((t) => t.id !== testId));
      if (selectedTest?.id === testId) setSelectedTest(null);
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  if (loading && tests.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            A/B Tests
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Compare campaign variants to optimize performance
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} style={btnPrimary}>
          + Create A/B Test
        </button>
      </div>

      {/* Stats Row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Tests", value: tests.length },
          {
            label: "Running",
            value: tests.filter((t) => t.status === "running").length,
          },
          {
            label: "Completed",
            value: tests.filter((t) => t.status === "completed").length,
          },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Test List */}
      {tests.length === 0 ? (
        <EmptyState message="No A/B tests yet" />
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "separate",
              borderSpacing: 0,
              background: "var(--bg-secondary, var(--card-bg))",
              border: "1px solid var(--border)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <thead>
              <tr>
                {[
                  "Name",
                  "Type",
                  "Status",
                  "Variants",
                  "Started",
                  "Actions",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: "left",
                      padding: "12px 16px",
                      fontSize: "0.8rem",
                      color: "var(--text-muted)",
                      fontWeight: 600,
                      borderBottom: "1px solid var(--border)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tests.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTest(t)}
                  style={{ cursor: "pointer", transition: "background 0.15s" }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = "var(--hover-overlay)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                >
                  <td
                    style={{
                      padding: "12px 16px",
                      color: "var(--text-primary)",
                      fontWeight: 600,
                    }}
                  >
                    {t.name || "Untitled Test"}
                  </td>
                  <td
                    style={{
                      padding: "12px 16px",
                      color: "var(--text-secondary)",
                      fontSize: "0.85rem",
                      textTransform: "capitalize",
                    }}
                  >
                    {t.test_type?.replace("_", " ") || "—"}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <StatusBadge status={t.status} />
                  </td>
                  <td
                    style={{
                      padding: "12px 16px",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {t.variants?.length ||
                      t.variant_count ||
                      t.ab_test_variants?.length ||
                      0}
                  </td>
                  <td
                    style={{
                      padding: "12px 16px",
                      fontSize: "0.85rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    {formatDate(t.started_at)}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      {t.status === "draft" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartTest(t.id);
                          }}
                          style={{
                            ...btnPrimary,
                            padding: "4px 10px",
                            fontSize: "0.75rem",
                          }}
                        >
                          Start
                        </button>
                      )}
                      {t.status === "running" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCompleteTest(t.id);
                          }}
                          style={{
                            ...btnSecondary,
                            padding: "4px 10px",
                            fontSize: "0.75rem",
                          }}
                        >
                          Complete
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(t.id);
                        }}
                        style={{
                          background: "none",
                          border: "1px solid var(--border)",
                          color: "var(--text-muted)",
                          padding: "4px 10px",
                          borderRadius: 6,
                          cursor: "pointer",
                          fontSize: "0.75rem",
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Results Panel */}
      {selectedTest && (
        <ResultsPanel
          test={selectedTest}
          onClose={() => setSelectedTest(null)}
        />
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateTestModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            loadTests();
          }}
        />
      )}
    </div>
  );
}
