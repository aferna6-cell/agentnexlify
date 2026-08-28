---
title: Tracking Inside an Embedded Widget — iframes, GTM, GA4, and postMessage
date: 2026-08-10
source_url: https://tagmaster.dev/blog/iframe-widget-tracking
fetched_at: 2026-08-26
category: growth
tags: [widget, iframe, gtm, ga4, postmessage, attribution, cross-domain, datalayer, conversion-tracking]
---

# Tracking inside an embedded widget

*hsynkvlc (TagMaster). 10 Aug 2026.*

## Why widget events go missing

- An iframe is a **separate window** with its own `dataLayer` and its own GTM container (if any). The host page's GTM cannot see clicks inside it.
- GTM Preview mode only attaches to the frame it was opened for.
- Same-origin iframes can be reached directly from the parent; **cross-origin** iframes can only communicate via `window.postMessage` — and only if the widget vendor implemented it.

## Three common failures

1. **Vendor-owned property** — the widget fires its own GA4 tag, so conversions land in the vendor's property, not the site owner's.
2. **Cross-domain payment/booking redirect** without the GA4 linker → client ID resets → session and attribution break.
3. **Duplicate GTM containers** (one in parent, one in iframe) → doubled `page_view`.

## Diagnostic checks

- Count `page_view` events without a frame filter; if it's 2× visits, you have a duplicate container.
- Interact with the widget while watching the Network tab **per frame**.
- Inspect the `tid` (GA4 measurement ID) / pixel ID on outgoing hits — whose property is it?
- Compare `cid` (client ID) before and after any domain boundary.

## Correct pattern: postMessage bridge

```js
// inside widget
window.parent.postMessage({ type: 'widget_event', event: 'lead_submitted', leadId }, '*');

// on host page
window.addEventListener('message', (e) => {
  if (e.origin !== 'https://widget.vendor.com') return;   // validate origin
  if (e.data?.type !== 'widget_event') return;
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ event: e.data.event, lead_id: e.data.leadId });
});
```

- Validate `event.origin`.
- Include an order/lead ID so downstream tags can dedupe.
- Parent-page tags then fire from the parent's dataLayer into the **site owner's** property.

## Notes for AgentNexLiFy

- Our widget (`widget/agentnexlify-widget.js`) is injected as a script, not an iframe, unless a tenant embeds it via a wrapper — but the same rule applies: tenants want `lead_submitted` / `appointment_booked` in **their** GA4/GTM.
- Add a documented `postMessage` (or direct `dataLayer.push` when same-window) event contract: `anx_lead_submitted`, `anx_appointment_booked`, `anx_chat_opened`, each with a stable ID.
- If we ever iframe the widget for CSS isolation, the postMessage bridge becomes mandatory and the origin allowlist must be per-tenant.
- Any Stripe Checkout or booking redirect off the tenant domain needs GA4 cross-domain linker guidance in the embed docs.
