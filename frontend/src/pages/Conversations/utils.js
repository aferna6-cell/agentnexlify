export function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export function formatNoteTime(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function _inlineMd(s) {
  s = s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );
  return s;
}

export function renderMarkdown(text) {
  if (!text) return "";
  const lines = text.split("\n");
  const out = [];
  let inList = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    if (
      trimmed.startsWith("- ") ||
      trimmed.startsWith("* ") ||
      /^\d+\.\s/.test(trimmed)
    ) {
      if (!inList) {
        out.push('<ul style="margin:4px 0 4px 16px;padding:0;">');
        inList = true;
      }
      const content = trimmed.replace(/^[-*]\s|^\d+\.\s/, "");
      out.push("<li>" + _inlineMd(content) + "</li>");
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      if (trimmed === "") {
        if (out.length > 0) out.push("<br>");
      } else {
        out.push(_inlineMd(line));
        const nextTrimmed = (lines[i + 1] || "").trim();
        if (
          nextTrimmed &&
          !nextTrimmed.startsWith("- ") &&
          !nextTrimmed.startsWith("* ") &&
          !/^\d+\.\s/.test(nextTrimmed)
        ) {
          out.push("<br>");
        }
      }
    }
  }
  if (inList) out.push("</ul>");
  while (out.length && out[out.length - 1] === "<br>") out.pop();
  return out.join("");
}

export function tagPillStyle(tag, tagColorMap) {
  const color = tagColorMap[tag] || null;
  if (color) {
    return {
      display: "inline-block",
      padding: "1px 7px",
      borderRadius: 10,
      fontSize: "0.68rem",
      background: color + "26",
      color: color,
    };
  }
  return {
    display: "inline-block",
    padding: "1px 7px",
    borderRadius: 10,
    fontSize: "0.68rem",
    background: "var(--accent-dim, rgba(0,191,255,0.15))",
    color: "var(--accent, #00BFFF)",
  };
}

export function buildTagColorMap(tagDefs) {
  const map = {};
  (tagDefs || []).forEach((td) => {
    if (td.tag_name && td.tag_color) map[td.tag_name] = td.tag_color;
  });
  return map;
}
