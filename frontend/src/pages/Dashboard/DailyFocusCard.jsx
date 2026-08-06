import { useState, useEffect } from "react";
import { fetchDailyFocus } from "../../utils/api/insights";

const KIND_ICONS = {
  new_leads: "⚡",
  appointments_today: "📅",
  cold_leads: "🧊",
  overdue_invoices: "💳",
};

export default function DailyFocusCard({ tenantId, token }) {
  const [picks, setPicks] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId || !token) return;
    let cancelled = false;

    fetchDailyFocus(tenantId, token)
      .then((res) => {
        if (!cancelled) setPicks(res?.picks ?? []);
      })
      .catch((err) => {
        console.warn("Daily focus fetch failed:", err?.message);
        if (!cancelled) setPicks(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tenantId, token]);

  if (loading) {
    return (
      <div className="crm-widget-card">
        <h3>Today's Focus</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Checking your leads and calendar...
        </p>
      </div>
    );
  }

  if (!picks) return null; // silently hide on error

  return (
    <div className="crm-widget-card">
      <h3>Today's Focus</h3>
      {picks.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          All clear — no new leads waiting, nothing going cold. Nice work.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
          {picks.map((p, i) => (
            <div key={p.kind} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{ fontSize: "1rem", lineHeight: 1.4 }}>
                {KIND_ICONS[p.kind] || `${i + 1}.`}
              </span>
              <div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-primary)", fontWeight: 600 }}>
                  {p.title}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {p.reason}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
