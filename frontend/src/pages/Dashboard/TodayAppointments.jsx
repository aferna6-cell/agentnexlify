import { useState, useEffect } from "react";
import { fetchAppointments } from "../../utils/api/appointments";

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

  useEffect(() => {
    if (!tenantId || !token) return;
    const today = new Date().toISOString().split("T")[0];
    const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
    fetchAppointments(tenantId, token, { startDate: today, endDate: tomorrow, status: "confirmed" })
      .then(res => { setAppointments(res.appointments || []); if (res.timezone) setBizTz(res.timezone); })
      .catch((err) => { console.warn("Appointments fetch failed:", err?.message); setAppointments([]); })
      .finally(() => setLoading(false));
  }, [tenantId, token]);

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
            <div key={a.id} className="today-appt-item">
              <div className="today-appt-time">{formatTime(a.start_time, bizTz)}</div>
              <div className="today-appt-info">
                <div className="today-appt-name">{a.customer_name}</div>
                <div className="today-appt-email">{a.customer_email}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      <button className="today-appts-viewall" onClick={() => onNavigate("calendar")}>View Calendar &rarr;</button>
    </div>
  );
}
