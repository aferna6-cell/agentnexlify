import { DAYS_OF_WEEK } from "./constants";

export default function HoursStep({
  businessHours,
  setBusinessHours,
  saving,
  saveError,
  onSave,
}) {
  return (
    <div className="onboarding-step-body">
      <p className="onboarding-hint">
        Set your business hours so the AI knows when you're available and can
        inform visitors.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {DAYS_OF_WEEK.map((day) => {
          const cfg = businessHours[day] || {
            enabled: false,
            start: "09:00",
            end: "17:00",
          };
          return (
            <div
              key={day}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "6px 0",
                borderBottom: "1px solid var(--border, #2a2a3e)",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  width: 120,
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  color: cfg.enabled
                    ? "var(--text-primary)"
                    : "var(--text-muted)",
                }}
              >
                <input
                  type="checkbox"
                  checked={cfg.enabled}
                  onChange={(e) =>
                    setBusinessHours((prev) => ({
                      ...prev,
                      [day]: { ...prev[day], enabled: e.target.checked },
                    }))
                  }
                  style={{ width: "auto" }}
                />
                {day.charAt(0).toUpperCase() + day.slice(1)}
              </label>
              {cfg.enabled && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: "0.85rem",
                  }}
                >
                  <input
                    type="time"
                    value={cfg.start}
                    onChange={(e) =>
                      setBusinessHours((prev) => ({
                        ...prev,
                        [day]: { ...prev[day], start: e.target.value },
                      }))
                    }
                    className="onboarding-input"
                    style={{
                      width: 110,
                      padding: "4px 6px",
                      fontSize: "0.82rem",
                    }}
                  />
                  <span style={{ color: "var(--text-muted)" }}>to</span>
                  <input
                    type="time"
                    value={cfg.end}
                    onChange={(e) =>
                      setBusinessHours((prev) => ({
                        ...prev,
                        [day]: { ...prev[day], end: e.target.value },
                      }))
                    }
                    className="onboarding-input"
                    style={{
                      width: 110,
                      padding: "4px 6px",
                      fontSize: "0.82rem",
                    }}
                  />
                </div>
              )}
              {!cfg.enabled && (
                <span
                  style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}
                >
                  Closed
                </span>
              )}
            </div>
          );
        })}
      </div>
      <button
        className="onboarding-save-btn"
        onClick={onSave}
        disabled={saving}
        style={{ marginTop: 12 }}
      >
        {saving ? "Saving..." : "Save Business Hours"}
      </button>
      {saveError && <div className="onboarding-error">{saveError}</div>}
    </div>
  );
}
