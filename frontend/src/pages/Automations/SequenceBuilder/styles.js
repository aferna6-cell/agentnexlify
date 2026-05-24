export const overlayStyle = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  animation: "fadeIn 0.2s ease",
};

export const modalStyle = {
  background: "var(--bg-card)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  width: "860px",
  maxWidth: "95vw",
  maxHeight: "90vh",
  overflowY: "auto",
  padding: "28px",
  display: "flex",
  flexDirection: "column",
  gap: "20px",
};

export const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--text-primary)",
  fontSize: "14px",
  outline: "none",
  boxSizing: "border-box",
};

export const selectStyle = { ...inputStyle, cursor: "pointer" };

export const labelStyle = {
  color: "var(--text-secondary)",
  fontSize: "12px",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "6px",
  display: "block",
};

export const stepCardStyle = {
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  position: "relative",
};

export const btnPrimary = {
  padding: "10px 20px",
  background: "var(--accent)",
  color: "var(--accent-contrast)",
  border: "none",
  borderRadius: "var(--radius-sm)",
  cursor: "pointer",
  fontWeight: 600,
  fontSize: "14px",
};

export const btnSecondary = {
  padding: "8px 14px",
  background: "transparent",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  cursor: "pointer",
  fontSize: "13px",
};

export const toolbarBtn = {
  padding: "4px 8px",
  background: "var(--bg-card)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
  borderRadius: "3px",
  cursor: "pointer",
  fontSize: "12px",
  fontWeight: 600,
  minWidth: "28px",
  lineHeight: 1,
};
