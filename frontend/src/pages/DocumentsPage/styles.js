export const overlay = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.5)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

export const modalBase = {
  background: "var(--bg-primary)",
  borderRadius: 12,
  padding: 24,
  border: "1px solid var(--border)",
};

export const sectionLabel = {
  fontSize: "0.75rem",
  color: "var(--text-muted)",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 8,
};

export const fieldLabel = {
  display: "block",
  fontSize: "0.8rem",
  marginBottom: 4,
  color: "var(--text-secondary)",
};

export const cancelBtn = {
  background: "transparent",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "8px 16px",
  color: "var(--text-primary)",
  cursor: "pointer",
};

export const warnBox = (c) => ({
  marginBottom: 12,
  padding: "8px 12px",
  background: `rgba(${c},0.1)`,
  border: `1px solid rgba(${c},0.3)`,
  borderRadius: 8,
  fontSize: "0.8rem",
});
