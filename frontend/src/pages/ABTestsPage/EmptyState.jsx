import { cardStyle } from "./utils";

export default function EmptyState({ message, icon }) {
  return (
    <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
      <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>{icon || "🔔"}</div>
      <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>
        {message}
      </h3>
      <p style={{ color: "var(--text-secondary)", margin: 0 }}>
        Create your first A/B test to get started
      </p>
    </div>
  );
}
