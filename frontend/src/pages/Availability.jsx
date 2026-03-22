import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { fetchAvailability, updateAvailability } from "../utils/api/appointments";
import { fetchGoogleCalendarStatus } from "../utils/api/integrations";

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const DAY_LABELS = { monday: "Monday", tuesday: "Tuesday", wednesday: "Wednesday", thursday: "Thursday", friday: "Friday", saturday: "Saturday", sunday: "Sunday" };

const TIMEZONES = [
  "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
  "America/Phoenix", "America/Anchorage", "Pacific/Honolulu", "America/Toronto",
  "Europe/London", "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney",
];

const DURATIONS = [15, 30, 45, 60];
const BUFFERS = [0, 5, 10, 15, 30];

export default function Availability({ onNavigate }) {
  const { user, token } = useAuth();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [gcalConnected, setGcalConnected] = useState(false);

  useEffect(() => {
    if (!user?.tenantId) return;
    fetchGoogleCalendarStatus(user.tenantId, token)
      .then(s => setGcalConnected(s.connected))
      .catch((err) => {
        console.warn("Failed to check Google Calendar status:", err.message || err);
        // Non-critical: gcalConnected defaults to false, UI will show "Not connected"
      });
  }, [user?.tenantId, token]);

  const loadConfig = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const res = await fetchAvailability(user.tenantId, token);
      setConfig(res);
    } catch (err) {
      console.warn("Failed to load availability config, using defaults:", err.message || err);
      setError("Could not load saved settings. Showing defaults.");
      setConfig({
        timezone: "America/New_York",
        hours: Object.fromEntries(DAYS.map(d => [d, { enabled: d !== "saturday" && d !== "sunday", start: "09:00", end: "17:00" }])),
        slot_duration_minutes: 30,
        buffer_minutes: 0,
        max_advance_days: 30,
      });
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  const handleDayToggle = (day) => {
    setConfig(c => ({
      ...c,
      hours: { ...c.hours, [day]: { ...c.hours[day], enabled: !c.hours[day].enabled } },
    }));
  };

  const handleTimeChange = (day, field, value) => {
    setConfig(c => ({
      ...c,
      hours: { ...c.hours, [day]: { ...c.hours[day], [field]: value } },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const res = await updateAvailability(user.tenantId, token, config);
      setConfig(res);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.body?.detail || err.message || "Failed to save availability settings.");
    }
    finally { setSaving(false); }
  };

  if (loading || !config) return <div className="fade-in"><div className="page-header"><h1>Availability</h1></div><p style={{ padding: 24, color: "var(--text-secondary)" }}>Loading...</p></div>;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>Availability Settings</h1>
        <p>Configure when customers can book appointments</p>
      </div>

      <div className="availability-container">
        <div className="availability-section">
          <h3>Timezone</h3>
          <select className="avail-select" value={config.timezone} onChange={e => setConfig(c => ({ ...c, timezone: e.target.value }))}>
            {TIMEZONES.map(tz => <option key={tz} value={tz}>{tz.replace(/_/g, " ")}</option>)}
          </select>
        </div>

        <div className="availability-section">
          <h3>Business Hours</h3>
          <div className="avail-days">
            {DAYS.map(day => (
              <div key={day} className="avail-day-row">
                <label className="avail-day-toggle">
                  <input type="checkbox" checked={config.hours[day]?.enabled ?? false} onChange={() => handleDayToggle(day)} />
                  <span className="avail-day-label">{DAY_LABELS[day]}</span>
                </label>
                {config.hours[day]?.enabled && (
                  <div className="avail-day-times">
                    <input type="time" value={config.hours[day]?.start || "09:00"} onChange={e => handleTimeChange(day, "start", e.target.value)} className="avail-time-input" />
                    <span className="avail-time-sep">to</span>
                    <input type="time" value={config.hours[day]?.end || "17:00"} onChange={e => handleTimeChange(day, "end", e.target.value)} className="avail-time-input" />
                  </div>
                )}
                {!config.hours[day]?.enabled && <span className="avail-closed">Closed</span>}
              </div>
            ))}
          </div>
        </div>

        <div className="availability-section">
          <h3>Slot Settings</h3>
          <div className="avail-settings-grid">
            <div className="avail-setting">
              <label>Appointment Duration</label>
              <select className="avail-select" value={config.slot_duration_minutes} onChange={e => setConfig(c => ({ ...c, slot_duration_minutes: parseInt(e.target.value) }))}>
                {DURATIONS.map(d => <option key={d} value={d}>{d} minutes</option>)}
              </select>
            </div>
            <div className="avail-setting">
              <label>Buffer Between Appointments</label>
              <select className="avail-select" value={config.buffer_minutes} onChange={e => setConfig(c => ({ ...c, buffer_minutes: parseInt(e.target.value) }))}>
                {BUFFERS.map(b => <option key={b} value={b}>{b === 0 ? "None" : `${b} minutes`}</option>)}
              </select>
            </div>
            <div className="avail-setting">
              <label>Max Advance Booking (days)</label>
              <input type="number" className="avail-input" min={1} max={90} value={config.max_advance_days} onChange={e => setConfig(c => ({ ...c, max_advance_days: parseInt(e.target.value) || 30 }))} />
            </div>
          </div>
        </div>

        <div className="availability-section">
          <h3>Google Calendar</h3>
          {gcalConnected ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--green)" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--green)", display: "inline-block" }} />
              Connected — availability checks against your real calendar
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              <span style={{ marginRight: 8 }}>Not connected.</span>
              <button className="btn-secondary" style={{ fontSize: 12, padding: "4px 10px" }} onClick={() => onNavigate("integrations")}>Connect Google Calendar</button>
            </div>
          )}
        </div>

        {error && <div className="error-banner" style={{ marginBottom: "1rem" }}>{error}</div>}

        <div className="availability-actions">
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
          </button>
          <button className="btn-secondary" onClick={() => onNavigate("calendar")}>View Calendar</button>
        </div>
      </div>
    </div>
  );
}
