import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

const PLAN_LABELS = {
  free: "Free",
  growth: "Growth",
  professional: "Professional",
  autopilot: "Autopilot",
  enterprise: "Enterprise",
};

const HEALTH_COLORS = {
  red: "#f87171",
  yellow: "var(--yellow, #f59e0b)",
  green: "var(--green)",
};

const HEALTH_ORDER = { red: 0, yellow: 1, green: 2 };

// Admin secret is entered at runtime via prompt - never baked into the JS bundle.
let _adminSecret = "";

function getAdminSecret() {
  if (!_adminSecret) {
    _adminSecret = window.prompt("Enter admin secret:") || "";
  }
  return _adminSecret;
}

function clearAdminSecret() {
  _adminSecret = "";
}

async function apiFetch(path) {
  const secret = getAdminSecret();
  if (!secret) throw new Error("No admin secret provided");
  const res = await fetch(`${BASE}/api/v1/admin${path}`, {
    headers: {
      "x-api-secret": secret,
      "Content-Type": "application/json",
    },
  });
  if (res.status === 401) {
    clearAdminSecret();
    throw new Error("Invalid admin secret - cleared. Refresh to retry.");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function HealthBadge({ health }) {
  const color = HEALTH_COLORS[health] || "var(--text-muted)";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: "0.8rem",
        fontWeight: 600,
        color,
        textTransform: "capitalize",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {health}
    </span>
  );
}

export default function AdminHealthPage() {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    if (!getAdminSecret()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/tenant-health");
      const list = Array.isArray(data) ? data : [];
      // Backend already sorts red first — re-sort defensively.
      list.sort(
        (a, b) =>
          (HEALTH_ORDER[a.health] ?? 3) - (HEALTH_ORDER[b.health] ?? 3) ||
          (a.business_name || "").localeCompare(b.business_name || ""),
      );
      setRows(list);
    } catch (err) {
      console.error("Admin health load failed:", err.message);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (!_adminSecret) {
    return (
      <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
        <div
          style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}
        >
          <h2 style={{ color: "var(--text-primary)" }}>
            Admin Access Required
          </h2>
          <p style={{ color: "var(--text-secondary)" }}>
            Refresh the page and enter the admin secret when prompted.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
        <div
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: "40px",
            color: "var(--text-secondary)",
          }}
        >
          Loading tenant health...
        </div>
      </div>
    );
  }

  const counts = rows.reduce(
    (acc, r) => {
      acc[r.health] = (acc[r.health] || 0) + 1;
      return acc;
    },
    { red: 0, yellow: 0, green: 0 },
  );

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1400 }}>
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
            Tenant Health
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Every tenant, red first — leads activity and stuck approval drafts
          </p>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {["red", "yellow", "green"].map((h) => (
            <div
              key={h}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: "0.85rem",
                color: "var(--text-secondary)",
              }}
            >
              <HealthBadge health={h} />
              <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                {counts[h]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div
          style={{
            ...cardStyle,
            marginBottom: 24,
            color: "#f87171",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}

      <div style={cardStyle}>
        {rows.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "separate",
                borderSpacing: 0,
              }}
            >
              <thead>
                <tr>
                  {[
                    "Health",
                    "Business",
                    "Plan",
                    "Leads (7d)",
                    "Leads (total)",
                    "Last Lead",
                    "Pending Drafts",
                    "Rotting (48h+)",
                    "Signed Up",
                  ].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "10px 16px",
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        fontWeight: 600,
                        borderBottom: "1px solid var(--border)",
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
                {rows.map((t) => (
                  <tr
                    key={t.tenant_id}
                    style={{ transition: "background 0.15s" }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background =
                        "var(--hover-overlay)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td style={{ padding: "12px 16px" }}>
                      <HealthBadge health={t.health} />
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-primary)",
                        fontWeight: 600,
                      }}
                    >
                      {t.business_name || "(unnamed)"}
                      {t.is_demo && (
                        <span
                          style={{
                            marginLeft: 8,
                            fontSize: "0.7rem",
                            fontWeight: 600,
                            color: "var(--text-muted)",
                            border: "1px solid var(--border)",
                            borderRadius: 6,
                            padding: "1px 6px",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                          }}
                        >
                          Demo
                        </span>
                      )}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {PLAN_LABELS[t.plan] || t.plan || "—"}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color:
                          t.leads_7d > 0
                            ? "var(--green)"
                            : "var(--text-muted)",
                        fontWeight: 600,
                      }}
                    >
                      {t.leads_7d}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {t.leads_total}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-secondary)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDate(t.last_lead_at)}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color:
                          t.pending_drafts > 3
                            ? "var(--yellow, #f59e0b)"
                            : "var(--text-secondary)",
                        fontWeight: t.pending_drafts > 3 ? 600 : 400,
                      }}
                    >
                      {t.pending_drafts}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color:
                          t.drafts_rotting > 0
                            ? "#f87171"
                            : "var(--text-muted)",
                        fontWeight: t.drafts_rotting > 0 ? 600 : 400,
                      }}
                    >
                      {t.drafts_rotting}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {formatDate(t.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-secondary)",
            }}
          >
            <p style={{ margin: "0 0 8px", fontWeight: 600 }}>
              No tenants yet
            </p>
            <p style={{ margin: 0, fontSize: "0.85rem" }}>
              Health rows appear as soon as the first business signs up. Red
              means no leads ever (7+ days old) or approval drafts stuck 48h+;
              yellow means quiet for a week or a draft backlog.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
