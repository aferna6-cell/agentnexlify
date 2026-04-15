/**
 * notify.js — minimal dark-theme toast notifications.
 *
 * Replaces native alert() across the dashboard. Vanilla DOM (no deps, no React state)
 * so it works from anywhere — event handlers, async catches, utilities.
 *
 * Usage:
 *   import { notify } from "@/utils/notify";  // or relative path
 *   notify.error("Failed to save");
 *   notify.success("Saved");
 *   notify.info("Heads up");
 *
 * Design: matches dashboard dark theme (frontend/src/index.css palette).
 * Auto-dismisses after 5s for info/success, 7s for error. Click to dismiss early.
 * Stacks bottom-right. Max 4 visible — older ones drop off.
 */

const CONTAINER_ID = "_notify_root";
const MAX_VISIBLE = 4;

const PALETTE = {
  error: { bg: "#2a0f15", border: "#7a1f2e", text: "#fecaca", icon: "✕" },
  success: { bg: "#0f1f15", border: "#2d6a4f", text: "#bbf7d0", icon: "✓" },
  info: { bg: "#0f1a2a", border: "#1e40af", text: "#bfdbfe", icon: "ℹ" },
  warn: { bg: "#2a1f0f", border: "#a16207", text: "#fde68a", icon: "⚠" },
};

function ensureContainer() {
  let c = document.getElementById(CONTAINER_ID);
  if (c) return c;
  c = document.createElement("div");
  c.id = CONTAINER_ID;
  Object.assign(c.style, {
    position: "fixed",
    bottom: "16px",
    right: "16px",
    zIndex: "999999",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    maxWidth: "420px",
    pointerEvents: "none",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  });
  document.body.appendChild(c);
  return c;
}

function show(level, message) {
  if (typeof document === "undefined") return; // SSR / tests
  const text = typeof message === "string" ? message : String(message ?? "Unknown error");
  const palette = PALETTE[level] || PALETTE.info;
  const container = ensureContainer();

  while (container.children.length >= MAX_VISIBLE) {
    container.removeChild(container.firstChild);
  }

  const toast = document.createElement("div");
  Object.assign(toast.style, {
    background: palette.bg,
    border: `1px solid ${palette.border}`,
    borderRadius: "8px",
    color: palette.text,
    padding: "12px 14px",
    fontSize: "14px",
    lineHeight: "1.4",
    boxShadow: "0 6px 20px rgba(0,0,0,0.4)",
    pointerEvents: "auto",
    cursor: "pointer",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    opacity: "0",
    transform: "translateX(20px)",
    transition: "opacity 180ms ease, transform 180ms ease",
  });

  const iconEl = document.createElement("span");
  iconEl.textContent = palette.icon;
  iconEl.style.fontWeight = "bold";
  iconEl.style.fontSize = "16px";
  iconEl.style.flexShrink = "0";

  const textEl = document.createElement("span");
  textEl.textContent = text;
  textEl.style.flex = "1";

  toast.appendChild(iconEl);
  toast.appendChild(textEl);
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateX(0)";
  });

  const ttl = level === "error" ? 7000 : 5000;
  let dismissed = false;
  const dismiss = () => {
    if (dismissed) return;
    dismissed = true;
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    setTimeout(() => toast.remove(), 200);
  };

  toast.addEventListener("click", dismiss);
  setTimeout(dismiss, ttl);
}

export const notify = {
  error: (msg) => show("error", msg),
  success: (msg) => show("success", msg),
  info: (msg) => show("info", msg),
  warn: (msg) => show("warn", msg),
};

export default notify;
