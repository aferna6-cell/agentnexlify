import DOMPurify from "dompurify";

const ALLOWED_TAGS = ["p", "ul", "ol", "li", "strong", "em", "code", "br"];

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/**
 * Assistant chat text as a small markdown subset.
 * HTML in the source is escaped before tags are added, then DOMPurify
 * keeps only the tags this renderer emits.
 */
export function renderAssistantMarkdown(source) {
  const lines = String(source ?? "")
    .replace(/\r\n/g, "\n")
    .split("\n");
  const html = [];
  let list = null;

  const closeList = () => {
    if (!list) return;
    html.push(list === "ul" ? "</ul>" : "</ol>");
    list = null;
  };

  for (const line of lines) {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      if (list !== kind) {
        closeList();
        html.push(kind === "ul" ? "<ul>" : "<ol>");
        list = kind;
      }
      html.push(`<li>${inlineMarkdown((bullet || numbered)[1])}</li>`);
      continue;
    }
    closeList();
    if (!line.trim()) continue;
    html.push(`<p>${inlineMarkdown(line)}</p>`);
  }
  closeList();

  return DOMPurify.sanitize(html.join(""), {
    ALLOWED_TAGS,
    ALLOWED_ATTR: [],
  });
}
