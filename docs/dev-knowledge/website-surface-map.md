# Website Surface Map — where the live site + widget actually live

**Created 2026-06-23.** Resolves recurring confusion about which repo folder serves
agentnexlify.com and where the live chat-widget greeting lives.

## The one fact that matters
**The live agentnexlify.com is the `frontend/` React app (Vite).** Not `landing-page-v2/`.

Proof (2026-06-23): the live page `<title>` is
`AgentNexLiFy | Your hardest working employees that don't stop`, which matches
`frontend/index.html` exactly. `landing-page-v2/index.html` has a *different* title
(`your AI service partner for small business`). The `.ai/manifest.json` directory_map
and `landing-page-v2/AGENTS.md` both confirm `frontend/` is active and
`landing-page-v2/` is legacy.

## Where things live

| Surface | Repo location | Notes |
|---|---|---|
| **Marketing site + dashboard (LIVE)** | `frontend/` | React/Vite. Entry `frontend/index.html`; homepage `frontend/src/pages/Home.jsx`. Hosted on Vercel. |
| Dashboard app host | `app.agentnexlify.com` | Same `frontend/` build; serves `/widget/agentnexlify-widget.js`. |
| Backend API | `backend/` | FastAPI on Railway (`agentnexlify-production.up.railway.app`); site proxies `/api/v1/*` there (see root + frontend `vercel.json`). |
| **Lead-capture widget (the product)** | `widget/agentnexlify-widget.js` + mirror `frontend/public/widget/agentnexlify-widget.js` | Must stay byte-identical (invariant). This is the widget embedded on the live site. |
| **Support widget** | `landing-page-v2/support-widget/agentnexlify-support-widget.js` | **LEGACY — not on the live site.** Editing it changes nothing in prod. |
| Legacy marketing | `landing-page-v2/`, `public/` | "do not touch" per `.ai/manifest.json`. Old static HTML; different title; not deployed. |

## The live chat widget + its greeting (IMPORTANT)
`frontend/index.html` (~line 73-102) embeds the **lead-capture widget**:
```html
<script src="https://app.agentnexlify.com/widget/agentnexlify-widget.js"
        data-api-key="anx_4-H8_i11vOOhbLHWQj1fxQutc3XbafG_WlMczCDm-zs"></script>
```
- That key = the **support@agentnexlify.com** enterprise tenant (`a890fba0-...`), the company account.
- **The greeting is NOT hardcoded in any JS file.** It lives in the DB:
  `widget_configs.greeting_message` for that tenant. The widget fetches config from
  `GET /api/v1/widget/config/{api_key}` (5-min per-worker cache).
- **To change the live greeting:** update `widget_configs.greeting_message` for
  api_key `anx_4-H8...` (or use the dashboard Widget settings on the support@ account).
  Goes live within ~5 min. No deploy needed. (Set to the "Nexi" greeting 2026-06-23.)
- Editing the legacy `support-widget` JS does nothing — that was a wrong-target edit,
  reverted same day.

## Vercel / deploy
- `frontend/vercel.json` + root `vercel.json` configure the live build (SPA rewrite +
  `/api/v1` → Railway). `landing-page-v2/vercel.json` is the legacy project's config.
- **CLAUDE.md note (2026-06-12) about agentnexlify.com being stuck on a stale
  `agentnexlify-site` Vercel project now looks OUTDATED** — the live title matches the
  current `frontend/` source, so `frontend/` is what's deployed. Re-verify project
  names in the Vercel dashboard before trusting that warning; update CLAUDE.md when
  confirmed.

## Rules of thumb
- Marketing copy / pages / live widget embed → `frontend/`.
- Live widget greeting / bot name / colors → DB `widget_configs` for the embedded
  api_key (support@ tenant), or the dashboard Widget page — not code.
- Never edit `landing-page-v2/` or `public/` for live changes — they're legacy.
- `.ai/manifest.json` `directory_map` is the authoritative surface map; check it first.
