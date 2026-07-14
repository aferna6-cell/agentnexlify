# UI Consistency + Responsive Audit — Launch Readiness

Date: 2026-07-09
Scope: `frontend/` dashboard + marketing site (React 18 / Vite). Read-only. Focus on the new admin dashboards (Funnel, Tenant Health, Referral, Analytics) and the `/ai-front-desk/*` vertical landing pages, cross-checked against `design.md` tokens, `frontend/src/index.css`, and `.claude/rules/frontend-patterns.md` anti-slop blocklist.
Method: traced actual rendered pages + shared components, not a lint pass. Every finding cites `file:line`.

## Severity counts
- HIGH: 3
- MEDIUM: 5
- LOW: 7

Token source of truth: `design.md` + `frontend/src/index.css` (`--accent #00bfff`, `--red #ff4444`, `--green #34d399`, `--yellow #f5a623`, `--text-primary #f0f0f5`, `--border #222233`, radius `6/10/20/50%`).

---

# HIGH

## H1 — Admin dashboards render on an off-brand color palette
- **Severity:** HIGH
- **Category:** Visual Consistency
- **Location:** `frontend/src/pages/AdminFunnelPage.jsx:59` (`FUNNEL_COLORS = ["#6366f1","#8b5cf6","#f59e0b","#10b981"]`), `:536`,`:541`,`:546` (WeeklyCard colors), `:367` (`color:"#fff"`); `frontend/src/pages/AdminAnalyticsPage.jsx:41`,`:50`,`:416` (`#f87171`); `frontend/src/pages/AdminReferralPage.jsx:89` (`#10b981`); `frontend/src/pages/AdminHealthPage.jsx:18` (`red:"#f87171"`); `frontend/src/pages/AdminTenantHealthPage.jsx` (amber row tints `rgba(245,158,11,...)`).
- **Issue:** The admin pages hardcode a Tailwind-style palette — indigo `#6366f1` as the primary/chart color, coral `#f87171` for errors, emerald `#10b981` for success, amber `#f59e0b` for warnings. The rest of the app uses brand tokens: accent `#00bfff` (cyan), `--red #ff4444`, `--green #34d399`, `--yellow #f5a623`. So the funnel chart bars, "Last 7 Days" cards, and error text on admin pages are visually a different product than every other dashboard page.
- **Impact:** Two color systems inside one dashboard. Charts on `/admin/funnel` are indigo; charts elsewhere are cyan. Error text is coral on admin, `#ff4444` everywhere else. Reads as unfinished/bolted-on.
- **Evidence:** `FUNNEL_COLORS` and `WeeklyCard color="#6366f1"` are raw hex, not tokens. `#f87171` appears 8+ times across admin files as the "red."
- **Reproduction:** Open `/admin/funnel` and `/admin/analytics` next to `/analytics` (tenant AnalyticsPage) — chart/error hues differ.
- **Recommended fix:** Replace the hardcoded arrays with token vars: primary → `var(--accent)`, red → `var(--red)`, green → `var(--green)`, yellow → `var(--yellow)`, purple → `var(--purple)`. For Recharts that need literals, read the computed CSS var once.
- **Confidence:** High.

## H2 — Plan display-name drift: "Chatbot / Agent OS" vs "AI Front Desk / AI Workforce"
- **Severity:** HIGH
- **Category:** Visual Consistency (copy/terminology)
- **Location:** `frontend/src/pages/BillingPage.jsx:14`,`:21` (`name:"Chatbot"`, `name:"Agent OS"`); `frontend/src/pages/FreeWidget.jsx:78`,`:92` (same). Contrast: `SignupPage.jsx:14`,`:20`; `wizard/WizardStepPlan.jsx:10`,`:19`; `components/UpgradePrompt.jsx:9-10`; `components/RequirePaid.jsx:35`,`:48`; `pages/verticals/VerticalLanding.jsx:244`,`:263`; `pages/Home.jsx:514`,`:797`,`:824` — all use "AI Front Desk" / "AI Workforce".
- **Issue:** The customer-facing display names for the two plans are inconsistent. Marketing site, signup, onboarding wizard, upgrade prompts and vertical pages call them "AI Front Desk" ($19.99) and "AI Workforce" ($99.99). The Billing page and the FreeWidget checkout call the same plans "Chatbot" and "Agent OS."
- **Impact:** A prospect signs up for "AI Front Desk," then lands on the Billing page and sees a plan called "Chatbot." Looks like a different product / possible billing error. This is on the two highest-trust surfaces (checkout + billing).
- **Evidence:** `BillingPage.jsx:14 name:"Chatbot"` vs `SignupPage.jsx:14 name:"AI Front Desk"` — same `chatbot` plan key, two display names.
- **Reproduction:** Sign up (see "AI Front Desk") → go to Billing (see "Chatbot").
- **Recommended fix:** Pick one canonical display-name pair and centralize it (a `PLAN_DISPLAY` map imported everywhere). The internal keys `chatbot`/`agent_os` stay; the labels shown to users must match the marketing names.
- **Confidence:** High.

## H3 — Admin Analytics plan map omits the two plans actually sold
- **Severity:** HIGH
- **Category:** Visual Consistency (data correctness)
- **Location:** `frontend/src/pages/AdminAnalyticsPage.jsx:28-42` — `PLAN_LABELS` = {free, growth, professional, autopilot, enterprise}; `PLAN_COLORS` same keys.
- **Issue:** The plan-label and plan-color maps only contain legacy/grandfathered plan names. The current sold plans `chatbot` and `agent_os` (CLAUDE.md, repriced 2026-06-15) are absent. Tenants on those plans render with the raw key (e.g. "agent_os") and an undefined color in the plan-distribution pie/legend.
- **Impact:** The admin plan-distribution chart mislabels/miscolors the majority of real paying tenants. The two plans the business runs on don't appear correctly in the analytics built to track them.
- **Evidence:** No `chatbot:` or `agent_os:` key in `PLAN_LABELS`/`PLAN_COLORS`; `PIE_COLORS` is a fixed 6-slot array keyed by legacy order.
- **Reproduction:** `/admin/analytics` with any `chatbot`/`agent_os` tenant → legend shows raw keys / default color.
- **Recommended fix:** Add `chatbot: "AI Front Desk"` and `agent_os: "AI Workforce"` to `PLAN_LABELS` and give them `var(--accent)` / `var(--green)` (or similar) in `PLAN_COLORS`. Keep legacy keys for grandfathered tenants.
- **Confidence:** High.

---

# MEDIUM

## M1 — Two live vertical-landing systems with divergent copy conventions
- **Severity:** MEDIUM
- **Category:** Visual Consistency
- **Location:** Standalone: `main.jsx:130` `/salon-booking-chatbot` → `SalonChatbot.jsx` (also `DentalChatbot`, `RestaurantChatbot`, `AutoShopChatbot`, `MedicalOfficeChatbot`). Data-driven: `main.jsx:134-141` `/ai-front-desk/*` → `VerticalLanding.jsx` + `verticals.js`. Both import the same `components/VerticalPage.jsx`.
- **Issue:** Two landing pages exist for the same verticals (e.g. `/salon-booking-chatbot` and `/ai-front-desk/salons`) with different copy rules. The standalone pages use em dashes and punchier stat claims (`SalonChatbot.jsx` H1 "Fill Every Chair — AI Booking…", painPoint "40% of salon bookings happen outside business hours"); `verticals.js` explicitly bans em dashes and fabricated stats (header comment lines 5-9; em-dash count: SalonChatbot 4, DentalChatbot 6, verticals.js 0).
- **Impact:** Inconsistent brand voice between two pages a prospect can reach for the same service; SEO cannibalization (two URLs targeting the same intent). Different H1 style and stat framing side by side.
- **Evidence:** em-dash grep above; both route sets mounted in `main.jsx`.
- **Reproduction:** Visit `/salon-booking-chatbot` then `/ai-front-desk/salons`.
- **Recommended fix:** Decide which set is canonical, 301 the other (or `rel=canonical`), and align copy conventions. If both must stay, unify voice (drop em dashes + unverified stats from the standalone set).
- **Confidence:** High that both are live; Medium on the SEO/brand impact weighting.

## M2 — Duplicate, competing internal-link rows on `/ai-front-desk/*`
- **Severity:** MEDIUM
- **Category:** Visual Consistency
- **Location:** `components/VerticalPage.jsx:31` (`otherVerticals = VERTICALS.filter(v => v.slug !== slug)`), `:116-133` ("Also explore" nav → `/restaurant-chatbot`, `/salon-booking-chatbot`, …); plus `VerticalLanding.jsx:288-305` ("AI Front Desk for other industries" → `/ai-front-desk/*`).
- **Issue:** A `/ai-front-desk/*` page renders two cross-link sections with two different URL schemes: its own "AI Front Desk for other industries" pointing at sibling `/ai-front-desk/*` pages, and the inherited "Also explore" pointing at the older `/*-chatbot` standalone pages. Also the filter at `VerticalPage.jsx:31` compares against `slug="ai-front-desk-salons"` (passed at `VerticalLanding.jsx:229`), which never matches the `VERTICALS` slugs, so the current vertical is never excluded — all 5 always show.
- **Impact:** Confusing double navigation feeding two competing page sets; dilutes the internal-linking that the pages exist for.
- **Evidence:** Both sections render in the same `VerticalLanding` tree; `slug` mismatch means no self-exclusion.
- **Reproduction:** Scroll the bottom of `/ai-front-desk/dentists`.
- **Recommended fix:** Suppress the inherited "Also explore" nav on `/ai-front-desk/*` (prop flag), or point both rows at one page set. Fix the self-exclusion slug.
- **Confidence:** High.

## M3 — Admin auth via native `window.prompt`, duplicated per page
- **Severity:** MEDIUM
- **Category:** Visual Consistency (UX)
- **Location:** `AdminAnalyticsPage.jsx:54-64` (module-level `_adminSecret`, `window.prompt("Enter admin secret:")`), `AdminFunnelPage.jsx:16` (same pattern per comment); repeated across the admin pages.
- **Issue:** Admin gate is a native browser `prompt()` — unstyled, off-theme, and each page holds its own module-level secret, so navigating between admin pages re-prompts.
- **Impact:** Jarring OS-chrome dialog inside a dark-theme app; repeated prompts across the admin section; looks unfinished.
- **Evidence:** `window.prompt` at `AdminAnalyticsPage.jsx:58`.
- **Reproduction:** Open `/admin/analytics`, then `/admin/funnel` — prompted twice.
- **Recommended fix:** One themed admin-auth modal/route holding the secret in shared context for the admin section.
- **Confidence:** High.

## M4 — Admin controls have no design-system focus state
- **Severity:** MEDIUM
- **Category:** Visual Consistency (accessibility)
- **Location:** All six `Admin*.jsx` pages — grep for `:focus`/`outline`/`onFocus` returns 0 in each. Buttons/sort headers/refresh are inline-styled (e.g. `AdminFunnelPage.jsx:360-367`).
- **Issue:** The pages are fully inline-styled; inline styles cannot express `:focus`/`:focus-visible`, so none of the admin interactive elements get the design system's accent-glow focus ring (`design.md` Accessibility: "All interactive elements have visible focus states"). Keyboard users get only the browser default.
- **Impact:** Inconsistent keyboard affordance vs the CSS-class dashboard pages; accessibility gap.
- **Evidence:** `:focus` count = 0 across `AdminAnalyticsPage/FunnelPage/HealthPage/PromotionsPage/ReferralPage/TenantHealthPage`.
- **Recommended fix:** Move admin buttons/inputs to shared CSS classes (e.g. `.btn`, `.admin-table`) that already carry `:focus-visible` accent-glow, or add a small scoped `<style>` with focus rules.
- **Confidence:** High.

## M5 — Emoji used as UI-chrome icons across all vertical feature cards
- **Severity:** MEDIUM
- **Category:** Visual Consistency
- **Location:** `frontend/src/pages/verticals/verticals.js` — every `icon:` field is an emoji (`:30 "📅"`, `:36 "💬"`, `:42 "🔔"`, … 72 total across 12 verticals × 6 cards), rendered at `VerticalPage.jsx:74` `<span className="vp-card__icon">{f.icon}</span>`. Same in standalone `SalonChatbot.jsx:19`, `DentalChatbot.jsx`, etc.
- **Issue:** `.claude/rules/frontend-patterns.md` anti-slop blocklist bans "Emoji in UI chrome (labels, buttons, headers, empty states)" unless a brand token or user content. Feature-card icons are UI chrome.
- **Impact:** Emoji icons render inconsistently across OS/browsers and read as AI-generated default styling on the main SEO landing pages prospects see.
- **Evidence:** icon fields are literal emoji; no icon component/system.
- **Reproduction:** Any `/ai-front-desk/*` or `/*-chatbot` page feature grid.
- **Recommended fix:** Swap to a consistent inline-SVG/icon set (monochrome, accent-tinted) or drop icons. If emoji stay by deliberate choice, record the override per the blocklist rule.
- **Confidence:** High on the rule violation; Medium on impact (common on marketing pages).

---

# LOW

## L1 — Admin empty states lack icon + CTA per spec
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `AdminFunnelPage.jsx:440-465`, `AdminReferralPage.jsx:361-393`, `AdminTenantHealthPage.jsx:567-585`, `AdminAnalyticsPage.jsx:613`.
- **Issue:** Empty states have a title + a guidance sentence (good — better than bare "0"/"No data"), but omit the `design.md` empty-state pattern's 48px icon and primary CTA button. Copy also uses hyphen-as-dash ("best-effort - check…").
- **Impact:** Minor polish gap; still functional and helpful.
- **Recommended fix:** Add the standard empty-state icon + a primary CTA where one exists (e.g. "Share referral program").
- **Confidence:** High.

## L2 — Bright white `#fff` button text in dark mode
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `AdminFunnelPage.jsx:367` (`color:"#fff"` on accent refresh button), `AdminPromotionsPage.jsx:26`.
- **Issue:** `design.md` Do-NOT: "Use bright white (#fff) as text in dark mode — use #f0f0f5"; buttons should use `--accent-contrast`.
- **Recommended fix:** Use `var(--accent-contrast)` / `var(--text-primary)`.
- **Confidence:** High.

## L3 — Button radius off token on vertical pages
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `VerticalLanding.jsx:131` (`.vl-btn` uses `var(--radius)` = 10px), `VerticalPage.jsx:188` (`.vp-btn` uses `var(--radius)` = 10px), `VerticalLanding.jsx:74` (`.vl-plan__badge border-radius:999px`).
- **Issue:** `design.md` buttons = 6px (`--radius-sm`); pills = 20px. Buttons here use the 10px card radius; the plan badge uses `999px` (not a token value 6/10/20/50%). Internal-link chips at `VerticalPage.jsx:322` correctly use `--radius-sm`, so it's inconsistent even within the same file.
- **Recommended fix:** `.vl-btn`/`.vp-btn` → `var(--radius-sm)`; badge → `20px` (or `--radius-pill` token).
- **Confidence:** High.

## L4 — Box-shadow glow on hover in dark mode
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `VerticalPage.jsx:203` (`.vp-btn--primary:hover box-shadow:0 0 20px var(--accent-glow)`), `VerticalLanding.jsx:159`.
- **Issue:** `design.md` Do-NOT: "Add box shadows in dark mode (only in light mode)." The accent glow is a deliberate hover affordance, but it's off-spec and unique to these pages.
- **Recommended fix:** Use border-color/background hover (as `.vp-btn--outline` does) or add a token for allowed glow and document the override.
- **Confidence:** Medium (arguably intentional).

## L5 — Stale CSS-var fallbacks encode a wrong palette
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** admin inline styles, e.g. `AdminFunnelPage.jsx:165` (`var(--border,#374151)`), `:184` (`var(--bg-secondary,#1e2030)`), `:366` (`var(--accent,#6366f1)`), `:170` (`var(--text-muted,#9ca3af)`); `AdminReferralPage.jsx:53`,`:56`,`:64`,`:419`.
- **Issue:** Fallback literals are Tailwind slate/indigo, not brand tokens (real values `#222233`, `#111118`, `#00bfff`, `#5c5c72`). Currently masked because the vars resolve, but any resolution failure flips the page to the wrong palette, and the fallbacks confirm these pages were built against a different design source (root cause of H1).
- **Recommended fix:** Correct fallbacks to real token values or drop the fallback and rely on `index.css`.
- **Confidence:** High.

## L6 — Long-name table overflow: nowrap without truncation
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `AdminTenantHealthPage.jsx:281-283` (`business_name` in a `whiteSpace:nowrap` cell, no `maxWidth`/ellipsis); `TD_STYLE` at `:104`.
- **Issue:** Tables correctly wrap in `overflowX:auto` (`:236`) and empty values use `|| "-"` (good), but a very long business name/email forces a wide horizontal scroll instead of truncating with an ellipsis.
- **Impact:** On mobile/tablet, one long tenant name pushes the whole table wide.
- **Recommended fix:** Add `max-width` + `text-overflow:ellipsis` (with `title` tooltip) on the name/email columns.
- **Confidence:** Medium.

## L7 — Native `<details>` FAQ has no styled marker or summary focus ring
- **Severity:** LOW · **Category:** Visual Consistency
- **Location:** `VerticalPage.jsx:106-109`, styles `:335-338`.
- **Issue:** FAQ accordion uses raw `<details>/<summary>` with the browser default disclosure triangle and no `:focus-visible` styling on `summary`. Works, but visually unpolished vs a designed accordion; keyboard focus is browser-default.
- **Recommended fix:** Style/hide the marker, add a `+/–` indicator and a `:focus-visible` ring.
- **Confidence:** Medium.

---

# Quick wins (low effort, high visible payoff)
1. H2 — centralize plan display names; fix Billing + FreeWidget to "AI Front Desk"/"AI Workforce". (checkout/billing trust)
2. H3 — add `chatbot`/`agent_os` to `AdminAnalyticsPage` `PLAN_LABELS`/`PLAN_COLORS`. (2-line fix)
3. H1 — swap the admin hardcoded hex (`#6366f1`/`#f87171`/`#10b981`/`#f59e0b`) for `var(--accent/--red/--green/--yellow)`. (find-and-replace across 6 files)
4. L2/L3 — `#fff` → `--accent-contrast`; `.vl-btn`/`.vp-btn` radius → `--radius-sm`.
5. M2 — suppress the inherited "Also explore" nav on `/ai-front-desk/*` and fix the self-exclusion slug.

# Architectural changes (larger, plan separately)
1. Kill the duplicate vertical-page system (M1): pick canonical `/ai-front-desk/*`, redirect the `/*-chatbot` set, unify copy voice.
2. De-inline the admin dashboards (H1/M4/L5): move to shared CSS classes so they inherit tokens + `:focus-visible` and stop carrying a private palette. These pages are the root cause of most Visual Consistency findings.
3. One themed admin-auth gate for the whole `/admin` section (M3), replacing per-page `window.prompt`.

# Ship recommendation
Fix H2 and H3 before launch (customer-facing plan-name mismatch on billing + wrong plans in admin analytics are the two that erode trust); H1 and the M-tier items can ship as a fast-follow but should be scheduled, not left — the admin pages are visibly a different design language than the product.
