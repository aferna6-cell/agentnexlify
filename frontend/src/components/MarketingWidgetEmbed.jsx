import { useEffect } from "react";

const DEFAULT_WIDGET_SRC = "https://app.agentnexlify.com/widget/agentnexlify-widget.js";
const DEFAULT_API_BASE = "https://agentnexlify-production.up.railway.app";
const DEFAULT_API_KEY = "anx_zc2Gfxz5n1oZgrYbM1biHWRI1oV1rMSIBFuIDtaCK3k";
const SCRIPT_ID = "anx-marketing-widget";

function cleanupWidgetArtifacts() {
  const container = document.getElementById("anx-container");
  if (container) container.remove();

  const legacyHost = document.getElementById("nexlify-chat-widget");
  if (legacyHost) legacyHost.remove();

  const host = document.getElementById("anx-chat-widget");
  if (host) host.remove();

  window.__agentNexlifyWidget = false;
  window.__nexlifyWidgetLoaded = false;
  window.__anxWidgetLoaded = false;
}

export default function MarketingWidgetEmbed() {
  useEffect(() => {
    const existing = document.getElementById(SCRIPT_ID);
    if (existing) existing.remove();
    cleanupWidgetArtifacts();

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.async = true;
    script.src = import.meta.env.VITE_MARKETING_WIDGET_SRC || DEFAULT_WIDGET_SRC;
    script.setAttribute("data-api-key", import.meta.env.VITE_MARKETING_WIDGET_API_KEY || DEFAULT_API_KEY);
    script.setAttribute("data-api-base", import.meta.env.VITE_MARKETING_WIDGET_API_BASE || DEFAULT_API_BASE);

    const brandColor = import.meta.env.VITE_MARKETING_WIDGET_BRAND_COLOR;
    if (brandColor) script.setAttribute("data-brand-color", brandColor);

    document.body.appendChild(script);

    return () => {
      const mounted = document.getElementById(SCRIPT_ID);
      if (mounted) mounted.remove();
      cleanupWidgetArtifacts();
    };
  }, []);

  return null;
}
