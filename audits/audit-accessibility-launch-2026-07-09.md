# Accessibility Audit — Launch Readiness (WCAG 2.2 AA)

**Date:** 2026-07-09
**Scope:** (1) React 18 + Vite dashboard AND public marketing site (`frontend/src/`), (2) embeddable chat widget (`widget/agentnexlify-widget.js`, byte-identical copy at `frontend/public/widget/agentnexlify-widget.js`)
**Method:** Static read of JSX + widget JS + `index.css`. READ-ONLY — no code changed.
**Auditor:** Accessibility specialist pass.

> **Blast-radius note:** Widget failures propagate to **every tenant's website end-customer**, not just AgentNexLiFy's own users. A keyboard/SR blocker in the widget is a blocker replicated across the entire customer base. Widget findings are weighted up accordingly.

---

## Severity counts

| Severity | Count |
|---|---|
| BLOCKER | 4 |
| HIGH | 8 |
| MEDIUM | 9 |
| LOW | 4 |
| **Total** | **25** |

**Single worst finding:** W-1 — the widget launcher bubble is a non-focusable `<div>` with a click handler and no accessible name. Keyboard-only and screen-reader users **cannot open the chat widget at all**, on every tenant site.

---

## BLOCKERS

### W-1 — Widget launcher bubble is an unfocusable, unlabeled `<div>`
- **Severity:** BLOCKER
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:921-924` (markup), `:2033-2035` (click wiring)
- **Issue:** The launch control is `<div id="anx-bubble">` with `cursor:pointer` and a `click` listener. It has no `tabindex`, no `role="button"`, no `aria-label`, and no key handler.
- **Impact:** Keyboard-only users cannot Tab to it or activate it (Enter/Space do nothing on a div). Screen-reader users get no name/role — it is invisible to AT. The entire widget (chat, lead capture, booking) is unreachable without a mouse. Blocks lead capture for disabled visitors on **every** tenant site.
- **Evidence:** `<div id="anx-bubble"> ... </div>` at line 921; wired via `document.getElementById("anx-bubble").addEventListener("click", ...)` at 2034. No `tabindex`/`role`/`keydown` anywhere for `anx-bubble`.
- **Reproduction:** Load any page with the widget. Press Tab repeatedly — focus never lands on the bubble. With a screen reader, the bubble is not announced.
- **Recommended fix:** Make it a real control: `<button id="anx-bubble" type="button" aria-label="Open chat" aria-expanded="false" aria-controls="anx-window">`. Update `aria-expanded` in `toggleWindow()`. If a `<div>` must stay, add `role="button"`, `tabindex="0"`, `aria-label`, and a `keydown` handler for Enter/Space.
- **Confidence:** High
- **WCAG 2.2:** 2.1.1 Keyboard (A), 4.1.2 Name/Role/Value (A)

### W-2 — Chat message stream is not a live region; new bot replies are never announced
- **Severity:** BLOCKER
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:944` (`<div id="anx-messages">`), `:1235-1320` (`addMessage`), `:1352-1360` (typing indicator)
- **Issue:** `#anx-messages` has no `role="log"`/`role="status"` and no `aria-live`. Assistant replies are appended as plain `<div>`s. Nothing tells AT that content changed.
- **Impact:** A screen-reader user sends a message and never hears the AI's answer — the core function of the product is silent for them. Typing indicator is also invisible/unannounced, so there's no "assistant is responding" cue.
- **Evidence:** `const container = document.getElementById("anx-messages"); ... container.appendChild(div);` (addMessage) with no live-region attributes on the container (line 944).
- **Reproduction:** With a screen reader, open chat, send a message. The assistant response is not announced.
- **Recommended fix:** On `#anx-messages` add `role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false"`. Give assistant bubbles a readable structure; consider `aria-label="Assistant"`/`"You"` per message. Announce typing via a visually-hidden `aria-live="polite"` status ("Assistant is typing…").
- **Confidence:** High
- **WCAG 2.2:** 4.1.3 Status Messages (AA), 1.3.1 Info & Relationships (A)

### W-3 — Widget forms: labels not programmatically associated + validation errors not announced
- **Severity:** BLOCKER (compound)
- **Category:** Accessibility
- **Location:** Booking form `widget/agentnexlify-widget.js:1715-1730`; offline form `:1849-1868`; error nodes `:1730/1751-1757`, `:1868/1885-1888`; chat input `:950`
- **Issue:** Every widget form field uses a detached `<label class="anx-form-label">…</label>` with no `for`/`id` link (e.g. `<label>Name *</label><input id="anx-book-name">`). Required state is conveyed only by a visual `*`. Error containers (`#anx-book-error`, `#anx-offline-error`) are toggled `display:block` with no `role="alert"`/`aria-live`, so "Name and email are required." is silent. The chat `<textarea id="anx-input">` has only a `placeholder`, no label.
- **Impact:** Screen-reader users hear an unlabeled edit field ("edit text") and cannot tell which field is which, that it's required, or why submission failed. Booking + lead capture are effectively unusable with AT. Placeholder-as-label also disappears on input for low-vision/cognitive users.
- **Evidence:** `<div class="anx-form-group"><label class="anx-form-label">Name *</label><input class="anx-form-input" id="anx-book-name" placeholder="Your name" required></div>` (1715); error shown by `errEl.style.display = "block"` with no live role (1755-1756).
- **Reproduction:** Open booking → "Your Details". Tab through fields with a screen reader — labels not announced. Submit empty — error not announced.
- **Recommended fix:** Add `for`/`id` pairs (or wrap input in the label). Add `aria-required="true"` (or rely on `required`, but announce it). Give error nodes `role="alert"`. Add `aria-invalid="true"` + `aria-describedby` pointing to the error on failed fields. Give `#anx-input` an `aria-label="Type your message"`.
- **Confidence:** High
- **WCAG 2.2:** 1.3.1 (A), 3.3.1 Error Identification (A), 3.3.2 Labels/Instructions (A), 4.1.3 (AA)

### F-1 — Clickable `<div>`/`<span>` across dashboard are not keyboard operable
- **Severity:** BLOCKER (systemic)
- **Category:** Accessibility
- **Location:** 80 `<div>`/`<span>` with `onClick` across 27 files; only 20 keyboard-handler/`role="button"` occurrences across 13 files. Hotspots: `pages/SocialMediaPage.jsx` (10), `pages/DocumentsPage.jsx` (8), `pages/Calendar.jsx` (7), `pages/Dashboard/QuickActions.jsx` (5), `pages/PipelinePage.jsx` (5), `components/Sidebar.jsx` (3)
- **Issue:** Many interactive controls are `onClick` on a non-focusable element with no `role="button"`, `tabIndex={0}`, or `onKeyDown`.
- **Impact:** Keyboard-only and switch users cannot reach or activate these actions; screen readers announce them as static text. Given the ratio (80 clickable divs vs 20 key handlers), most are inoperable without a mouse.
- **Evidence:** Grep — 80 `<div|span … onClick` matches; `onKeyDown|onKeyPress|onKeyUp|tabIndex|role="button"` = 20 matches. `InvoiceFormModal.jsx` returned zero role/tabIndex/keydown.
- **Reproduction:** Tab through the dashboard; interactive cards/rows/icons in the listed files are skipped or unusable.
- **Recommended fix:** Convert to `<button type="button">` (preferred). Where markup must stay a div, add `role="button" tabIndex={0}` plus an `onKeyDown` handling Enter/Space. Audit each of the 27 files; prioritize Sidebar nav and Dashboard actions.
- **Confidence:** High (systemic; per-site confirmation recommended)
- **WCAG 2.2:** 2.1.1 Keyboard (A), 4.1.2 (A)

---

## HIGH

### F-2 — Form labels not associated site-wide (login, signup, settings, wizard)
- **Severity:** HIGH (systemic)
- **Category:** Accessibility
- **Location:** 227 `<label>` elements across 40 files, but only 11 `htmlFor=` across 5 files (`WidgetPage`, `BusinessPageSettings`, `DemoExperience`, `settings/shared`, `Contact`). Confirmed unassociated: `components/LoginPage.jsx:104-125`.
- **Issue:** ~95% of labels are visually adjacent but not linked to inputs via `htmlFor`/`id` (and inputs aren't wrapped by the label). Example: `<label>Email</label><input type="email" …>` with no id.
- **Impact:** Screen readers announce "edit text" with no name; clicking the label doesn't focus the field (larger hit target lost). Affects auth, signup, settings, onboarding wizard.
- **Evidence:** `<div className="login-field"><label>Email</label><input type="email" className="login-input" …/></div>` (LoginPage 104-113). htmlFor count 11 ≪ label count 227.
- **Reproduction:** Screen-reader the login form; fields announce without names.
- **Recommended fix:** Add `htmlFor`/`id` to every label/input pair, or wrap the `<input>` inside `<label>`. Cheapest global fix: wrap.
- **Confidence:** High
- **WCAG 2.2:** 1.3.1 (A), 3.3.2 (A), 4.1.2 (A)

### F-3 — Modals/drawers lack dialog semantics, focus trap, and focus restoration
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** `components/invoices/InvoiceFormModal.jsx`, `InvoiceDetailModal.jsx`, `InvoiceSendModal.jsx`, `pages/Dashboard/LeadDetailDrawer.jsx`, `components/UpgradePrompt.jsx`. Only `components/os/DemoTour.jsx` and `components/CookieConsent.jsx` use `role="dialog"`.
- **Issue:** Modal components render without `role="dialog"`/`aria-modal="true"`, no `aria-labelledby`, no focus trap, no Escape-to-close, and no return of focus to the trigger on close (`InvoiceFormModal.jsx` has no `role`/`tabIndex`/`useEffect`).
- **Impact:** Keyboard focus stays behind the modal (users tab into the obscured page); screen readers don't announce a dialog; no Escape; focus is lost on close. Confusing/trapping for AT users.
- **Evidence:** Grep of `InvoiceFormModal.jsx` for `role=|tabIndex|onKeyDown|useEffect` → no matches. `role="dialog"` present in only 2 of the modal-bearing files.
- **Reproduction:** Open the invoice form modal; Tab past the last field — focus escapes to the page underneath. Press Escape — nothing.
- **Recommended fix:** Add `role="dialog" aria-modal="true" aria-labelledby="<title-id>"`; on open, move focus into the dialog and trap Tab within it; Escape closes; on close, restore focus to the invoking control. Consider a shared `<Modal>` primitive.
- **Confidence:** High
- **WCAG 2.2:** 2.1.2 No Keyboard Trap (A, inverse — focus must be contained *and* escapable), 2.4.3 Focus Order (A), 4.1.2 (A); 2.4.11 Focus Not Obscured (AA)

### F-4 — Login/auth errors are not announced (no live region)
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** `components/LoginPage.jsx:126` (`<div className="login-error">{error}</div>`); same pattern in `pages/SignupPage.jsx`, `ForgotPasswordPage.jsx`, `ResetPasswordPage.jsx`, `ClientLoginPage.jsx`
- **Issue:** Validation/auth error text renders in a plain `<div>` with no `role="alert"`/`aria-live`. "Invalid credentials" / "session expired" appear silently.
- **Impact:** Screen-reader users submit, get no feedback, and don't know why login failed. Error recovery is blocked.
- **Evidence:** `{error && <div className="login-error">{error}</div>}` (LoginPage 126).
- **Reproduction:** Submit wrong password with a screen reader — error not announced.
- **Recommended fix:** Add `role="alert"` (assertive) or `aria-live="polite"` to the error container so it announces on appearance.
- **Confidence:** High
- **WCAG 2.2:** 4.1.3 Status Messages (AA), 3.3.1 (A)

### F-5 — No visible focus indicator system; inputs strip `outline` and replace with a weak border-color-only cue
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** `frontend/src/index.css` — 19 `outline: none` declarations; every input/select/textarea `:focus` rule replaces the native outline with only `border-color: var(--accent)` (e.g. `:775/779`, `:1549/1553`, `:1593/1596`, `:2380`, `:2414`, `:2468`, `:2509`, `:2938-2942`). Zero `:focus-visible` rules anywhere in `frontend/src`.
- **Issue:** The native focus ring is removed and replaced by a 1px border-color swap. A border-color change alone is a low-visibility focus indicator and can fail the 3:1 non-text-contrast/change requirement; there is no consistent `:focus-visible` treatment, and custom buttons/links have no bespoke focus style (rely on UA default, which is inconsistent once other resets apply).
- **Impact:** Keyboard users struggle to see where focus is, especially on selects where only the border tints. Low-vision users lose the field boundary.
- **Evidence:** `.login-input { … outline: none; } .login-input:focus { border-color: var(--accent); }` (775-779). `:focus-visible` grep = 0 matches.
- **Reproduction:** Tab through a settings form; the focused control is only subtly re-bordered.
- **Recommended fix:** Add a global `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` and keep it on buttons/links/inputs. If removing the default outline, always pair with an equally-visible replacement meeting 3:1 against adjacent colors.
- **Confidence:** Medium-High
- **WCAG 2.2:** 2.4.7 Focus Visible (AA), 1.4.11 Non-text Contrast (AA)

### F-6 — Input purpose not identified (missing `autocomplete`) on auth/signup/contact
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** Only 3 `autoComplete=` usages in 2 files site-wide (`DemoExperience.jsx`, `settings/ProviderKeyCard.jsx`). Missing on `components/LoginPage.jsx:106-123`, `pages/SignupPage.jsx`, `Contact.jsx`, wizard forms.
- **Issue:** Email/password/name/phone fields lack `autocomplete` tokens.
- **Impact:** Users with cognitive disabilities and password managers lose autofill; violates AA 1.3.5. Also weakens password-manager UX for everyone.
- **Evidence:** LoginPage email/password inputs have no `autoComplete`. Global `autoComplete=` count = 3.
- **Reproduction:** Inspect login inputs — no `autocomplete`.
- **Recommended fix:** `autoComplete="username"`/`"email"` on email, `"current-password"` on login password, `"new-password"` on signup password, `"name"`, `"tel"`, `"organization"` where applicable.
- **Confidence:** High
- **WCAG 2.2:** 1.3.5 Identify Input Purpose (AA)

### W-4 — Widget booking calendar exposes empty/disabled `<button>`s to keyboard + SR
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:1612-1627` (grid build), `:1636-1653` (wiring)
- **Issue:** Leading blank cells render as `<button class="anx-cal-day empty">` (focusable, empty name, no action). Past/beyond days render as `<button class="…disabled">` using CSS `pointer-events:none` but **without** the `disabled` attribute, so they remain in the tab order and are announced as actionable buttons that do nothing. There's no `aria-label` giving the full date (screen reader hears only the day number "14").
- **Impact:** Keyboard users tab through many dead/empty buttons; SR users hear unlabeled "button" repeatedly and can focus disabled dates that won't respond. Date meaning ("Monday, July 14") is lost.
- **Evidence:** `html += `<button class="anx-cal-day empty"></button>`;` (1613); disabled path adds class only, click listener bound to `:not(.disabled):not(.empty)` (1646-1647), so those buttons are focusable no-ops.
- **Reproduction:** Open booking calendar, Tab across the grid — focus lands on empty and past-date buttons.
- **Recommended fix:** Render empty cells as non-focusable `<div aria-hidden="true">`. Add the real `disabled` attribute to unavailable dates. Add `aria-label` with the full localized date to each day button. Consider a grid `role`/roving-tabindex pattern.
- **Confidence:** High
- **WCAG 2.2:** 4.1.2 (A), 2.4.3 (A), 1.1.1 Non-text Content (A)

### W-5 — Widget auto-opens after 5s and moves focus into its input unprompted
- **Severity:** HIGH
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:2088-2095` (auto-open timer), `:1386-1387` (`input.focus()` in `toggleWindow`)
- **Issue:** If not previously closed, the window auto-opens after 5s and `toggleWindow(true)` calls `input.focus()`, yanking keyboard focus off whatever the visitor was doing on the host page.
- **Impact:** A keyboard/SR user reading or filling the tenant's page is suddenly thrown into the chat textarea with no warning — disorienting context/focus change; can cause form data loss on the host page.
- **Evidence:** `setTimeout(() => { … toggleWindow(true); }, 5000)` (2089-2094); `if (input) input.focus();` (1387).
- **Reproduction:** Load a widget page, start interacting elsewhere, wait 5s — focus jumps to the widget input.
- **Recommended fix:** Do not steal focus on auto-open. Only move focus into the widget when the user explicitly opens it. On auto-open, show the panel without calling `.focus()` (or gate focus behind user action). Respect a "reduce interruptions" heuristic.
- **Confidence:** High
- **WCAG 2.2:** 3.2.1 On Focus (A), 3.2.5 Change on Request (AAA — but the unexpected focus move is A-level under 3.2.1)

---

## MEDIUM

### W-6 — No focus restoration or Escape-to-close on widget window / booking
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:1375-1401` (`toggleWindow`), init listeners `:2036-2041`
- **Issue:** On close, focus is not returned to the launcher; there is no Escape handler to close the window or back out of the booking flow.
- **Impact:** Keyboard users lose their place on close; no fast dismiss. (Not a hard trap — minimize/close buttons are reachable — hence MEDIUM.)
- **Evidence:** `win.classList.remove("open")` on close with no `bubble.focus()`; no `keydown`/Escape listener on the window.
- **Reproduction:** Open, then close via the × button — focus is dropped to `<body>`.
- **Recommended fix:** After W-1 makes the bubble focusable, call `bubble.focus()` on close. Add a `keydown` Escape handler to close the window (or step back one booking screen).
- **Confidence:** High
- **WCAG 2.2:** 2.4.3 Focus Order (A), 2.1.2 (A)

### W-7 — Icon-only controls rely on `title` (and emoji) for their accessible name
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** Header buttons `widget/agentnexlify-widget.js:935-939` (content-mode ✎, menu 🍽, booking 📅, minimize −, close ×) use `title=`; feedback buttons 👍/👎 `:1305-1306` have **no** name at all; teaser close `:918` uses `title="Dismiss"`.
- **Issue:** `title` is an unreliable accessible-name source (not surfaced by all AT, invisible to touch/keyboard). The 👍/👎 feedback buttons expose only the emoji glyph ("thumbs up sign") as their name.
- **Impact:** SR users get inconsistent or emoji-derived names; touch/keyboard users get no tooltip. Rating controls are ambiguous.
- **Evidence:** `<button id="anx-booking-btn" title="…">&#128197;</button>` (937); `fbRow.appendChild(makeBtn("\u{1F44D}", "thumbs_up"))` with no aria (1305).
- **Recommended fix:** Add `aria-label` to every icon button ("Book appointment", "Close chat", "Rate this reply helpful"/"not helpful"). Keep `title` for sighted tooltip but don't rely on it for the name. Mark decorative emoji `aria-hidden="true"` with a text label alongside.
- **Confidence:** High
- **WCAG 2.2:** 4.1.2 (A), 1.1.1 (A)

### W-8 — Widget animations ignore `prefers-reduced-motion` (infinite pulse, typing dots, message slide, teaser fade)
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:305-308` (`anx-pulse` 2s infinite), `:462-465` (`anx-msgIn`), `:503-506` (`anx-dot` typing), `:669` (`anxFadeIn`)
- **Issue:** The launcher pulses infinitely; messages slide; typing dots bounce; no `@media (prefers-reduced-motion: reduce)` guard.
- **Impact:** Users with vestibular disorders / motion sensitivity get continuous motion they cannot disable. Infinite attention-drawing animation.
- **Evidence:** `animation: anx-pulse 2s infinite;` (268) with no reduced-motion override in the injected `<style>`.
- **Recommended fix:** Wrap non-essential animations in `@media (prefers-reduced-motion: reduce) { animation: none; transition: none; }`; at minimum kill the infinite pulse.
- **Confidence:** High
- **WCAG 2.2:** 2.3.3 Animation from Interactions (AAA); infinite pulse also touches 2.2.2 Pause/Stop/Hide (A)

### F-7 — Dashboard/marketing has zero `prefers-reduced-motion` handling
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `frontend/src` — `prefers-reduced-motion` = 0 matches. Marketing uses `.reveal` scroll-in animations (`pages/Home.jsx` `className="reveal"` throughout).
- **Issue:** No reduced-motion media query anywhere; scroll-reveal and transitions always run.
- **Impact:** Motion-sensitive users get unavoidable animation on the public site and dashboard.
- **Evidence:** Grep `prefers-reduced-motion` → 0. `Home.jsx` headings carry `reveal` class (607, 658, 694…).
- **Recommended fix:** Add a global `@media (prefers-reduced-motion: reduce)` block disabling `.reveal`/transitions/animations.
- **Confidence:** High
- **WCAG 2.2:** 2.3.3 (AAA), 2.2.2 (A) where scroll-reveal delays content

### F-8 — Marketing homepage heading order: `<h2>` appears before the page `<h1>`
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `pages/Home.jsx` — first heading is `<h2 className="section-title">` at line **317**; the `<h1>` hero is not until line **607**. Footer uses `<h4>` (941-1010) with no intervening `<h3>` section headers in that block.
- **Issue:** DOM-order heading sequence starts at h2 before any h1, and jumps levels. Screen-reader heading navigation is disordered.
- **Impact:** SR users navigating by heading hit an h2 before the h1 and encounter skipped levels; document outline is wrong.
- **Evidence:** Grep of `Home.jsx` headings: `317:<h2 …>`, then `607:<h1 …>`. Footer `<h4>` at 941/955/969/1010.
- **Reproduction:** Screen-reader heading list on the homepage — order/levels are off. (Confirm final rendered order in-browser; source order is strong evidence.)
- **Recommended fix:** Ensure exactly one `<h1>` and that it precedes section `<h2>`s; make footer column titles `<h2>`/`<h3>` consistent with the outline (or restyle without demoting level).
- **Confidence:** Medium (source order; verify rendered DOM)
- **WCAG 2.2:** 1.3.1 (A); 2.4.6 Headings & Labels (AA)

### W-9 — Low-contrast text in widget default theme
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js` — "Powered by" `#anx-powered` `rgba(255,255,255,0.2)` (660); header subtitle `rgba(255,255,255,0.45)` (374); menu item desc `rgba(255,255,255,0.4)` (637); input placeholder `rgba(255,255,255,0.25)` (536); form label `rgba(255,255,255,0.45)` (810)
- **Issue:** Multiple text colors on the `#0a0a0f` dark background fall below the 4.5:1 (normal) / 3:1 (large) thresholds. `0.2`/`0.25` opacity white ≈ ~1.5–2:1.
- **Impact:** Low-vision users can't read watermark, placeholders, menu descriptions, or field labels.
- **Evidence:** `color: rgba(255,255,255,0.2)` on `#anx-powered` over `#0d0d14` (660/656).
- **Recommended fix:** Raise opacity/lightness so text meets 4.5:1 (≈ `rgba(255,255,255,0.6)`+ depending on bg). Don't use placeholder as the only label (see W-3).
- **Confidence:** Medium (computed from opacity over stated bg; verify with a contrast tool)
- **WCAG 2.2:** 1.4.3 Contrast (Minimum) (AA)

### W-10 — Small touch targets on widget feedback / teaser-close / calendar controls
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** Feedback 👍/👎 `widget/agentnexlify-widget.js:1285-1286` (`padding:2px 4px`, 14px glyph ≈ <24px); teaser close `:918` (16px, tiny); calendar nav ‹ › `.anx-cal-nav` `:746-753` (font 18px, `padding 4px 8px`)
- **Issue:** Several targets are below the 24×24 CSS px minimum with no spacing exception.
- **Impact:** Motor-impaired and touch users mis-tap or can't hit the control.
- **Evidence:** `btn.style.cssText = "…font-size:14px;padding:2px 4px;…"` (1285-1286).
- **Recommended fix:** Ensure ≥24×24px hit area (min-width/height + padding), or provide 24px spacing. Header action buttons (30×30) already pass — match that.
- **Confidence:** Medium
- **WCAG 2.2:** 2.5.8 Target Size (Minimum) (AA)

### W-11 — Widget window is not exposed as a dialog / labeled region
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:925-957` (`#anx-window` and children)
- **Issue:** The chat panel is a bare `<div id="anx-window">` — no `role="dialog"`/`role="complementary"`, no `aria-label`, and the header `<h3>` isn't wired as its label.
- **Impact:** SR users get no landmark/name for the chat surface; hard to locate or understand as a distinct region.
- **Evidence:** `<div id="anx-window"> <div id="anx-header"> … <h3 id="anx-title">Aria</h3>` (925-930) with no role/aria on the window.
- **Recommended fix:** Add `role="dialog" aria-labelledby="anx-title"` (or `role="complementary" aria-label="Chat"`). Pair with focus management from W-1/W-6.
- **Confidence:** High
- **WCAG 2.2:** 4.1.2 (A), 1.3.1 (A)

### F-9 — Icon-only / ambiguous controls in dashboard lack accessible names (spot pattern)
- **Severity:** MEDIUM
- **Category:** Accessibility
- **Location:** `components/NotificationBell.jsx` (icon toggle), `components/Sidebar.jsx` (collapse/nav), close "×" buttons in invoice modals — low `aria-label` coverage (62 aria-* across only 26 of 90+ files)
- **Issue:** Icon buttons (bell, sidebar collapse, modal ×) frequently render a glyph with no `aria-label`.
- **Impact:** SR users hear "button" with no purpose.
- **Evidence:** aria-attribute density is low relative to interactive-element count; NotificationBell/Sidebar use `onClick` on icon elements.
- **Recommended fix:** Add `aria-label` to every icon-only control; mark decorative glyphs `aria-hidden`.
- **Confidence:** Medium (pattern-level; confirm per component)
- **WCAG 2.2:** 4.1.2 (A), 1.1.1 (A)

---

## LOW

### W-12 — Uploaded-file images: alt falls back to filename; link-only files announced generically
- **Severity:** LOW
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:1245-1258`
- **Issue:** `img.alt = attachment.filename || "Image"` (filename is weak alt); non-image files render as a link with text = filename only. Acceptable but not descriptive; `"Image"` fallback is non-informative.
- **Impact:** Minor — SR users hear a filename or generic "Image".
- **Recommended fix:** Prefer a meaningful alt when available; for the generic case use "Uploaded image: <filename>".
- **Confidence:** High
- **WCAG 2.2:** 1.1.1 (A)

### W-13 — Widget language set on JS var but not on a DOM `lang` attribute
- **Severity:** LOW
- **Category:** Accessibility
- **Location:** `widget/agentnexlify-widget.js:19-26` (lang resolution), widget root `:911-960`
- **Issue:** ES/EN strings are chosen in JS, but the injected widget container has no `lang="es"`/`lang="en"` attribute. If the tenant page `lang` differs from the widget content language, SR pronunciation is wrong.
- **Impact:** Spanish widget content read with an English speech engine (or vice-versa).
- **Recommended fix:** Set `container.lang = lang` (or on `#anx-window`).
- **Confidence:** High
- **WCAG 2.2:** 3.1.2 Language of Parts (AA)

### F-10 — `SkeletonLoader` / loading states likely not announced
- **Severity:** LOW
- **Category:** Accessibility
- **Location:** `components/SkeletonLoader.jsx`; loading spinners across pages
- **Issue:** Loading placeholders render without `role="status"`/`aria-live` or a visually-hidden "Loading…".
- **Impact:** SR users don't know content is loading; perceive an empty/broken screen.
- **Recommended fix:** Wrap loaders in `role="status"` with an sr-only "Loading…" label.
- **Confidence:** Medium
- **WCAG 2.2:** 4.1.3 (AA)

### F-11 — Consistent-help / accessible-authentication (WCAG 2.2 new criteria) — verify
- **Severity:** LOW
- **Category:** Accessibility
- **Location:** Auth: `components/LoginPage.jsx`, Google OAuth path (`:50-64`); help entry points (`pages/HelpPage.jsx`, `SupportPage.jsx`)
- **Issue:** (a) 3.3.8 Accessible Authentication — email+password with Google SSO is compliant (no cognitive-function test / no CAPTCHA seen); flagged only to confirm no CAPTCHA or memory puzzle gets added. (b) 3.2.6 Consistent Help — ensure the help/support link sits in a consistent location across pages.
- **Impact:** None currently observed; forward-looking guard.
- **Evidence:** No CAPTCHA in login; SSO present. Help pages exist but placement consistency not verified statically.
- **Recommended fix:** Keep SSO + password-manager support (see F-6); avoid CAPTCHAs lacking a non-cognitive alternative; place a help link consistently in header/footer.
- **Confidence:** Medium
- **WCAG 2.2:** 3.3.8 Accessible Authentication (AA), 3.2.6 Consistent Help (A)

---

## Quick wins (low effort, high value)

1. **Add `aria-live="polite" role="log"` to `#anx-messages`** (W-2) — one attribute, unblocks SR chat.
2. **Make `#anx-bubble` a `<button aria-label="Open chat">`** (W-1) — unblocks all keyboard users on every tenant site.
3. **Add `role="alert"` to widget error nodes and dashboard `.login-error`** (W-3, F-4).
4. **Add `aria-label` to every widget icon button + 👍/👎** (W-7).
5. **Global `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`** (F-5).
6. **Add `autocomplete` tokens to auth/signup inputs** (F-6).
7. **Add a `@media (prefers-reduced-motion: reduce)` block** to the widget `<style>` and `index.css`; kill the infinite pulse (W-8, F-7).
8. **Set `container.lang`** in the widget (W-13).

## Architectural changes (larger, plan separately)

1. **Widget dialog + focus model** — dialog role, focus trap, Escape, focus restoration, no focus-steal on auto-open (W-1/W-5/W-6/W-11). Requires re-testing byte-identical sync across `widget/` and `frontend/public/widget/` per `.claude/rules/widget-rules.md`.
2. **Shared accessible `<Modal>` primitive** for the dashboard (role=dialog, trap, Escape, restore) to fix all invoice/drawer/upgrade modals at once (F-3).
3. **Form-field convention** — wrap inputs in labels (or enforce `htmlFor`/`id`) + `aria-required` + `aria-invalid`/`aria-describedby` error wiring, applied across 40 form files and both widget forms (F-2/W-3).
4. **Interactive-element lint** — convert `onClick` divs to buttons; add an ESLint jsx-a11y ruleset (`click-events-have-key-events`, `no-static-element-interactions`, `label-has-associated-control`) to CI to stop regressions (F-1).
5. **Reduced-motion + focus-visible design tokens** in `design.md` so new components inherit them.

## Ship recommendation

**Do not ship the widget to production until W-1, W-2, and W-3 are fixed** — as-is, keyboard-only and screen-reader visitors cannot open the widget, cannot hear AI replies, and cannot complete booking/lead forms, and that failure is replicated on every tenant site. The four quick wins for those (bubble→button, messages live-region, error `role="alert"`, form label association) are small, surgical, and unblock launch; the dashboard form-label + focus-visible + modal fixes should follow immediately after but are not launch-blocking for the widget itself.
