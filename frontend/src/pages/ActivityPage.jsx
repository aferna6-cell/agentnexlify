import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { getActivity } from "../utils/api/automations";

const ACCENT = "#00BFFF";
const BG = "rgba(11,14,19,0.92)";
const BG_CARD = "rgba(255,255,255,0.04)";
const BORDER = "rgba(255,255,255,0.08)";
const TEXT_MUTED = "rgba(255,255,255,0.5)";

const EVENT_LABELS = {
  missed_call_textback: "Missed call — text-back sent",
  appointment_booked: "Appointment booked",
  sms_conversation: "SMS conversation",
  noshow_recovery_sent: "No-show recovery sent",
};

const FILTERS = [
  { key: "", label: "All" },
  { key: "missed_call_textback", label: "Missed Call" },
  { key: "appointment_booked", label: "Appointment" },
];

function relativeTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
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
        marginTop: 2,
      }}
    />
  );
}

function EventCard({ event }) {
  const label =
    EVENT_LABELS[event.activity_type] ||
    event.description ||
    event.activity_type;
  const meta = event.metadata || {};
  const phone = meta.caller || meta.from_phone || meta.phone || null;
  const smsStatus = meta.status || null;

  return (
    <div
      style={{
        background: BG_CARD,
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "12px 16px",
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        marginBottom: 8,
      }}
    >
      <StatusDot status={smsStatus} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: "#e2e8f0", fontSize: "0.9rem", fontWeight: 500 }}>
          {label}
        </div>
        {phone && (
          <div style={{ color: TEXT_MUTED, fontSize: "0.8rem", marginTop: 2 }}>
            {phone}
          </div>
        )}
      </div>
      <div
        style={{
          color: TEXT_MUTED,
          fontSize: "0.78rem",
          flexShrink: 0,
          whiteSpace: "nowrap",
        }}
      >
        {event.created_at ? relativeTime(event.created_at) : ""}
      </div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <div
      style={{
        background: BG_CARD,
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "12px 16px",
        marginBottom: 8,
        height: 48,
        animation: "pulse 1.5s ease-in-out infinite",
      }}
    />
  );
}

export default function ActivityPage() {
  const { user, session } = useAuth();
  const tenantId = user?.tenant_id || user?.id;
  const token = session?.access_token;

  const [events, setEvents] = useState([]);
  const [totals, setTotals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  const load = useCallback(() => {
    if (!tenantId || !token) return;
    setLoading(true);
    getActivity({ tenantId, token, limit: 50, type: filter || undefined })
      .then((data) => {
        setEvents(data?.events || []);
        setTotals(data?.totals || null);
      })
      .catch(() => {
        setEvents([]);
        setTotals(null);
      })
      .finally(() => setLoading(false));
  }, [tenantId, token, filter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div style={{ maxWidth: 820, margin: "0 auto", padding: "24px 16px" }}>
      {/* Header */}
      <h1
        style={{
          color: "#fff",
          fontSize: "1.4rem",
          fontWeight: 700,
          margin: "0 0 4px",
        }}
      >
        AI Employee Activity
      </h1>

      {/* Totals headline */}
      {totals && (
        <div
          style={{ color: TEXT_MUTED, fontSize: "0.88rem", marginBottom: 20 }}
        >
          <span style={{ color: "#4caf50", fontWeight: 600 }}>
            ${(totals.dollars_this_month || 0).toFixed(0)} recovered this month
          </span>
          {" · "}
          <span style={{ color: ACCENT, fontWeight: 600 }}>
            {(totals.hours_this_week || 0).toFixed(1)} hrs saved this week
          </span>
        </div>
      )}

      {/* Filter chips */}
      <div
        style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}
      >
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: "6px 16px",
              borderRadius: 20,
              border: `1px solid ${filter === f.key ? ACCENT : BORDER}`,
              background:
                filter === f.key ? `rgba(0,191,255,0.12)` : "transparent",
              color: filter === f.key ? ACCENT : TEXT_MUTED,
              cursor: "pointer",
              fontSize: "0.84rem",
              fontWeight: filter === f.key ? 600 : 400,
              transition: "all 0.15s",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Event list */}
      <div
        style={{
          background: BG,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: 16,
        }}
      >
        {loading ? (
          <>
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
          </>
        ) : events.length === 0 ? (
          <div
            style={{
              color: TEXT_MUTED,
              fontSize: "0.9rem",
              textAlign: "center",
              padding: "32px 0",
            }}
          >
            Your AI employee hasn&apos;t fired yet
          </div>
        ) : (
          events.map((e) => <EventCard key={e.id} event={e} />)
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
