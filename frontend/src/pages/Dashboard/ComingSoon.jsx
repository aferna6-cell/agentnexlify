export default function ComingSoon({ title }) {
  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>{title}</h1>
        <p>This feature is coming soon.</p>
      </div>
      <div style={{
        background: "var(--bg-card, #fff)",
        border: "1px solid var(--border, #e5e7eb)",
        borderRadius: 12,
        padding: "48px 32px",
        textAlign: "center",
        color: "var(--text-secondary, #6b7280)",
        fontSize: 15,
        marginTop: 24,
      }}>
        We're building this right now. Check back soon!
      </div>
    </div>
  );
}
