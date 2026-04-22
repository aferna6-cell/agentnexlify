/**
 * AutomationActivityCard — Phase 1 dashboard card.
 * Shows last 5 automation events (missed call text-backs, etc.).
 * Dark theme. Masked phone numbers. Empty state included.
 */
import { useState, useEffect } from "react";
import { getActivity } from "../../utils/api/automations";

const ACCENT = "#00BFFF";
const BG = "rgba(11,14,19,0.92)";
const BORDER = "rgba(255,255,255,0.08)";
const TEXT_MUTED = "rgba(255,255,255,0.5)";

const EVENT_LABELS = {
  missed_call_textback: "Missed call — text-back sent",
  sms_conversation: "SMS conversation",
  appointment_booked: "Appointment booked",
};

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

export default function AutomationActivityCard({
  tenantId,
  token,
  onNavigate,
}) {
  const [events, setEvents] = useState([]);
  const [totals, setTotals] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId || !token) return;
    setLoading(true);
    getActivity({ tenantId, token, limit: 5 })
      .then((data) => {
        setEvents(data?.events || []);
        setTotals(data?.totals || null);
      })
      .catch(() => {
        setEvents([]);
        setTotals(null);
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
          marginBottom: 14,
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
        {onNavigate && events.length > 0 && (
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

      {/* Totals headline */}
      {totals && (
        <div style={{ fontSize: "0.82rem", marginBottom: 12, lineHeight: 1.4 }}>
          <span style={{ color: "#4caf50", fontWeight: 600 }}>
            ${(totals.dollars_this_month || 0).toFixed(0)} recovered
          </span>
          <span style={{ color: TEXT_MUTED }}> this month · </span>
          <span style={{ color: ACCENT, fontWeight: 600 }}>
            {(totals.hours_this_week || 0).toFixed(1)} hrs saved
          </span>
          <span style={{ color: TEXT_MUTED }}> this week</span>
        </div>
      )}

      {/* Body */}
      {loading ? (
        <div style={{ color: TEXT_MUTED, fontSize: "0.85rem" }}>Loading...</div>
      ) : events.length === 0 ? (
        <div
          style={{
            color: TEXT_MUTED,
            fontSize: "0.87rem",
            textAlign: "center",
            padding: "16px 0",
          }}
        >
          No automations yet — your AI employee is ready.
        </div>
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
