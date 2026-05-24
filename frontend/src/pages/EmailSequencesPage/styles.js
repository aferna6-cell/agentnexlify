export const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 24,
};

export const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--bg-primary)",
  color: "var(--text-primary)",
  fontSize: "0.9rem",
  boxSizing: "border-box",
};

export const selectStyle = {
  ...inputStyle,
  cursor: "pointer",
};

export const textareaStyle = {
  ...inputStyle,
  resize: "vertical",
  minHeight: 90,
  fontFamily: "inherit",
};

export const btnPrimary = {
  background: "var(--accent)",
  color: "#fff",
  border: "none",
  padding: "10px 20px",
  borderRadius: 8,
  fontWeight: 600,
  cursor: "pointer",
  fontSize: "0.9rem",
};

export const btnSecondary = {
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  padding: "8px 16px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.85rem",
};

export const btnDanger = {
  background: "rgba(248, 113, 113, 0.12)",
  color: "#f87171",
  border: "1px solid rgba(248, 113, 113, 0.25)",
  padding: "6px 14px",
  borderRadius: 8,
  cursor: "pointer",
  fontSize: "0.82rem",
  fontWeight: 600,
};

export const labelStyle = {
  display: "block",
  fontSize: "0.85rem",
  color: "var(--text-secondary)",
  marginBottom: 6,
};

export const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.65)",
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "center",
  zIndex: 1000,
  overflowY: "auto",
  padding: "40px 16px",
};

export const modalStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  borderRadius: 16,
  padding: "28px 32px",
  width: "100%",
  maxWidth: 720,
  border: "1px solid var(--border)",
  position: "relative",
};
