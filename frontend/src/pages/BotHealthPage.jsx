import { useState, useEffect, useCallback } from "react";
import { BASE } from "../utils/api/_client";

// ---------------------------------------------------------------------------
// BotHealthPage - frontend for GET /api/v1/admin/loop-health (GH #465).
// Renders the automation-loop vitals the endpoint computes so operations
// reviews stop re-deriving them with ad-hoc SQL. Admin-secret pattern is
// identical to AdminFunnelPage / AdminHealthPage: secret entered at runtime
// via window.prompt, never baked into the bundle.
// ---------------------------------------------------------------------------
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

const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

function StatCard({ label, value, sub, alert }) {
  return (
    <div
      style={{
        ...cardStyle,
        ...(alert ? { borderColor: "#f87171" } : {}),
      }}
    >
      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          color: alert ? "#f87171" : "var(--text-primary, #f1f5f9)",
          lineHeight: 1,
        }}
      >
        {value ?? "-"}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginTop: 6,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function StatusBreakdown({ title, byStatus }) {
  const entries = Object.entries(byStatus || {}).sort((a, b) => b[1] - a[1]);
  return (
    <div style={cardStyle}>
      <h3
        style={{
          margin: "0 0 14px",
          fontSize: "1rem",
          fontWeight: 600,
          color: "var(--text-primary, #f1f5f9)",
        }}
      >
        {title}
      </h3>
      {entries.length === 0 ? (
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          No rows yet
        </div>
      ) : (
        <table style={{ width: "100%", fontSize: "0.85rem" }}>
          <tbody>
            {entries.map(([status, count]) => (
              <tr key={status}>
                <td style={{ color: "var(--text-muted)", padding: "3px 0" }}>
                  {status}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    fontWeight: 600,
                    color: "var(--text-primary, #f1f5f9)",
                  }}
                >
                  {count}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function SectionUnavailable({ name }) {
  return (
    <div style={{ ...cardStyle, borderColor: "#f59e0b" }}>
      <div style={{ fontSize: "0.85rem", color: "#f59e0b" }}>
        {name} section unavailable - its query failed on the backend. Check
        backend logs.
      </div>
    </div>
  );
}

export default function BotHealthPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await apiFetch("/loop-health");
      setData(payload);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div style={{ padding: 32, color: "var(--text-muted)" }}>
        Loading loop health...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ ...cardStyle, borderColor: "#f87171" }}>
          <div style={{ color: "#f87171", fontWeight: 600, marginBottom: 8 }}>
            Failed to load loop health
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            {error}
          </div>
          <button
            className="btn-secondary"
            style={{ marginTop: 14 }}
            onClick={load}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const deliverables = data?.deliverables;
  const suggestions = data?.suggestions;
  const osActivity = data?.os_activity;
  const bridges = data?.bridges;
  const errors7d = data?.errors_7d;

  const pendingDrafts = deliverables?.by_status?.pending_approval ?? 0;
  const draftAge = deliverables?.pending_oldest_age_days;
  const pendingCards = suggestions?.by_status?.pending ?? 0;
  const cardAge = suggestions?.pending_oldest_age_days;

  return (
    <div style={{ padding: 32, display: "grid", gap: 20 }}>
      <div>
        <h2
          style={{
            margin: 0,
            color: "var(--text-primary, #f1f5f9)",
            fontSize: "1.4rem",
          }}
        >
          Agent OS Loop Health
        </h2>
        <div
          style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}
        >
          Generated {data?.generated_at || "-"} · same data as the daily
          loop-health scan · refresh for live numbers
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
          gap: 16,
        }}
      >
        <StatCard
          label="Pending drafts"
          value={pendingDrafts}
          sub={
            draftAge != null
              ? `oldest ${draftAge}d${draftAge > 1 ? " - review the queue" : ""}`
              : "none waiting"
          }
          alert={draftAge != null && draftAge > 1}
        />
        <StatCard
          label="Suggestions queued"
          value={pendingCards}
          sub={cardAge != null ? `oldest ${cardAge}d` : "none pending"}
          alert={cardAge != null && cardAge > 21}
        />
        <StatCard
          label="OS threads (7d)"
          value={osActivity?.threads_7d}
          sub={`${osActivity?.runs_7d ?? "-"} agent runs`}
        />
        <StatCard
          label="Bridges enabled"
          value={bridges?.tenants_enabled}
          sub={`${bridges?.tenants_configured ?? 0} tenant(s) configured`}
        />
        <StatCard
          label="Errors (7d)"
          value={errors7d}
          sub="error_events rows"
          alert={typeof errors7d === "number" && errors7d > 0}
        />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {deliverables ? (
          <StatusBreakdown
            title="Deliverables by status"
            byStatus={deliverables.by_status}
          />
        ) : (
          <SectionUnavailable name="Deliverables" />
        )}
        {suggestions ? (
          <StatusBreakdown
            title="Suggestions by status"
            byStatus={suggestions.by_status}
          />
        ) : (
          <SectionUnavailable name="Suggestions" />
        )}
      </div>

      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
        Sweep rot pages at 16d, suggestion rot at 21d (scripts/loop_health_scan.py).
        Expired drafts last 7d: {deliverables?.expired_7d ?? "-"} · suggestions
        filed last 24h: {suggestions?.filed_24h ?? "-"}
      </div>
    </div>
  );
}
