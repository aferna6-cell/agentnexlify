import DOMPurify from "dompurify";

export function sanitizeDocHtml(html) {
  if (!html) return "";
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["iframe", "object", "embed", "form", "link", "meta"],
  });
}

export function formatDate(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
