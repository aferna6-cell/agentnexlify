# Live Mockup Widget — PRD (Draft)

**Status:** Draft v0.1 (DO NOT BUILD YET — needs grill-me + design review)
**Author:** Aidan (drafted by Claude after solo-agency 7-agent pattern review)
**Date:** 2026-05-06
**Phase:** Concept exploration
**Positioning:** Cold-outreach conversion lift for AgentNexLiFy sales motion + tenant lead capture
**Target tier:** All paid (free tier excluded — high compute per send)
**Ship bar:** 2x reply rate vs current cold-outreach baseline OR 1.5x widget-load → conversation rate, measured over ≥200 sends

---

## Problem statement

Cold outreach to SMBs converts at 3-8% reply rate industry-wide. The viral solo-agency pattern (`knowledge-base/raw/competitors/solo-agency-7-agent-pattern-2026-05-06.md`) claims 14% by sending a pre-built mockup of the prospect's would-be landing page. Hook: prospect sees their business in a finished form before saying yes.

Our widget is the AgentNexLiFy product surface. Same psychological hook applies — but through chat-on-their-site preview instead of a static landing-page mockup. Prospect clicks a personalized link, lands on a sandbox that mirrors their real homepage with our widget already running, branded to their colors, primed with a greeting tied to their business.

## Goals

1. Generate a per-prospect preview URL in <60s from {domain, business_name, industry}
2. Mirror prospect homepage layout + colors + logo (best-effort scrape, fall back to template)
3. Pre-load widget with industry-specific KB + greeting referencing prospect's business
4. Track: link-open, widget-load, conversation-start, message-count, lead-captured
5. Add the live preview link to outbound email/SMS as the call to action

## Non-goals

- Production-grade clone of prospect site (legal + load risk; we render a sanitized mock)
- Building landing pages for sale (that's GoHighLevel / Lovable territory — explicitly REJECTED in KB log)
- Auto-pushing to prospect's real site without consent
- Replacing existing widget embed flow for active tenants

## User stories

- **Sales / partner:** "I paste a prospect domain into the dashboard, get a shareable preview link, and ship it in a cold email."
- **Prospect:** "I click a link in an email, see my own site rendered with a chat widget already running, and either dismiss or chat with it."
- **Tenant (post-conversion):** "The widget I tried in the preview is the same widget I embed on my real site."

## Acceptance criteria

- [ ] `POST /api/preview/generate` accepts `{domain, business_name, industry}` returns `{preview_id, preview_url, expires_at}` in <60s p95
- [ ] Preview URL renders sanitized homepage clone with widget loaded, branded to scraped colors/logo
- [ ] Widget greeting references business name + industry (e.g. "Hey, this is the chat we'd add to MikesPlumbing — ask me anything")
- [ ] Preview expires 30 days after creation, returns 410 Gone
- [ ] Tracking events fire to existing analytics: `preview.opened`, `preview.widget_loaded`, `preview.conversation_started`, `preview.lead_captured`
- [ ] Dashboard page lists generated previews with funnel metrics
- [ ] Robots/scrape-block compliance: skip prospects with explicit `robots.txt` disallow on home page
- [ ] No tenant data leaks across previews (preview KB is ephemeral, scoped to preview_id)

## Open questions (need grill-me before plan)

1. Which scraper? `firecrawl_scrape` already wired vs custom `agent-browser` snapshot vs server-side Puppeteer
2. Where does sanitized HTML live? Supabase Storage vs new `previews` table vs Vercel Blob
3. How do we color/logo-extract reliably? CSS analysis vs LLM vision pass on a screenshot
4. Legal posture on rendering a clone — do we need an explicit "preview, not affiliated" banner?
5. Rate limit: per-domain (one prospect = one preview) or per-sender (partner-level cap)?
6. Industry KB selection: explicit `industry` param OR infer from scrape OR LLM classifier
7. Compute budget: target $X per preview (scrape + LLM classify + render). Need ceiling before build.
8. Does this slot into existing `/dashboard/widgets` or new `/dashboard/cold-outreach`?
9. Multi-tenant: is this a feature partners use TO SELL agentnexlify, or a feature tenants use to acquire their own customers? (Probably both — needs separation.)

## Success metrics

- Reply rate on cold outreach with preview link vs without (target: 2x lift)
- Widget-load rate on opened previews (target: >60%)
- Conversation-start rate on widget-load (target: >25%)
- Lead-capture rate on conversation-start (target: >40%, matches existing tenant rate)
- Cost per preview generated (ceiling: $0.50 — needs validation)

## Risks

- **Legal:** rendering a clone of a third-party homepage without consent. Mitigation: sanitized mock not pixel clone; "preview" banner; opt-out mechanism.
- **Compute cost:** scrape + render + classify could exceed $1/preview at scale. Need cost model before scoping.
- **Hype gap:** the 14% reply rate from the source is unverified. Reality may be 5-8% — still a lift but reframes ROI.
- **Channel ban:** sending links that load full-page mocks may flag as phishing in Gmail/Outlook. Mitigation: link to a clearly-branded `preview.agentnexlify.com/...` domain.
- **Scope creep:** drift toward "we sell landing pages too." Already REJECTED in KB log. Hold the line.

## Cross-refs

- `knowledge-base/raw/competitors/solo-agency-7-agent-pattern-2026-05-06.md` — source pattern
- `widget/agentnexlify-widget.js` — embed surface this previews
- `backend/services/widget_config.py` — widget config layer the preview reuses
- `specs/marketing-automation_spec.md` — adjacent outbound automation context
- `.claude/rules/widget-rules.md` — widget byte-identical rule (preview must respect)

## Re-evaluate when

- Source numbers get independently verified (currently treated as fiction per KB log)
- Cost model validated under $0.50/preview
- Legal review on third-party homepage cloning
- After grill-me batch on the 9 open questions above

## Decision gate

Do NOT enter `prd-to-issues` until:
1. Open questions answered (grill-me)
2. Cost model under $0.50/preview confirmed
3. Legal posture documented
4. Scope explicitly separated: partner sales tool vs tenant acquisition tool
