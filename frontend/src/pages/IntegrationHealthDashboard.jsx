import { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getWidgetHealth,
  updateAllowedDomains,
} from "../utils/api/widgetHealth";
import SkeletonLoader from "../components/SkeletonLoader";

// --- Status dot colors ---
const STATUS_COLOR = {
  ok: "var(--green)",
  warn: "var(--yellow)",
  fail: "var(--red)",
};

const STATUS_BG = {
  ok: "var(--green-dim)",
  warn: "var(--yellow-dim)",
  fail: "var(--red-dim)",
};

// --- Overall banner config ---
const OVERALL_META = {
  healthy: {
    label: "You're live",
    color: "var(--green)",
    bg: "var(--green-dim)",
    border: "rgba(52, 211, 153, 0.28)",
  },
  needs_attention: {
    label: "A few things to finish",
    color: "var(--yellow)",
    bg: "var(--yellow-dim)",
    border: "rgba(245, 166, 35, 0.28)",
  },
  not_ready: {
    label: "Setup incomplete",
    color: "var(--red)",
    bg: "var(--red-dim)",
    border: "rgba(255, 68, 68, 0.28)",
  },
};

function StatusDot({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: STATUS_COLOR[status] || "var(--text-muted)",
        flexShrink: 0,
        marginTop: 2,
      }}
    />
  );
}

function StatCard({ label, value }) {
  return (
    <div className="ih-stat-card">
      <div className="ih-stat-label">{label}</div>
      <div className="ih-stat-value">{value}</div>
      <div className="ih-stat-hint">last 7 days</div>
    </div>
  );
}

export default function IntegrationHealthDashboard({ onNavigate }) {
  const { user, token } = useAuth();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  // Allowed domains editor state
  const [domains, setDomains] = useState([]);
  const [domainInput, setDomainInput] = useState("");
  const [domainSaving, setDomainSaving] = useState(false);
  const [domainMsg, setDomainMsg] = useState(null); // {type: "success"|"error", text: string}
  const domainMsgTimerRef = useRef(null);

  useEffect(() => {
    if (!user?.tenantId || !token) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const result = await getWidgetHealth(user.tenantId, token);
        if (!cancelled) {
          setData(result);
          setDomains(result.allowed_domains || []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Couldn't load setup health.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [user?.tenantId, token, reloadKey]);

  // --- Domain helpers ---

  function showDomainMsg(type, text) {
    clearTimeout(domainMsgTimerRef.current);
    setDomainMsg({ type, text });
    domainMsgTimerRef.current = setTimeout(() => setDomainMsg(null), 4000);
  }

  function handleAddDomain() {
    const trimmed = domainInput.trim().toLowerCase();
    if (!trimmed) return;
    if (domains.includes(trimmed)) {
      showDomainMsg("error", "Domain already in list.");
      return;
    }
    setDomains((prev) => [...prev, trimmed]);
    setDomainInput("");
  }

  function handleRemoveDomain(domain) {
    setDomains((prev) => prev.filter((d) => d !== domain));
  }

  async function handleSaveDomains() {
    if (!user?.tenantId || !token) return;
    setDomainSaving(true);
    try {
      const result = await updateAllowedDomains(user.tenantId, token, domains);
      setDomains(result.allowed_domains || domains);
      showDomainMsg("success", "Allowed domains saved.");
    } catch (err) {
      showDomainMsg("error", err.message || "Failed to save domains.");
    } finally {
      setDomainSaving(false);
    }
  }

  function handleDomainKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddDomain();
    }
  }

  // --- Render states ---

  if (loading && !data) {
    return <SkeletonLoader />;
  }

  if (error && !data) {
    return (
      <div className="ih-page">
        <div className="ih-card ih-empty">
          <h2 style={{ margin: "0 0 10px" }}>Setup Health</h2>
          <p style={{ color: "var(--text-secondary)", marginBottom: 18 }}>
            {error}
          </p>
          <button
            className="btn-primary"
            onClick={() => setReloadKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const overall = data?.overall || "not_ready";
  const checks = data?.checks || [];
  const stats = data?.stats || {};
  const overallMeta = OVERALL_META[overall] || OVERALL_META.not_ready;

  return (
    <div className="ih-page">
      <style>{`
        .ih-page {
          display: flex;
          flex-direction: column;
          gap: 24px;
          color: var(--text-primary);
        }
        .ih-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
          flex-wrap: wrap;
        }
        .ih-header h1 {
          margin: 0 0 4px;
          font-size: 1.75rem;
          line-height: 1.1;
        }
        .ih-header p {
          margin: 0;
          color: var(--text-secondary);
          font-size: 0.93rem;
        }
        .ih-banner {
          padding: 14px 20px;
          border-radius: var(--radius);
          border: 1px solid;
          font-weight: 600;
          font-size: 0.95rem;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .ih-banner-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .ih-stats-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }
        .ih-stat-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 20px;
        }
        .ih-stat-label {
          color: var(--text-secondary);
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          margin-bottom: 10px;
        }
        .ih-stat-value {
          font-size: 2rem;
          font-weight: 700;
          line-height: 1;
          margin-bottom: 6px;
        }
        .ih-stat-hint {
          color: var(--text-muted);
          font-size: 0.85rem;
        }
        .ih-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 24px;
        }
        .ih-card-title {
          margin: 0 0 18px;
          font-size: 1.05rem;
          font-weight: 600;
        }
        .ih-checks-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ih-check-item {
          display: flex;
          align-items: flex-start;
          gap: 14px;
          padding: 14px 16px;
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          background: rgba(255, 255, 255, 0.02);
        }
        .ih-check-body {
          flex: 1;
          min-width: 0;
        }
        .ih-check-label {
          font-weight: 600;
          font-size: 0.93rem;
          margin-bottom: 4px;
        }
        .ih-check-detail {
          color: var(--text-secondary);
          font-size: 0.87rem;
          line-height: 1.5;
        }
        .ih-check-action {
          margin-top: 8px;
        }
        .ih-action-btn {
          background: var(--accent-dim);
          color: var(--accent);
          border: 1px solid rgba(0, 191, 255, 0.22);
          border-radius: var(--radius-sm);
          padding: 6px 12px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s ease;
        }
        .ih-action-btn:hover {
          background: rgba(0, 191, 255, 0.22);
        }
        .ih-empty {
          text-align: center;
          color: var(--text-secondary);
        }
        .ih-empty p {
          margin: 0;
        }
        .ih-domains-section {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .ih-domains-empty {
          color: var(--text-secondary);
          font-size: 0.88rem;
          padding: 10px 0;
        }
        .ih-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .ih-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(148, 163, 184, 0.1);
          border: 1px solid var(--border);
          border-radius: 999px;
          padding: 5px 10px;
          font-size: 0.83rem;
          color: var(--text-secondary);
        }
        .ih-chip-remove {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 0;
          font-size: 1rem;
          line-height: 1;
          display: flex;
          align-items: center;
          transition: color 0.15s ease;
        }
        .ih-chip-remove:hover {
          color: var(--red);
        }
        .ih-domain-input-row {
          display: flex;
          gap: 10px;
          align-items: stretch;
        }
        .ih-domain-input {
          flex: 1;
          background: var(--bg-secondary);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 9px 14px;
          color: var(--text-primary);
          font-size: 0.9rem;
          outline: none;
          transition: border-color 0.15s ease;
        }
        .ih-domain-input:focus {
          border-color: var(--accent);
        }
        .ih-add-btn {
          background: var(--bg-secondary);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 9px 16px;
          color: var(--text-primary);
          font-weight: 600;
          font-size: 0.88rem;
          cursor: pointer;
          white-space: nowrap;
          transition: border-color 0.15s ease;
        }
        .ih-add-btn:hover {
          border-color: var(--accent);
          color: var(--accent);
        }
        .ih-save-row {
          display: flex;
          align-items: center;
          gap: 14px;
          flex-wrap: wrap;
        }
        .ih-save-btn {
          background: var(--accent-dim);
          color: var(--accent);
          border: 1px solid rgba(0, 191, 255, 0.22);
          border-radius: var(--radius-sm);
          padding: 9px 20px;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: background 0.15s ease;
        }
        .ih-save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .ih-save-btn:not(:disabled):hover {
          background: rgba(0, 191, 255, 0.22);
        }
        .ih-msg {
          font-size: 0.88rem;
          padding: 7px 12px;
          border-radius: var(--radius-sm);
          border: 1px solid;
        }
        .ih-msg.success {
          color: var(--green);
          background: var(--green-dim);
          border-color: rgba(52, 211, 153, 0.28);
        }
        .ih-msg.error {
          color: var(--red);
          background: var(--red-dim);
          border-color: rgba(255, 68, 68, 0.28);
        }
        @media (max-width: 720px) {
          .ih-stats-row {
            grid-template-columns: 1fr;
          }
          .ih-domain-input-row {
            flex-direction: column;
          }
        }
      `}</style>

      {/* Header */}
      <div className="ih-header">
        <div>
          <h1>Setup Health</h1>
          <p>
            Check that your widget is configured correctly and tracking
            activity.
          </p>
        </div>
        <button
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            padding: "8px 14px",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
          onClick={() => setReloadKey((k) => k + 1)}
        >
          Refresh
        </button>
      </div>

      {/* Overall status banner */}
      <div
        className="ih-banner"
        style={{
          color: overallMeta.color,
          background: overallMeta.bg,
          borderColor: overallMeta.border,
        }}
      >
        <span
          className="ih-banner-dot"
          style={{ background: overallMeta.color }}
        />
        {overallMeta.label}
      </div>

      {/* Stats row */}
      <div className="ih-stats-row">
        <StatCard label="Leads captured" value={stats.leads_7d ?? 0} />
        <StatCard label="Conversations" value={stats.conversations_7d ?? 0} />
        <StatCard
          label="Appointments booked"
          value={stats.appointments_7d ?? 0}
        />
      </div>

      {/* Checks list */}
      <div className="ih-card">
        <h2 className="ih-card-title">Health Checks</h2>
        {checks.length === 0 ? (
          <div className="ih-empty">
            <p>
              No checks available yet. Configure your widget to see health data
              here.
            </p>
          </div>
        ) : (
          <div className="ih-checks-list">
            {checks.map((check) => (
              <div key={check.id} className="ih-check-item">
                <StatusDot status={check.status} />
                <div className="ih-check-body">
                  <div className="ih-check-label">{check.label}</div>
                  {check.detail && (
                    <div className="ih-check-detail">{check.detail}</div>
                  )}
                  {check.action && (
                    <div className="ih-check-action">
                      {onNavigate ? (
                        <button
                          className="ih-action-btn"
                          onClick={() => onNavigate(check.action.target)}
                        >
                          {check.action.label}
                        </button>
                      ) : (
                        <span
                          style={{
                            fontSize: "0.82rem",
                            color: "var(--accent)",
                            fontWeight: 600,
                          }}
                        >
                          {check.action.label}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: STATUS_COLOR[check.status] || "var(--text-muted)",
                    background: STATUS_BG[check.status] || "transparent",
                    flexShrink: 0,
                    alignSelf: "flex-start",
                  }}
                >
                  {check.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Allowed domains editor */}
      <div className="ih-card">
        <h2 className="ih-card-title">Allowed Domains</h2>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "0.88rem",
            marginBottom: 16,
          }}
        >
          Restrict which domains can load your widget. Leave empty to allow any
          origin.
        </p>

        <div className="ih-domains-section">
          {domains.length === 0 ? (
            <div className="ih-domains-empty">
              No domains set — your widget currently accepts any origin.
            </div>
          ) : (
            <div className="ih-chips">
              {domains.map((domain) => (
                <span key={domain} className="ih-chip">
                  {domain}
                  <button
                    className="ih-chip-remove"
                    onClick={() => handleRemoveDomain(domain)}
                    aria-label={`Remove ${domain}`}
                    title={`Remove ${domain}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="ih-domain-input-row">
            <input
              className="ih-domain-input"
              type="text"
              placeholder="example.com"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              onKeyDown={handleDomainKeyDown}
            />
            <button className="ih-add-btn" onClick={handleAddDomain}>
              Add
            </button>
          </div>

          <div className="ih-save-row">
            <button
              className="ih-save-btn"
              onClick={handleSaveDomains}
              disabled={domainSaving}
            >
              {domainSaving ? "Saving..." : "Save"}
            </button>
            {domainMsg && (
              <span className={`ih-msg ${domainMsg.type}`}>
                {domainMsg.text}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
