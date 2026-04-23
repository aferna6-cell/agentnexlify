import { useState } from "react";

const DAYS = [
  { key: "monday", label: "Mon" },
  { key: "tuesday", label: "Tue" },
  { key: "wednesday", label: "Wed" },
  { key: "thursday", label: "Thu" },
  { key: "friday", label: "Fri" },
  { key: "saturday", label: "Sat" },
  { key: "sunday", label: "Sun" },
];

function defaultHours() {
  return {
    monday: { open: "08:00", close: "18:00" },
    tuesday: { open: "08:00", close: "18:00" },
    wednesday: { open: "08:00", close: "18:00" },
    thursday: { open: "08:00", close: "18:00" },
    friday: { open: "08:00", close: "18:00" },
    saturday: { open: "09:00", close: "14:00" },
    sunday: null,
  };
}

export default function VisualHoursPicker({ value, onChange }) {
  const [hours, setHours] = useState(() => value || defaultHours());

  function update(next) {
    setHours(next);
    onChange(next);
  }

  function toggleDay(key) {
    const next = { ...hours };
    if (next[key] === null) {
      next[key] = { open: "08:00", close: "18:00" };
    } else {
      next[key] = null;
    }
    update(next);
  }

  function setTime(key, field, val) {
    const next = {
      ...hours,
      [key]: { ...hours[key], [field]: val },
    };
    update(next);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {DAYS.map(({ key, label }) => {
        const isOpen = hours[key] !== null;
        return (
          <div
            key={key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              minHeight: 48,
              padding: "4px 0",
              borderBottom: "1px solid rgba(255,255,255,0.05)",
            }}
          >
            <span
              style={{
                width: 32,
                fontSize: "0.82rem",
                color: isOpen
                  ? "rgba(255,255,255,0.8)"
                  : "rgba(255,255,255,0.3)",
                flexShrink: 0,
              }}
            >
              {label}
            </span>

            {/* Toggle switch */}
            <button
              type="button"
              onClick={() => toggleDay(key)}
              aria-label={isOpen ? `Close ${label}` : `Open ${label}`}
              style={{
                width: 40,
                height: 24,
                borderRadius: 12,
                border: "none",
                background: isOpen ? "#6366f1" : "rgba(255,255,255,0.12)",
                position: "relative",
                cursor: "pointer",
                flexShrink: 0,
                transition: "background 0.15s ease",
              }}
            >
              <span
                style={{
                  position: "absolute",
                  top: 3,
                  left: isOpen ? 19 : 3,
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: "#fff",
                  transition: "left 0.15s ease",
                }}
              />
            </button>

            {isOpen ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flex: 1,
                }}
              >
                <input
                  type="time"
                  value={hours[key].open}
                  onChange={(e) => setTime(key, "open", e.target.value)}
                  style={timeInputStyle}
                />
                <span
                  style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.8rem" }}
                >
                  to
                </span>
                <input
                  type="time"
                  value={hours[key].close}
                  onChange={(e) => setTime(key, "close", e.target.value)}
                  style={timeInputStyle}
                />
              </div>
            ) : (
              <span
                style={{
                  fontSize: "0.82rem",
                  color: "rgba(255,255,255,0.25)",
                  flex: 1,
                }}
              >
                Closed
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

const timeInputStyle = {
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  padding: "8px 10px",
  color: "#e2e8f0",
  fontSize: "0.85rem",
  minHeight: 44,
  minWidth: 0,
  flex: 1,
  maxWidth: 120,
  boxSizing: "border-box",
};
