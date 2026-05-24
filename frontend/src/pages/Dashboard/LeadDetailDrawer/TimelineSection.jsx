import { useState, useEffect } from "react";
import { fetchLeadActivity } from "../../../utils/api/leads";
import { timelineIcon, formatTimelineDate } from "./helpers";

export default function TimelineSection({ lead, tenantId, token }) {
  const [timeline, setTimeline] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);

  useEffect(() => {
    if (!tenantId || !token || !lead?.id) return;
    setTimelineLoading(true);
    fetchLeadActivity(tenantId, token, lead.id)
      .then((data) => setTimeline(data.timeline || []))
      .catch((err) => {
        console.warn("Lead activity fetch failed:", err?.message);
        setTimeline([]);
      })
      .finally(() => setTimelineLoading(false));
  }, [tenantId, token, lead?.id]);

  return (
    <div className="intel-section">
      <div className="intel-title">Activity Timeline</div>
      {timelineLoading ? (
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "0.85rem",
            padding: "12px 0",
          }}
        >
          Loading...
        </div>
      ) : timeline.length === 0 ? (
        <div
          style={{
            color: "var(--text-muted)",
            fontSize: "0.85rem",
            padding: "12px 0",
          }}
        >
          No activity recorded yet.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {timeline.slice(0, 15).map((item, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 10,
                padding: "8px 0",
                borderBottom:
                  i < Math.min(timeline.length, 15) - 1
                    ? "1px solid var(--border-color, rgba(255,255,255,0.06))"
                    : "none",
                alignItems: "flex-start",
              }}
            >
              {timelineIcon(item.type)}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-primary)",
                    lineHeight: 1.4,
                    wordBreak: "break-word",
                  }}
                >
                  {item.description}
                </div>
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--text-muted)",
                    marginTop: 2,
                  }}
                >
                  {formatTimelineDate(item.created_at)}
                </div>
              </div>
            </div>
          ))}
          {timeline.length > 15 && (
            <div
              style={{
                fontSize: "0.78rem",
                color: "var(--text-muted)",
                padding: "8px 0",
                textAlign: "center",
              }}
            >
              +{timeline.length - 15} more events
            </div>
          )}
        </div>
      )}
    </div>
  );
}
