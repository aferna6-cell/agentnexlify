export const PLATFORMS = [
  { key: "facebook", label: "Facebook", color: "#1877f2", icon: "f" },
  { key: "instagram", label: "Instagram", color: "#e4405f", icon: "Ig" },
  { key: "twitter", label: "Twitter/X", color: "#000000", icon: "X" },
  { key: "linkedin", label: "LinkedIn", color: "#0a66c2", icon: "in" },
  {
    key: "google_business",
    label: "Google Business",
    color: "#4285f4",
    icon: "G",
  },
];

export const PLATFORM_MAP = Object.fromEntries(
  PLATFORMS.map((p) => [p.key, p]),
);

export const CHAR_LIMITS = {
  twitter: 280,
  linkedin: 3000,
  facebook: 2200,
  instagram: 2200,
  google: 2200,
};

export const STATUS_STYLES = {
  draft: {
    label: "Draft",
    color: "var(--text-secondary)",
    bg: "var(--hover-overlay)",
  },
  scheduled: {
    label: "Scheduled",
    color: "var(--purple, #8b5cf6)",
    bg: "rgba(139, 92, 246, 0.15)",
  },
  published: {
    label: "Published",
    color: "var(--green)",
    bg: "var(--green-dim)",
  },
  failed: {
    label: "Failed",
    color: "#f87171",
    bg: "rgba(248, 113, 113, 0.15)",
  },
};

export const TONES = ["professional", "casual", "friendly", "promotional"];

export const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
