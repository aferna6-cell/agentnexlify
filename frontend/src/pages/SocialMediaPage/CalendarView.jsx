import { PLATFORM_MAP, MONTH_NAMES } from "./constants";
import { getDaysInMonth, getFirstDayOfWeek } from "./helpers";
import { btnSecondary } from "./styles";

export default function CalendarView({
  posts,
  calendarMonth,
  setCalendarMonth,
  onEdit,
}) {
  const calendarDays = getDaysInMonth(calendarMonth.year, calendarMonth.month);
  const calendarStartDay = getFirstDayOfWeek(
    calendarMonth.year,
    calendarMonth.month,
  );

  const getPostsForDate = (day) => {
    const dateStr = `${calendarMonth.year}-${String(calendarMonth.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return posts.filter((p) => {
      const d = p.scheduled_for || p.published_at || p.created_at;
      return d && d.startsWith(dateStr);
    });
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <button
          onClick={() =>
            setCalendarMonth((m) => {
              const d = new Date(m.year, m.month - 1, 1);
              return { year: d.getFullYear(), month: d.getMonth() };
            })
          }
          style={btnSecondary}
        >
          &larr;
        </button>
        <h3
          style={{
            margin: 0,
            color: "var(--text-primary)",
            fontSize: "1rem",
          }}
        >
          {MONTH_NAMES[calendarMonth.month]} {calendarMonth.year}
        </h3>
        <button
          onClick={() =>
            setCalendarMonth((m) => {
              const d = new Date(m.year, m.month + 1, 1);
              return { year: d.getFullYear(), month: d.getMonth() };
            })
          }
          style={btnSecondary}
        >
          &rarr;
        </button>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 2,
        }}
      >
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div
            key={d}
            style={{
              textAlign: "center",
              fontSize: "0.7rem",
              color: "var(--text-muted)",
              padding: "6px 0",
              fontWeight: 600,
            }}
          >
            {d}
          </div>
        ))}
        {Array.from({ length: calendarStartDay }, (_, i) => (
          <div key={`empty-${i}`} style={{ minHeight: 80 }} />
        ))}
        {Array.from({ length: calendarDays }, (_, i) => {
          const day = i + 1;
          const dayPosts = getPostsForDate(day);
          const now = new Date();
          const isToday =
            now.getFullYear() === calendarMonth.year &&
            now.getMonth() === calendarMonth.month &&
            now.getDate() === day;
          return (
            <div
              key={day}
              style={{
                minHeight: 80,
                background: isToday
                  ? "var(--accent-dim)"
                  : "var(--bg-secondary, var(--card-bg))",
                border: isToday
                  ? "2px solid var(--accent)"
                  : "1px solid var(--border)",
                borderRadius: 6,
                padding: "4px 6px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  color: isToday ? "var(--accent)" : "var(--text-secondary)",
                  marginBottom: 2,
                }}
              >
                {day}
              </div>
              {dayPosts.map((post) => (
                <div
                  key={post.id}
                  onClick={() => onEdit(post)}
                  style={{
                    fontSize: "0.6rem",
                    padding: "2px 4px",
                    borderRadius: 3,
                    background:
                      PLATFORM_MAP[post.platform]?.color || "var(--accent)",
                    color: "#fff",
                    marginBottom: 2,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    fontWeight: 500,
                  }}
                  title={`${PLATFORM_MAP[post.platform]?.label}: ${(post.content || "").slice(0, 60)}`}
                >
                  {PLATFORM_MAP[post.platform]?.icon}{" "}
                  {(post.content || "").slice(0, 30)}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
