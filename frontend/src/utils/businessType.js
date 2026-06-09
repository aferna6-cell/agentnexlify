// Business-type alias resolution for the dashboard.
//
// SOURCE OF TRUTH: backend/services/business_profiles.py (`_TYPE_ALIASES` +
// `resolve_business_profile_key`). `business_type` is free-text on onboarding,
// not an enum — tenants store raw values like "plumbing", "cafe", "barber".
// The backend maps those aliases to canonical industry-pack keys. The Sidebar
// gates vertical-only pages on the canonical key, so it must resolve the raw
// stored value the same way the backend does. Keep this map in sync with the
// Python `_TYPE_ALIASES` dict above whenever a new alias is added there.

const TYPE_ALIASES = {
  other: "default",
  general: "default",
  default: "default",
  hvac: "hvac",
  contractor: "home_services",
  contractors: "home_services",
  plumbing: "home_services",
  electrical: "home_services",
  roofing: "home_services",
  landscaping: "home_services",
  cleaning: "home_services",
  pest_control: "home_services",
  painting: "home_services",
  flooring: "home_services",
  general_contractor: "home_services",
  construction: "home_services",
  moving: "home_services",
  home_services: "home_services",
  real_estate: "real_estate",
  realestate: "real_estate",
  dental: "dental",
  medical: "medical",
  health_wellness: "medical",
  healthcare: "medical",
  clinic: "medical",
  doctor: "medical",
  chiropractic: "medical",
  veterinary: "medical",
  salon: "salon",
  spa: "salon",
  beauty: "salon",
  barber: "salon",
  restaurant: "restaurant",
  bakery: "restaurant",
  bar_nightclub: "restaurant",
  cafe: "restaurant",
  catering: "restaurant",
  food_truck: "restaurant",
  legal: "legal",
  accounting: "professional_services",
  professional: "professional_services",
  professional_services: "professional_services",
  consulting: "professional_services",
  photography: "professional_services",
  tutoring: "professional_services",
  auto_shop: "auto_shop",
  automotive: "auto_shop",
  mechanic: "auto_shop",
  auto_detailing: "auto_shop",
  auto_detailer: "auto_shop",
  fitness: "fitness",
  retail: "retail",
};

// Canonical pack keys (industry_packs/__init__.py `_REGISTRY`). Anything not in
// the alias map and not already a canonical key falls back to "default".
const CANONICAL_KEYS = new Set([
  "default",
  "hvac",
  "home_services",
  "real_estate",
  "dental",
  "medical",
  "salon",
  "restaurant",
  "legal",
  "professional_services",
  "auto_shop",
  "fitness",
  "retail",
]);

/**
 * Resolve a raw stored business_type to its canonical industry-pack key.
 * Mirrors backend `resolve_business_profile_key`.
 * @param {string|null|undefined} raw
 * @returns {string} canonical key (e.g. "home_services"), "default" if unknown/empty
 */
export function resolveBusinessTypeKey(raw) {
  const normalized = (raw || "").trim().toLowerCase();
  if (!normalized) return "default";
  if (TYPE_ALIASES[normalized]) return TYPE_ALIASES[normalized];
  return CANONICAL_KEYS.has(normalized) ? normalized : "default";
}
