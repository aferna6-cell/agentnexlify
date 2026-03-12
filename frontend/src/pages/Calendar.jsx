import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchAppointments, updateAppointment, cancelAppointment } from "../utils/api";

const STATUS_COLORS = {
  confirmed: { bg: "var(--accent-dim)", border: "var(--accent)", text: "var(--accent)" },
  cancelled: { bg: "var(--hover-overlay)", border: "var(--text-muted)", text: "var(--text-muted)" },
  completed: { bg: "var(--green-dim)", border: "var(--green)", text: "var(--green)" },
  no_show: { bg: "var(--yellow-dim)", border: "var(--yellow)", text: "var(--yellow)" },
};

const HOURS = Array.from({ length: 14 }, (_, i) => i + 7); // 7am - 8pm

function formatTime(isoStr, tz) {
  try {
    return new Date(isoStr).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: tz });
  } catch {
    return new Date(isoStr).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
}

function formatDate(d) {
  return d.toISOString().split("T")[0];
}

function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function getWeekStart(d) {
  const r = new Date(d);
  r.setDate(r.getDate() - r.getDay());
  return r;
}

function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function Calendar({ onNavigate }) {
  const { user, token } = useAuth();
  const [view, setView] = useState("week");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppt, setSelectedAppt] = useState(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [error, setError] = useState(null);

  const weekStart = useMemo(() => getWeekStart(currentDate), [currentDate]);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  const loadAppointments = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const startDate = view === "week" ? formatDate(weekStart) : formatDate(currentDate);
      const endDate = view === "week" ? formatDate(addDays(weekStart, 7)) : formatDate(addDays(currentDate, 1));
      const res = await fetchAppointments(user.tenantId, token, { startDate, endDate });
      setAppointments(res.appointments || []);
    } catch {
      setAppointments([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, view, weekStart, currentDate]);

  useEffect(() => { loadAppointments(); }, [loadAppointments]);

  const handlePrev = () => setCurrentDate(d => addDays(d, view === "week" ? -7 : -1));
  const handleNext = () => setCurrentDate(d => addDays(d, view === "week" ? 7 : 1));
  const handleToday = () => setCurrentDate(new Date());

  const openEdit = (appt) => {
    setSelectedAppt(appt);
    setEditStatus(appt.status);
    setEditNotes(appt.notes || "");
    setError(null);
  };

  const handleSave = async () => {
    if (!selectedAppt) return;
    const updates = {};
    if (editStatus !== selectedAppt.status) updates.status = editStatus;
    if (editNotes !== (selectedAppt.notes || "")) updates.notes = editNotes;
    if (Object.keys(updates).length === 0) { setSelectedAppt(null); return; }
    try {
      await updateAppointment(user.tenantId, token, selectedAppt.id, updates);
      setError(null);
      setSelectedAppt(null);
      loadAppointments();
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to save appointment changes.");
    }
  };

  const handleCancel = async () => {
    if (!selectedAppt) return;
    try {
      await cancelAppointment(user.tenantId, token, selectedAppt.id);
      setError(null);
      setSelectedAppt(null);
      loadAppointments();
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to cancel appointment.");
    }
  };

  const getApptPosition = (appt) => {
    const start = new Date(appt.start_time);
    const end = new Date(appt.end_time);
    const startMinutes = start.getHours() * 60 + start.getMinutes();
    const endMinutes = end.getHours() * 60 + end.getMinutes();
    const topOffset = startMinutes - HOURS[0] * 60;
    const height = endMinutes - startMinutes;
    return { top: `${(topOffset / 60) * 64}px`, height: `${Math.max((height / 60) * 64, 24)}px` };
  };

  const titleText = view === "week"
    ? `${MONTH_NAMES[weekStart.getMonth()]} ${weekStart.getDate()} - ${MONTH_NAMES[addDays(weekStart, 6).getMonth()]} ${addDays(weekStart, 6).getDate()}, ${weekStart.getFullYear()}`
    : `${DAY_NAMES[currentDate.getDay()]}, ${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Calendar</h1>
        <p>Manage your appointments</p>
      </div>

      <div className="calendar-toolbar">
        <div className="calendar-nav">
          <button className="btn-secondary" onClick={handlePrev}>&larr;</button>
          <button className="btn-secondary" onClick={handleToday}>Today</button>
          <button className="btn-secondary" onClick={handleNext}>&rarr;</button>
          <span className="calendar-title">{titleText}</span>
        </div>
        <div className="calendar-view-toggle">
          <button className={`btn-secondary${view === "week" ? " active" : ""}`} onClick={() => setView("week")}>Week</button>
          <button className={`btn-secondary${view === "day" ? " active" : ""}`} onClick={() => setView("day")}>Day</button>
          <button className="btn-secondary" onClick={() => onNavigate("availability")}>Availability</button>
        </div>
      </div>

      {loading ? (
        <div className="calendar-loading">Loading appointments...</div>
      ) : !loading && appointments.length === 0 ? (
        <div className="empty-card" style={{ textAlign: "center", padding: "3rem 2rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}>📅</div>
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--text-primary)" }}>No appointments yet</h3>
          <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>
            When customers book through your widget, appointments will appear here.
          </p>
          <button className="btn-primary" onClick={() => onNavigate("availability")}>
            Set up availability
          </button>
        </div>
      ) : view === "week" ? (
        <div className="calendar-week">
          <div className="calendar-week-header">
            <div className="calendar-time-gutter"></div>
            {weekDays.map((d, i) => (
              <div key={i} className={`calendar-day-header${isSameDay(d, new Date()) ? " today" : ""}`}
                onClick={() => { setCurrentDate(d); setView("day"); }}>
                <span className="calendar-day-name">{DAY_NAMES[d.getDay()]}</span>
                <span className="calendar-day-num">{d.getDate()}</span>
              </div>
            ))}
          </div>
          <div className="calendar-week-body">
            <div className="calendar-time-gutter">
              {HOURS.map(h => (
                <div key={h} className="calendar-hour-label">
                  {h === 0 ? "12 AM" : h < 12 ? `${h} AM` : h === 12 ? "12 PM" : `${h - 12} PM`}
                </div>
              ))}
            </div>
            {weekDays.map((day, di) => (
              <div key={di} className={`calendar-day-col${isSameDay(day, new Date()) ? " today" : ""}`}>
                {HOURS.map(h => <div key={h} className="calendar-hour-cell"></div>)}
                {appointments
                  .filter(a => isSameDay(new Date(a.start_time), day))
                  .map(a => {
                    const pos = getApptPosition(a);
                    const colors = STATUS_COLORS[a.status] || STATUS_COLORS.confirmed;
                    return (
                      <div key={a.id} className="calendar-appt-block" style={{
                        ...pos, background: colors.bg, borderLeft: `3px solid ${colors.border}`, color: colors.text,
                      }} onClick={() => openEdit(a)} title={`${a.customer_name} - ${a.status}`}>
                        <div className="calendar-appt-name">{a.customer_name}</div>
                        <div className="calendar-appt-time">{formatTime(a.start_time)}</div>
                      </div>
                    );
                  })}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="calendar-day-view">
          <div className="calendar-day-timeline">
            {HOURS.map(h => (
              <div key={h} className="calendar-day-hour-row">
                <div className="calendar-hour-label">
                  {h === 0 ? "12 AM" : h < 12 ? `${h} AM` : h === 12 ? "12 PM" : `${h - 12} PM`}
                </div>
                <div className="calendar-day-hour-content">
                  {appointments
                    .filter(a => {
                      const s = new Date(a.start_time);
                      return isSameDay(s, currentDate) && s.getHours() === h;
                    })
                    .map(a => {
                      const colors = STATUS_COLORS[a.status] || STATUS_COLORS.confirmed;
                      return (
                        <div key={a.id} className="calendar-day-appt-card" style={{
                          background: colors.bg, borderLeft: `3px solid ${colors.border}`,
                        }} onClick={() => openEdit(a)}>
                          <div style={{ color: colors.text, fontWeight: 600 }}>{a.customer_name}</div>
                          <div style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                            {formatTime(a.start_time)} - {formatTime(a.end_time)}
                          </div>
                          {a.customer_email && <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>{a.customer_email}</div>}
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedAppt && (
        <div className="modal-overlay" onClick={() => setSelectedAppt(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3>Edit Appointment</h3>
            {error && <div className="error-banner" style={{ marginBottom: "0.75rem" }}>{error}</div>}
            <div className="modal-field">
              <label>Customer</label>
              <div>{selectedAppt.customer_name} ({selectedAppt.customer_email})</div>
            </div>
            <div className="modal-field">
              <label>Time</label>
              <div>{formatTime(selectedAppt.start_time)} - {formatTime(selectedAppt.end_time)}</div>
            </div>
            <div className="modal-field">
              <label>Status</label>
              <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="modal-select">
                <option value="confirmed">Confirmed</option>
                <option value="completed">Completed</option>
                <option value="no_show">No Show</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div className="modal-field">
              <label>Notes</label>
              <textarea value={editNotes} onChange={e => setEditNotes(e.target.value)} className="modal-textarea" rows={3} />
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={handleSave}>Save</button>
              <button className="btn-danger" onClick={handleCancel}>Cancel Appointment</button>
              <button className="btn-secondary" onClick={() => setSelectedAppt(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
