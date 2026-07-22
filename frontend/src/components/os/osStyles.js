/**
 * Shared inline styles for the Agent OS cards (audit 2026-07-22 M2).
 *
 * AskDataCard, ResearchCard, ProjectsCard, and ScheduledTasksCard each
 * carried an identical copy of these consts; a theme tweak meant four
 * edits (and OpportunityCards had already drifted to hardcoded hex).
 * One module, theme tokens only.
 */

export const cardStyle = {
  background: "var(--bg-secondary, var(--card-bg))",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: "18px 22px",
};

export const btnStyle = {
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  cursor: "pointer",
  fontSize: "0.85rem",
  color: "#fff",
  background: "var(--accent, #6366f1)",
};

export const btnQuiet = {
  ...btnStyle,
  background: "var(--bg-primary)",
  color: "var(--text-secondary)",
  border: "1px solid var(--border)",
};

// Width/flex is layout, not theme - callers spread and add their own
// ({ ...inputBaseStyle, flex: 1 } or { ...inputBaseStyle, width: "100%" }).
export const inputBaseStyle = {
  background: "var(--bg-primary)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text-primary, #f1f5f9)",
  padding: "8px 10px",
  fontSize: "0.85rem",
  boxSizing: "border-box",
};

export const headingStyle = {
  margin: "0 0 4px",
  fontSize: "1rem",
  fontWeight: 600,
  color: "var(--text-primary, #f1f5f9)",
};

export const mutedStyle = { fontSize: "0.8rem", color: "var(--text-muted)" };
