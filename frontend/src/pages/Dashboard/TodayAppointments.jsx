import { useState, useEffect } from "react";
import { fetchAppointments } from "../../utils/api/appointments";
import { fetchAppointmentBrief } from "../../utils/api/insights";

function formatTime(isoStr, tz) {
  try {
    const opts = { hour: "numeric", minute: "2-digit" };
    if (tz) opts.timeZone = tz;
    return new Date(isoStr).toLocaleTimeString([], opts);
  } catch {
    return new Date(isoStr).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
}

export default function TodayAppointments({ tenantId, token, onNavigate }) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bizTz, setBizTz] = useState(null);
  // briefs: { [appointmentId]: { status: "loading" | "ready" | "error", text } }
  const [briefs, setBriefs] = useState({});

  useEffect(() => {
    if (!tenantId || !token) return;
    const today = new Date().toISOString().split("T")[0];
    const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
    fetchAppointments(tenantId, token, { startDate: today, endDate: tomorrow, status: "confirmed" })
      .then(res => { setAppointments(res.appointments || []); if (res.timezone) setBizTz(res.timezone); })
      .catch((err) => { console.warn("Appointments fetch failed:", err?.message); setAppointments([]); })
      .finally(() => setLoading(false));
  }, [tenantId, token]);

  const loadBrief = async (appointmentId) => {
    const current = briefs[appointmentId];
    if (current?.status === "loading") return;
    if (current?.status === "ready") {
      // second click toggles the brief closed
      setBriefs(prev => { const next = { ...prev }; delete next[appointmentId]; return next; });
      return;
    }
    setBriefs(prev => ({ ...prev, [appointmentId]: { status: "loading" } }));
    try {
      const res = await fetchAppointmentBrief(tenantId, appointmentId, token);
      setBriefs(prev => ({ ...prev, [appointmentId]: { status: "ready", text: res.brief } }));
    } catch (err) {
      console.warn("Brief fetch failed:", err?.message);
      setBriefs(prev => ({ ...prev, [appointmentId]: { status: "error" } }));
    }
  };

  const upcoming = appointments.filter(a => new Date(a.start_time) >= new Date()).slice(0, 5);

  return (
    <div className="today-appts-card">
      <div className="today-appts-header">
        <h3>Today's Appointments</h3>
        <span className="today-appts-count">{appointments.length}</span>
      </div>
      {loading ? (
        <p className="today-appts-empty">Loading...</p>
      ) : upcoming.length === 0 ? (
        <p className="today-appts-empty">No upcoming appointments today</p>
      ) : (
        <div className="today-appts-list">
          {upcoming.map(a => (
            <div key={a.id} className="today-appt-item" style={{ flexWrap: "wrap" }}>
              <div className="today-appt-time">{formatTime(a.start_time, bizTz)}</div>
              <div className="today-appt-info">
                <div className="today-appt-name">{a.customer_name}</div>
                <div className="today-appt-email">{a.customer_email}</div>
              </div>
              <button
                onClick={() => loadBrief(a.id)}
                title="Walk in prepared: who they are, what they asked about, talking points"
                style={{
                  marginLeft: "auto",
                  padding: "2px 8px",
                  fontSize: "0.7rem",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: "var(--bg-primary)",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                }}
              >
                {briefs[a.id]?.status === "loading" ? "Prepping..." : briefs[a.id]?.status === "ready" ? "Hide brief" : "Brief me"}
              </button>
              {briefs[a.id]?.status === "ready" && (
                <div
                  style={{
                    flexBasis: "100%",
                    marginTop: 6,
                    padding: "8px 10px",
                    borderRadius: 8,
                    background: "var(--bg-primary)",
                    border: "1px solid var(--border)",
                    fontSize: "0.75rem",
                    color: "var(--text-primary)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {briefs[a.id].text}
                </div>
              )}
              {briefs[a.id]?.status === "error" && (
                <div style={{ flexBasis: "100%", marginTop: 4, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  Couldn't build a brief for this one — try again in a moment.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <button className="today-appts-viewall" onClick={() => onNavigate("calendar")}>View Calendar &rarr;</button>
    </div>
  );
}
