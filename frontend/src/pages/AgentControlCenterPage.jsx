import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchAgentControlCenter } from "../utils/api/analytics";
import SkeletonLoader from "../components/SkeletonLoader";

const PERIODS = [
  { value: "7d", label: "7 days" },
  { value: "14d", label: "14 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
];

const STATUS_META = {
  strong: { label: "Strong", color: "var(--green)", bg: "rgba(34, 197, 94, 0.14)" },
  watch: { label: "Watch", color: "var(--yellow)", bg: "rgba(245, 158, 11, 0.14)" },
  at_risk: { label: "At Risk", color: "var(--red)", bg: "rgba(239, 68, 68, 0.14)" },
};

const RESOLUTION_META = {
  won: { color: "var(--green)", bg: "rgba(34, 197, 94, 0.14)" },
  booked: { color: "var(--green)", bg: "rgba(34, 197, 94, 0.14)" },
  resolved: { color: "var(--green)", bg: "rgba(34, 197, 94, 0.14)" },
  open: { color: "var(--yellow)", bg: "rgba(245, 158, 11, 0.14)" },
  in_progress: { color: "var(--yellow)", bg: "rgba(245, 158, 11, 0.14)" },
  abandoned: { color: "var(--red)", bg: "rgba(239, 68, 68, 0.14)" },
  lost: { color: "var(--red)", bg: "rgba(239, 68, 68, 0.14)" },
};

const URGENCY_META = {
  high: { label: "High", color: "var(--red)", bg: "rgba(239, 68, 68, 0.14)" },
  medium: { label: "Medium", color: "var(--yellow)", bg: "rgba(245, 158, 11, 0.14)" },
  low: { label: "Low", color: "var(--accent)", bg: "var(--accent-dim)" },
};

function formatPercent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatSeconds(value) {
  if (value === null || value === undefined) return "No reply data";
  const seconds = Number(value);
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} hr`;
}

function formatDate(value) {
  if (!value) return "Unknown";
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function SummaryCard({ label, value, hint }) {
  return (
    <div className="agent-control-card agent-control-summary-card">
      <div className="agent-control-summary-label">{label}</div>
      <div className="agent-control-summary-value">{value}</div>
      <div className="agent-control-summary-hint">{hint}</div>
    </div>
  );
}

function Badge({ meta, text }) {
  return (
    <span
      className="agent-control-badge"
      style={{ color: meta.color, background: meta.bg }}
    >
      {text}
    </span>
  );
}

function FunnelBar({ label, value, maxValue, helper }) {
  const width = maxValue > 0 ? Math.max((value / maxValue) * 100, 8) : 8;
  return (
    <div className="agent-control-funnel-row">
      <div className="agent-control-funnel-labels">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="agent-control-funnel-track">
        <div className="agent-control-funnel-fill" style={{ width: `${width}%` }} />
      </div>
      <div className="agent-control-funnel-helper">{helper}</div>
    </div>
  );
}

export default function AgentControlCenterPage({ onNavigate }) {
  const { user, token } = useAuth();
  const [period, setPeriod] = useState("30d");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!user?.tenantId || !token) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      setData(null);
      try {
        const response = await fetchAgentControlCenter(user.tenantId, token, period);
        if (!cancelled) {
          setData(response);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load the agent control center.");
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
  }, [user?.tenantId, token, period, reloadKey]);

  if (loading && !data) {
    return <SkeletonLoader />;
  }

  if (error && !data) {
    return (
      <div className="agent-control-page">
        <div className="agent-control-card agent-control-empty">
          <h1>Agent Control</h1>
          <p>{error}</p>
          <button className="btn-primary" onClick={() => setReloadKey((current) => current + 1)}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  const summary = data?.summary || {};
  const scorecards = data?.scorecards || [];
  const recoveryQueue = data?.recovery_queue || [];
  const roi = data?.roi || {};
  const maxFunnelValue = Math.max(
    roi.conversations || 0,
    roi.assisted || 0,
    roi.leads_captured || 0,
    roi.appointments_booked || 0,
    1,
  );

  return (
    <div className="agent-control-page">
      <style>{`
        .agent-control-page {
          display: flex;
          flex-direction: column;
          gap: 24px;
          color: var(--text-primary);
        }
        .agent-control-hero {
          display: flex;
          justify-content: space-between;
          gap: 20px;
          align-items: flex-start;
          padding: 28px;
          border-radius: 20px;
          background:
            radial-gradient(circle at top right, rgba(34, 211, 238, 0.18), transparent 34%),
            linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(17, 24, 39, 0.96));
          border: 1px solid rgba(148, 163, 184, 0.12);
          box-shadow: 0 16px 40px rgba(2, 6, 23, 0.28);
        }
        .agent-control-hero h1 {
          margin: 0 0 10px;
          font-size: 2rem;
          line-height: 1.1;
        }
        .agent-control-hero p {
          margin: 0;
          color: var(--text-secondary);
          line-height: 1.6;
          max-width: 760px;
        }
        .agent-control-periods {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          justify-content: flex-end;
        }
        .agent-control-period {
          border: 1px solid rgba(148, 163, 184, 0.18);
          background: rgba(15, 23, 42, 0.55);
          color: var(--text-secondary);
          border-radius: 999px;
          padding: 10px 14px;
          cursor: pointer;
          transition: all 0.18s ease;
        }
        .agent-control-period.active {
          background: var(--accent-dim);
          color: var(--accent);
          border-color: rgba(34, 211, 238, 0.28);
        }
        .agent-control-section-grid {
          display: grid;
          grid-template-columns: repeat(12, minmax(0, 1fr));
          gap: 20px;
        }
        .agent-control-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 18px;
          padding: 22px;
          box-shadow: 0 10px 30px rgba(2, 6, 23, 0.16);
        }
        .agent-control-summary-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 16px;
        }
        .agent-control-summary-card {
          min-height: 132px;
        }
        .agent-control-summary-label {
          color: var(--text-secondary);
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 14px;
        }
        .agent-control-summary-value {
          font-size: 2rem;
          font-weight: 700;
          line-height: 1;
          margin-bottom: 10px;
        }
        .agent-control-summary-hint {
          color: var(--text-muted);
          line-height: 1.5;
          font-size: 0.92rem;
        }
        .agent-control-panel {
          display: flex;
          flex-direction: column;
          gap: 16px;
          min-height: 100%;
        }
        .agent-control-panel-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
        }
        .agent-control-panel-title {
          margin: 0;
          font-size: 1.12rem;
        }
        .agent-control-panel-subtitle {
          margin: 6px 0 0;
          color: var(--text-secondary);
          line-height: 1.5;
        }
        .agent-control-list {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .agent-control-item {
          border: 1px solid rgba(148, 163, 184, 0.12);
          background: rgba(15, 23, 42, 0.32);
          border-radius: 16px;
          padding: 18px;
        }
        .agent-control-item-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 12px;
        }
        .agent-control-item-title {
          margin: 0;
          font-size: 1rem;
        }
        .agent-control-item-meta {
          margin-top: 6px;
          color: var(--text-muted);
          font-size: 0.9rem;
        }
        .agent-control-badges {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          justify-content: flex-end;
        }
        .agent-control-badge {
          display: inline-flex;
          align-items: center;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 0.78rem;
          font-weight: 600;
          white-space: nowrap;
        }
        .agent-control-score {
          margin: 12px 0 6px;
        }
        .agent-control-score-labels {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.9rem;
          margin-bottom: 8px;
        }
        .agent-control-score-track {
          height: 10px;
          border-radius: 999px;
          background: rgba(148, 163, 184, 0.14);
          overflow: hidden;
        }
        .agent-control-score-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--accent), rgba(34, 197, 94, 0.95));
        }
        .agent-control-chip-list {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin: 12px 0;
        }
        .agent-control-chip {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(148, 163, 184, 0.1);
          color: var(--text-secondary);
          font-size: 0.8rem;
        }
        .agent-control-copy {
          color: var(--text-secondary);
          line-height: 1.6;
          margin: 0;
        }
        .agent-control-bullet-list {
          margin: 0;
          padding-left: 18px;
          color: var(--text-secondary);
          line-height: 1.65;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .agent-control-actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 14px;
        }
        .agent-control-btn {
          border: 1px solid rgba(148, 163, 184, 0.16);
          background: transparent;
          color: var(--text-primary);
          border-radius: 12px;
          padding: 10px 14px;
          cursor: pointer;
          font-weight: 600;
        }
        .agent-control-btn.primary {
          background: var(--accent-dim);
          color: var(--accent);
          border-color: rgba(34, 211, 238, 0.26);
        }
        .agent-control-funnel {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .agent-control-funnel-row {
          display: grid;
          grid-template-columns: 140px 1fr 150px;
          gap: 14px;
          align-items: center;
        }
        .agent-control-funnel-labels {
          display: flex;
          flex-direction: column;
          gap: 6px;
          color: var(--text-secondary);
        }
        .agent-control-funnel-track {
          height: 14px;
          border-radius: 999px;
          background: rgba(148, 163, 184, 0.12);
          overflow: hidden;
        }
        .agent-control-funnel-fill {
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, rgba(34, 211, 238, 0.92), rgba(59, 130, 246, 0.92));
        }
        .agent-control-funnel-helper {
          color: var(--text-muted);
          font-size: 0.88rem;
          text-align: right;
        }
        .agent-control-recommendations {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }
        .agent-control-recommendation {
          border: 1px solid rgba(148, 163, 184, 0.12);
          border-radius: 14px;
          padding: 16px;
          background: rgba(15, 23, 42, 0.28);
          color: var(--text-secondary);
          line-height: 1.6;
        }
        .agent-control-empty {
          text-align: center;
          color: var(--text-secondary);
          line-height: 1.6;
        }
        @media (max-width: 1180px) {
          .agent-control-section-grid > * {
            grid-column: 1 / -1 !important;
          }
          .agent-control-summary-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .agent-control-funnel-row {
            grid-template-columns: 1fr;
          }
          .agent-control-funnel-helper {
            text-align: left;
          }
        }
        @media (max-width: 920px) {
          .agent-control-hero {
            flex-direction: column;
          }
          .agent-control-periods {
            justify-content: flex-start;
          }
          .agent-control-recommendations {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .agent-control-summary-grid {
            grid-template-columns: 1fr;
          }
          .agent-control-item-header {
            flex-direction: column;
          }
          .agent-control-badges {
            justify-content: flex-start;
          }
        }
      `}</style>

      <section className="agent-control-hero">
        <div>
          <h1>Agent Control</h1>
          <p>
            Review how the assistant is performing across conversations, which customer
            threads need manual recovery, and how much pipeline or revenue is tied to
            recent interactions.
          </p>
        </div>
        <div className="agent-control-periods">
          {PERIODS.map((option) => (
            <button
              key={option.value}
              className={`agent-control-period${period === option.value ? " active" : ""}`}
              onClick={() => setPeriod(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="agent-control-summary-grid">
        <SummaryCard
          label="Avg QA score"
          value={summary.avg_qa_score || 0}
          hint="Heuristic quality score across coverage, capture, booking, and ownership."
        />
        <SummaryCard
          label="Lead capture rate"
          value={formatPercent(summary.lead_capture_rate)}
          hint="Share of conversations that turned into a known lead record."
        />
        <SummaryCard
          label="Booking rate"
          value={formatPercent(summary.booking_rate)}
          hint="How often captured leads moved forward into appointments."
        />
        <SummaryCard
          label="Recovery queue"
          value={summary.active_recovery_queue || 0}
          hint="Conversations where the assistant or team still has a chance to recover intent."
        />
        <SummaryCard
          label="At-risk pipeline"
          value={formatMoney(summary.at_risk_pipeline_value)}
          hint="Potential value sitting in unanswered, stalled, or unbooked conversations."
        />
      </section>

      <section className="agent-control-section-grid">
        <div className="agent-control-card agent-control-panel" style={{ gridColumn: "span 7" }}>
          <div className="agent-control-panel-header">
            <div>
              <h2 className="agent-control-panel-title">QA Scorecards</h2>
              <p className="agent-control-panel-subtitle">
                Recent conversation scorecards show what the assistant handled well and
                where a flow, prompt, or human handoff should improve.
              </p>
            </div>
            <div className="agent-control-badges">
              <Badge meta={STATUS_META.strong} text={`${summary.strong_sessions || 0} strong`} />
              <Badge meta={STATUS_META.watch} text={`${summary.watch_sessions || 0} watch`} />
              <Badge meta={STATUS_META.at_risk} text={`${summary.at_risk_sessions || 0} at risk`} />
            </div>
          </div>

          {scorecards.length === 0 ? (
            <div className="agent-control-empty">
              No recent scorecards yet. Once conversations arrive, this panel will score
              quality and recommend the next play.
            </div>
          ) : (
            <div className="agent-control-list">
              {scorecards.map((card) => {
                const statusMeta = STATUS_META[card.qa_status] || STATUS_META.watch;
                return (
                  <article key={card.session_id} className="agent-control-item">
                    <div className="agent-control-item-header">
                      <div>
                        <h3 className="agent-control-item-title">{card.lead_name || "Visitor"}</h3>
                        <div className="agent-control-item-meta">
                          {card.channel || "widget"} • {card.message_count} messages • last active {formatDate(card.last_message_at)}
                          {card.assigned_to_name ? ` • owner ${card.assigned_to_name}` : ""}
                        </div>
                      </div>
                      <div className="agent-control-badges">
                        <Badge meta={statusMeta} text={statusMeta.label} />
                        <Badge meta={RESOLUTION_META[card.resolution_status] || STATUS_META.watch} text={card.resolution_status.replace(/_/g, " ")} />
                      </div>
                    </div>

                    <div className="agent-control-score">
                      <div className="agent-control-score-labels">
                        <span>QA score</span>
                        <strong>{card.qa_score}/100</strong>
                      </div>
                      <div className="agent-control-score-track">
                        <div className="agent-control-score-fill" style={{ width: `${card.qa_score}%` }} />
                      </div>
                    </div>

                    <div className="agent-control-chip-list">
                      {card.intent_signals.map((signal) => (
                        <span key={signal} className="agent-control-chip">{signal}</span>
                      ))}
                      <span className="agent-control-chip">first reply {formatSeconds(card.first_response_seconds)}</span>
                      {card.pipeline_value > 0 && (
                        <span className="agent-control-chip">pipeline {formatMoney(card.pipeline_value)}</span>
                      )}
                      {card.revenue_won > 0 && (
                        <span className="agent-control-chip">won {formatMoney(card.revenue_won)}</span>
                      )}
                    </div>

                    <p className="agent-control-copy">{card.preview || "No transcript preview available."}</p>

                    {card.strengths?.length > 0 && (
                      <ul className="agent-control-bullet-list">
                        {card.strengths.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}
                    {card.risks?.length > 0 && (
                      <ul className="agent-control-bullet-list">
                        {card.risks.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    )}

                    <p className="agent-control-copy" style={{ marginTop: 12 }}>
                      <strong>Next play:</strong> {card.recommended_action}
                    </p>

                    <div className="agent-control-actions">
                      <button
                        className="agent-control-btn primary"
                        onClick={() => onNavigate?.("conversations", { sessionId: card.session_id })}
                      >
                        Open conversation
                      </button>
                      <button
                        className="agent-control-btn"
                        onClick={() => onNavigate?.("chat_flows")}
                      >
                        Review chat flows
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="agent-control-card agent-control-panel" style={{ gridColumn: "span 5" }}>
          <div className="agent-control-panel-header">
            <div>
              <h2 className="agent-control-panel-title">Recovery Queue</h2>
              <p className="agent-control-panel-subtitle">
                These are the conversations most likely to recover if someone responds,
                quotes, or books quickly.
              </p>
            </div>
          </div>

          {recoveryQueue.length === 0 ? (
            <div className="agent-control-empty">
              No active recovery items right now. That usually means recent threads were
              answered, captured, or already moved into an outcome.
            </div>
          ) : (
            <div className="agent-control-list">
              {recoveryQueue.map((item) => {
                const urgencyMeta = URGENCY_META[item.urgency] || URGENCY_META.medium;
                return (
                  <article key={item.session_id} className="agent-control-item">
                    <div className="agent-control-item-header">
                      <div>
                        <h3 className="agent-control-item-title">{item.lead_name || "Visitor"}</h3>
                        <div className="agent-control-item-meta">
                          {item.channel || "widget"} • last touch {formatDate(item.last_activity_at)}
                          {item.assigned_to_name ? ` • owner ${item.assigned_to_name}` : " • unassigned"}
                        </div>
                      </div>
                      <div className="agent-control-badges">
                        <Badge meta={urgencyMeta} text={urgencyMeta.label} />
                      </div>
                    </div>

                    <p className="agent-control-copy"><strong>{item.reason}</strong></p>
                    <p className="agent-control-copy">{item.last_customer_message || "No customer preview available."}</p>
                    <p className="agent-control-copy">
                      <strong>Suggested play:</strong> {item.suggested_playbook}
                    </p>

                    <div className="agent-control-chip-list">
                      <span className="agent-control-chip">risk {item.risk_score}</span>
                      {item.estimated_value > 0 && (
                        <span className="agent-control-chip">est. value {formatMoney(item.estimated_value)}</span>
                      )}
                    </div>

                    <div className="agent-control-actions">
                      <button
                        className="agent-control-btn primary"
                        onClick={() => onNavigate?.("conversations", { sessionId: item.session_id })}
                      >
                        Recover now
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section className="agent-control-section-grid">
        <div className="agent-control-card agent-control-panel" style={{ gridColumn: "span 7" }}>
          <div className="agent-control-panel-header">
            <div>
              <h2 className="agent-control-panel-title">Closed-loop ROI</h2>
              <p className="agent-control-panel-subtitle">
                This ties conversations to lead capture, appointments, and revenue so the
                assistant can be managed like an operator, not just a chat widget.
              </p>
            </div>
          </div>

          <div className="agent-control-funnel">
            <FunnelBar label="Conversations" value={roi.conversations || 0} maxValue={maxFunnelValue} helper="All recent threads" />
            <FunnelBar label="Assisted" value={roi.assisted || 0} maxValue={maxFunnelValue} helper={formatPercent(roi.capture_rate || 0)} />
            <FunnelBar label="Leads" value={roi.leads_captured || 0} maxValue={maxFunnelValue} helper={`${formatPercent(roi.capture_rate || 0)} capture`} />
            <FunnelBar label="Booked" value={roi.appointments_booked || 0} maxValue={maxFunnelValue} helper={`${formatPercent(roi.booking_rate || 0)} booking`} />
            <FunnelBar label="Won" value={roi.deals_won || 0} maxValue={maxFunnelValue} helper={`${formatPercent(roi.win_rate || 0)} win`} />
          </div>

          <div className="agent-control-summary-grid" style={{ marginTop: 18 }}>
            <SummaryCard label="Won revenue" value={formatMoney(roi.revenue_won)} hint="Paid invoices attached to recent assistant-led conversations." />
            <SummaryCard label="Pipeline value" value={formatMoney(roi.pipeline_value)} hint="Deal value currently associated with captured leads." />
            <SummaryCard label="At-risk value" value={formatMoney(roi.at_risk_pipeline_value)} hint="Pipeline sitting inside the recovery queue right now." />
            <SummaryCard label="Avg first reply" value={formatSeconds(summary.avg_first_response_seconds)} hint="How quickly the assistant answered after the first customer message." />
            <SummaryCard label="Resolved rate" value={formatPercent(summary.resolved_rate)} hint="Sessions that moved into capture, booking, or won outcomes." />
          </div>
        </div>

        <div className="agent-control-card agent-control-panel" style={{ gridColumn: "span 5" }}>
          <div className="agent-control-panel-header">
            <div>
              <h2 className="agent-control-panel-title">Recommended Next Moves</h2>
              <p className="agent-control-panel-subtitle">
                These recommendations are generated from current recovery pressure, capture
                gaps, and booking bottlenecks in the selected period.
              </p>
            </div>
          </div>

          <div className="agent-control-recommendations">
            {(data?.recommendations || []).map((item) => (
              <div key={item} className="agent-control-recommendation">{item}</div>
            ))}
          </div>

          <div className="agent-control-actions">
            <button className="agent-control-btn primary" onClick={() => onNavigate?.("automations")}>
              Tune automations
            </button>
            <button className="agent-control-btn" onClick={() => onNavigate?.("analytics")}>
              Open analytics
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
