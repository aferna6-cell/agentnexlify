export const STORAGE_KEY_PREFIX = "anx_onboarding_";

export const DEFAULT_GREETING = "Hi! How can I help you today?";
export const DEFAULT_COLOR = "#00BFFF";

export const DAYS_OF_WEEK = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

export const DEFAULT_HOURS = Object.fromEntries(
  DAYS_OF_WEEK.map((d) => [
    d,
    {
      enabled: [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
      ].includes(d),
      start: "09:00",
      end: "17:00",
    },
  ]),
);

export const COLOR_SWATCHES = [
  "#00BFFF",
  "#6366F1",
  "#8B5CF6",
  "#EC4899",
  "#EF4444",
  "#F59E0B",
  "#10B981",
  "#14B8A6",
];

export const PLATFORM_INSTRUCTIONS = {
  HTML: "Paste this snippet before the closing </body> tag of your website.",
  WordPress:
    "Go to Appearance > Theme Editor > footer.php and paste the snippet before </body>. Or use a plugin like 'Insert Headers and Footers'.",
  Shopify:
    "Go to Online Store > Themes > Edit Code > theme.liquid and paste before </body>.",
  Wix: "Go to Settings > Custom Code > Add Custom Code and paste as Body - End.",
};
