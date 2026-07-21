---
title: "Photo-Quote — Instant Vision-Based Estimates in the Widget"
category: widget
tags: [photo-quote, widget, vision, pricing, verticals, stripe-metered, needs-human, quote-requests, opus-vision]
sources: ["specs/photo-quote_spec.md"]
created: 2026-07-21
updated: 2026-07-21
summary: "Photo-quote lets a widget visitor upload one photo of a job and get an instant price range grounded in the tenant's per-vertical pricing rules, or a needs_human handoff when the model's confidence falls below the vertical's floor. Shipped across six trades (plumbing, roofing, hvac, auto_body, landscaping, pest) with metered billing at 500/mo + $0.15 overage."
---

# Photo-Quote — Instant Vision-Based Estimates in the Widget

Photo-quote turns a single uploaded photo into a priced estimate inside the chat widget. A visitor to a contractor's site uploads a picture of the job (a leaking pipe, a dented panel, an overgrown yard), Claude vision assesses it against the tenant's own pricing rules, and the widget returns a low-high dollar range with a severity tier and a confidence score. When the model cannot price the job confidently, it returns a `needs_human` handoff instead of a guessed number — the customer is offered a three-fork choice (try another photo, book an inspection, get a text quote) rather than a misleading estimate. The moat is the same as the rest of AgentNexLiFy: quotes cite the tenant's real per-vertical pricing, not a generic model guess. This closes a gap GoHighLevel and other all-in-one platforms leave open — instant visual quoting per trade, not just a chat reply.

The request path is deliberately thin over a tested core. `POST /api/widget/photo-quote` accepts a multipart `{image, client_id, conversation_id}`, validates the image (JPEG/PNG, non-empty, 10 MB ceiling), gates on a per-conversation rate limit (5 uploads/minute) plus a hard daily per-tenant quota, and checks plan eligibility — photo-quote is a premium feature, so a non-Pro tenant receives HTTP 402. The router then loads the tenant's pricing rule, builds the vision prompt, calls the model through the shared `llm_runtime` wrapper, and persists the result to `quote_requests`. All of the actual judgment — prompt assembly, response parsing, the `needs_human` gate — lives in `backend/services/photo_quote_service.py` and `photo_quote_prompts.py`, which are unit-tested in isolation; the router is the I/O shell (multipart parse, Pillow thumbnail, dual Storage upload, DB insert) and its persistence is best-effort so a visitor always gets their quote even if a write hiccups.

The pricing model is per-vertical severity, not a flat markup. Each of the six supported trades carries a confidence floor: below it, the quote is flagged `needs_human` instead of shown. Plumbing, landscaping, and pest sit at 0.7; hvac and auto_body at 0.75; roofing at 0.8 (roof damage is the hardest to price from a single photo). A tenant can override the floor with `tenant_pricing_rules.min_confidence_threshold`; otherwise the vertical default applies, and an unknown vertical falls back to a conservative 0.75 — always erring toward human review. Platform-default price ranges are seeded per trade from HomeAdvisor/Angi 2025 national averages, each with at least six damage types mapping `minor`/`major` to `{low, high}` USD bands. That JSON is stored verbatim as `tenant_pricing_rules.rules_jsonb` and injected into the vision prompt, so every price the model returns is grounded in the tenant's configured bands rather than invented. See [[design]] for the dashboard theme conventions the Quote Requests page follows.

The data model is `client_id`-scoped (migration 108), matching the leads/conversations convention, not the `tenant_id` used elsewhere. A `quote_requests` row records `image_url`, `thumbnail_url`, `quote_low`, `quote_high`, `severity` (`minor`/`major`/`needs_human`), `confidence`, `claude_summary`, and `needs_human`. PII hygiene is built in: a retention cron purges the full-resolution image from Storage 30 days after upload (setting `full_image_purged_at` and nulling `image_url`) while keeping the thumbnail and all metadata permanently — the dashboard shows "image purged after 30d" instead of a dead link. Storage deletion failures never block the DB update, so a stuck object can never keep re-surfacing a row as a purge candidate.

Billing is metered and fail-open. A tenant's Pro plan includes 500 quotes per calendar month, tracked in `tenant_quote_usage` keyed on `(client_id, period_start)` with automatic monthly rollover. Beyond 500, each quote increments an overage counter and reports a Stripe metered usage event at $0.15, keyed with an idempotency token of `{client_id}:{quote_request_id}` so a retried request never double-charges. If the Stripe metered price is not configured, usage is still counted locally and the visitor is never blocked — the report is a safe no-op, and billing activates the moment the SKU and `STRIPE_PHOTO_QUOTE_METERED_PRICE_ID` land in production, with no code change. This mirrors the fail-open discipline used across the automation layer.

Vertical-specific gotchas drove several decisions. Roofing's high floor (0.8) reflects that shingle damage and structural sag are genuinely hard to distinguish from a phone photo at ground level; it routes to `needs_human` more often by design. Auto_body needs the model to separate cosmetic scratches (a paint-chip band) from panel replacement (an order of magnitude more), which is why the pricing bands per damage type are wide. Pest and plumbing photograph cleanly and price tightly, so they hold the lowest floor. The `needs_human` path is not a failure mode — it is the product working correctly, protecting the tenant's credibility by declining to quote what a person should quote. Higher-resolution vision input matters here: see [[vision-3x]] for why Opus-class vision at full fidelity reads dense job photos (tiny cracks, rust edges) that downsampling would lose.

The customer UX flow, end to end: the visitor uploads a photo through the widget (the upload control appears only when `photo_quote_enabled` is true for the tenant); the backend assesses and persists; the widget renders either a priced range with the tenant's disclaimer and a call-to-action, or the three-fork `needs_human` prompt. The disclaimer is mandatory — tenant-supplied via `tenant_pricing_rules.disclaimer_text`, or a platform default — because an instant estimate is not a binding quote. The tenant sees every request on the Quote Requests dashboard tab with a monthly usage meter (green under 400, yellow 400-500, red over the cap), a thumbnail that opens the full image (until it is purged), and filters for the `needs_human` flag. Tenant override options: the pricing bands (`rules_jsonb`), the confidence floor (`min_confidence_threshold`), and the disclaimer text are all per-tenant, per-vertical.

## Key Concepts

- **Severity tier** — Each quote resolves to `minor`, `major`, or `needs_human`. `minor`/`major` map to the tenant's low-high pricing bands for the detected damage type; `needs_human` zeroes the price and hands off to a person.
- **Confidence floor** — A per-vertical threshold (plumbing/landscaping/pest 0.7, hvac/auto_body 0.75, roofing 0.8) below which any quote is forced to `needs_human`. Overridable per tenant via `min_confidence_threshold`; unknown verticals fall back to 0.75.
- **rules_jsonb** — The tenant's per-vertical pricing map (`{damage_type: {minor: {low, high}, major: {low, high}}}`), stored on `tenant_pricing_rules` and injected verbatim into the vision prompt so quotes stay grounded in real bands.
- **needs_human handoff** — The deliberate decline-to-quote path. Surfaced to the customer as a three-fork choice (try another photo, book an inspection, get a text quote) rather than a guessed number.
- **Metered overage** — Usage past the 500/mo Pro allowance is billed at $0.15/quote via a Stripe metered event, idempotency-keyed on `{client_id}:{quote_request_id}`. Fail-open: unconfigured billing counts locally and never blocks the visitor.
- **30-day image retention** — Full-resolution uploads are purged from Storage 30 days after upload for PII hygiene; the thumbnail and all metadata are kept permanently.

## Relevance to AgentNexLiFy

Photo-quote is a widget-first differentiator: instant per-trade visual quoting is something GoHighLevel and the other all-in-one platforms do not offer out of the box, and it plugs directly into the existing lead-capture and booking flows — a `needs_human` handoff routes straight into the widget's inspection-booking path. It monetizes on its own metered SKU (500/mo + $0.15 overage) on top of the Pro tier, so it is both a conversion lever (a priced range converts a browsing visitor faster than "we'll call you back") and a usage-based revenue line. Operationally it reuses the platform's existing muscle: the `llm_runtime` wrapper, `client_id` tenant scoping, fail-open billing, and 30-day PII retention. The per-vertical confidence floors encode the same trust discipline as the rest of the product — decline to quote what a person should quote, rather than shipping a confident-but-wrong number that damages the tenant's credibility.

## Related Articles

- [[design]] — dashboard theme conventions the Quote Requests tab follows
- `specs/photo-quote_spec.md` — source spec
- `backend/services/photo_quote_prompts.py` — per-vertical floors + vision prompt builder
- `backend/services/photo_quote_service.py` — validation, response parse, `needs_human` gate
- `backend/services/photo_quote_usage.py` — metered billing + usage summary
- `backend/routers/widget_photo_quote.py` — the widget endpoint
- `backend/routers/photo_quote_admin.py` — the Quote Requests dashboard API
- `.claude/rules/vision-3x.md` — higher-resolution vision input
- `.claude/rules/schema-discipline.md` — `client_id` vs `tenant_id`
