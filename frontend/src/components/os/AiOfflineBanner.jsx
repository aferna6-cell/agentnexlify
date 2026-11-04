/**
 * Persistent alert while the latest Agent OS turn was not live AI.
 */
export default function AiOfflineBanner() {
  return (
    <div
      role="alert"
      style={{
        padding: "10px 16px",
        background: "rgba(245,158,11,0.12)",
        borderBottom: "1px solid rgba(245,158,11,0.35)",
        color: "#fbbf24",
        fontSize: "0.82rem",
        fontWeight: 600,
        lineHeight: 1.45,
      }}
    >
      AI generation is unavailable. Replies right now come from built-in
      templates, not live AI. Review every draft before you use it.
    </div>
  );
}
