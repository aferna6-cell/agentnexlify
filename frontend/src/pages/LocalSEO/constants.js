export const TABS = [
  { key: "audit", label: "SEO Audit" },
  { key: "geo", label: "GEO Score" },
  { key: "keywords", label: "Keywords" },
  { key: "competitors", label: "Competitors" },
  { key: "profile", label: "Profile" },
];

export const DIFFICULTY_COLORS = {
  low: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  medium: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  high: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

export const CATEGORY_ICONS = {
  technical: "⚙",
  content: "✎",
  on_page: "☑",
  link_analysis: "↗",
};

export const CATEGORY_LABELS = {
  technical: "Technical SEO",
  content: "Content Quality",
  on_page: "On-Page SEO",
  link_analysis: "Link Analysis",
};

export const PLATFORM_CONFIG = {
  chatgpt: { label: "ChatGPT", color: "#10a37f" },
  claude: { label: "Claude", color: "#d4a574" },
  perplexity: { label: "Perplexity", color: "#20b2aa" },
  gemini: { label: "Gemini", color: "#4285f4" },
};

export function getDifficultyLevel(difficulty) {
  if (difficulty <= 33) return "low";
  if (difficulty <= 66) return "medium";
  return "high";
}
