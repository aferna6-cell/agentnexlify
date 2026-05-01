/**
 * AutomationActivityCard - Phase 1 + Phase 2 dashboard card.
 * Shows dollars recovered (calendar month UTC) + hours saved (ISO week UTC)
 * as a top headline, then last 5 automation events beneath.
 * Dark theme. Masked phone numbers. Empty / loading / error states included.
 */
import { useState, useEffect } from "react";
import { getActivity } from "../../utils/api/automations";

const ACCENT = "#00BFFF";
const BG = "rgba(11,14,19,0.92)";
const BORDER = "rgba(255,255,255,0.08)";
const TEXT_MUTED = "rgba(255,255,255,0.5)";

const EVENT_LABELS = {
  missed_call_textback: "Missed call - text-back sent",
  sms_conversation: "SMS conversation",
  appointment_booked: "Appointment booked",
  email_sequence_sent: "Follow-up email sent",
};

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

function relativeTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/**
 * Format a Decimal-as-string value as USD.
 * Falls back to "$0" when value is null / undefined / "0".
 */
function formatDollars(raw) {
  const n = parseFloat(raw ?? "0");
  if (isNaN(n)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

/**
 * Format a Decimal-as-string value as hours with 1 decimal.
 */
function formatHours(raw) {
  const n = parseFloat(raw ?? "0");
  if (isNaN(n)) return "0.0h";
  return `${n.toFixed(1)}h`;
}

// ----------------------------------------------------------------
// Sub-components
// ----------------------------------------------------------------

function StatusDot({ status }) {
  const color =
    status === "sent" || status === "delivered"
      ? "#4caf50"
      : status === "pending" || status === "queued"
        ? "#ff9800"
        : status === "failed"
          ? "#ef4444"
          : ACCENT;
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
        boxShadow: color === "#4caf50" ? "0 0 5px rgba(76,175,80,0.5)" : "none",
      }}
    />
  );
}

function SkeletonBar({ width = "60%", height = 14 }) {
  return (
    <span
      style={{
        display: "inline-block",
        width,
        height,
        borderRadius: 4,
        background: "rgba(255,255,255,0.08)",
        verticalAlign: "middle",
      }}
    />
  );
}

/**
 * Top headline showing dollars recovered + hours saved + event count.
 * Renders skeleton while loading, zeros on empty, values otherwise.
 */
function TotalsHeadline({ totals, loading, error }) {
  const dollars = totals?.dollars_this_month ?? "0";
  const hours = totals?.hours_this_week ?? "0";
  const count = totals?.events_count ?? 0;

  const statStyle = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flex: 1,
    minWidth: 0,
  };
  const valueStyle = {
    fontSize: "1.35rem",
    fontWeight: 700,
    color: "#fff",
    lineHeight: 1.2,
    letterSpacing: "-0.01em",
  };
  const labelStyle = {
    fontSize: "0.72rem",
    color: TEXT_MUTED,
    marginTop: 3,
    whiteSpace: "nowrap",
  };
  const dividerStyle = {
    width: 1,
    alignSelf: "stretch",
    background: BORDER,
    margin: "0 4px",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "stretch",
        padding: "14px 4px 16px",
        borderBottom: `1px solid ${BORDER}`,
        marginBottom: 14,
        gap: 4,
      }}
    >
      {/* Dollars recovered this month */}
      <div style={statStyle}>
        <div style={valueStyle}>
          {loading ? (
            <SkeletonBar width={70} height={22} />
          ) : error ? (
            <span style={{ color: "#ef4444", fontSize: "0.9rem" }}>—</span>
          ) : (
            formatDollars(dollars)
          )}
        </div>
        <div style={labelStyle}>Recovered this month</div>
      </div>

      <div style={dividerStyle} />

      {/* Hours saved this week */}
      <div style={statStyle}>
        <div style={valueStyle}>
          {loading ? (
            <SkeletonBar width={52} height={22} />
          ) : error ? (
            <span style={{ color: "#ef4444", fontSize: "0.9rem" }}>—</span>
          ) : (
            formatHours(hours)
          )}
        </div>
        <div style={labelStyle}>Saved this week</div>
      </div>

      <div style={dividerStyle} />

      {/* Total events */}
      <div style={statStyle}>
        <div style={valueStyle}>
          {loading ? (
            <SkeletonBar width={36} height={22} />
          ) : error ? (
            <span style={{ color: "#ef4444", fontSize: "0.9rem" }}>—</span>
          ) : (
            count
          )}
        </div>
        <div style={labelStyle}>Actions total</div>
      </div>
    </div>
  );
}

function EventRow({ event }) {
  const label =
    EVENT_LABELS[event.activity_type] ||
    event.description ||
    event.activity_type;
  const meta = event.metadata || {};
  const phone = meta.caller || meta.from_phone || meta.phone || null;
  const time = event.created_at ? relativeTime(event.created_at) : "";
  const smsStatus = meta.status || null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 0",
        borderBottom: `1px solid ${BORDER}`,
      }}
    >
      <StatusDot status={smsStatus} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            color: "#e2e8f0",
            fontSize: "0.87rem",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {label}
          {phone && (
            <span style={{ color: TEXT_MUTED, marginLeft: 6 }}>{phone}</span>
          )}
        </div>
      </div>
      <div
        style={{
          fontSize: "0.75rem",
          color: TEXT_MUTED,
          flexShrink: 0,
          whiteSpace: "nowrap",
        }}
      >
        {time}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------
// Empty state — shown when no activity has been logged yet
// ----------------------------------------------------------------

function EmptyState() {
  return (
    <div
      style={{
        color: TEXT_MUTED,
        fontSize: "0.87rem",
        textAlign: "center",
        padding: "16px 0",
        lineHeight: 1.6,
      }}
    >
      <div style={{ marginBottom: 6 }}>Your AI employee is standing by.</div>
      <div style={{ fontSize: "0.78rem" }}>
        Activity appears here once missed calls or appointments come in.
      </div>
    </div>
  );
}

// ----------------------------------------------------------------
// Loading skeleton for event rows
// ----------------------------------------------------------------

function EventSkeleton() {
  return (
    <div>
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 0",
            borderBottom: `1px solid ${BORDER}`,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1 }}>
            <SkeletonBar width="55%" height={13} />
          </div>
          <SkeletonBar width={32} height={11} />
        </div>
      ))}
    </div>
  );
}

// ----------------------------------------------------------------
// Main export
// ----------------------------------------------------------------

export default function AutomationActivityCard({
  tenantId,
  token,
  onNavigate,
}) {
  const [events, setEvents] = useState([]);
  const [totals, setTotals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!tenantId || !token) return;
    setLoading(true);
    setError(false);
    getActivity({ tenantId, token, limit: 5 })
      .then((data) => {
        setEvents(data?.events || []);
        setTotals(data?.totals ?? null);
      })
      .catch(() => {
        setEvents([]);
        setTotals(null);
        setError(true);
      })
      .finally(() => setLoading(false));
  }, [tenantId, token]);

  return (
    <div
      style={{
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 10,
        padding: "18px 20px",
        marginBottom: 18,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: "0.95rem",
            fontWeight: 700,
            color: "#fff",
            letterSpacing: "0.01em",
          }}
        >
          AI Employee Activity
        </h3>
        {onNavigate && !loading && (
          <button
            onClick={() => onNavigate("activity")}
            style={{
              background: "none",
              border: "none",
              color: ACCENT,
              fontSize: "0.8rem",
              cursor: "pointer",
              padding: 0,
              fontWeight: 600,
            }}
          >
            View all &rarr;
          </button>
        )}
      </div>

      {/* Totals headline — always rendered (zeros / skeleton / error state) */}
      <TotalsHeadline totals={totals} loading={loading} error={error} />

      {/* Event list */}
      {loading ? (
        <EventSkeleton />
      ) : error ? (
        <div
          style={{
            color: "#ef4444",
            fontSize: "0.82rem",
            textAlign: "center",
            padding: "10px 0",
          }}
        >
          Could not load activity. Refresh to retry.
        </div>
      ) : events.length === 0 ? (
        <EmptyState />
      ) : (
        <div>
          {events.map((event) => (
            <EventRow key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
