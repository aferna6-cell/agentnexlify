---
name: seo-audit-marketing
effort: medium
description: On-page + local SEO audit workflow for tenant business sites. Load when editing backend/routers/local_seo.py, building SEO reports for tenants, or diagnosing organic traffic issues in the marketing addon.
origin: coreyhaines31/marketingskills (adapted)
version: 1.0.0
triggers:
  - seo audit
  - tenant seo report
  - local seo
  - organic traffic issue
  - on-page audit
---

# SEO Audit — Tenant Marketing Addon

Tenant-facing SEO audit workflow for AgentNexLiFy marketing addon. Different from infra-level SEO — this is the audit we run FOR tenants on THEIR websites.

## When to Use
- Editing `backend/routers/local_seo.py`
- Building an SEO report for a specific tenant
- Diagnosing why a tenant's organic traffic dropped
- Pre-launch checklist for a new tenant site

## When NOT to Use
- AgentNexLiFy's own marketing site (use `seo-specialist` agent instead)
- Paid search / SEM (this is organic only)
- Content strategy / topic research (use `deep-research` first)

## Audit phases

1. **Crawl + inventory** — `site:example.com` count, sitemap.xml check, robots.txt sanity, indexed pages vs submitted
2. **On-page scan** — title tags (50-60 chars), meta description (140-160 chars), H1 uniqueness, image alt text, internal linking
3. **Local SEO** (critical for our SMB tenants) — Google Business Profile claim + NAP consistency, local citations (Yelp, Facebook, industry directories), review count + recency, local schema markup
4. **Technical** — Core Web Vitals (LCP <2.5s, INP <200ms, CLS <0.1), mobile usability, HTTPS, canonical tags, schema.org markup
5. **Content gap** — keywords competitors rank for that tenant doesn't (use Ahrefs/SEMrush API if subscribed, else manual SERP check)

## Local SEO priorities (our bread and butter)
SMB tenants (plumbers, salons, dentists, contractors) live or die on:
- **Google Business Profile completeness** — hours, photos, services, Q&A
- **NAP consistency** — Name/Address/Phone identical across 20+ directories
- **Review velocity + response rate** — aim for 4+ new reviews/month, response to 100% within 48hr
- **Local schema** — LocalBusiness + Service + Review schema.org JSON-LD on homepage
- **Location pages** — one page per service area (even if single location, target nearby city names)

## AgentNexLiFy hooks
- Endpoint: `backend/routers/local_seo.py::audit_tenant_site(tenant_id)` → returns SEO report
- Storage: `seo_audits` table with `tenant_id`, `audit_date`, `scores`, `recommendations` JSONB
- Schedule: weekly cron via `scripts/automation/` or `backend/routers/automation_rules.py`
- Report delivery: email via existing `email-sequence` skill pattern or dashboard view

## Deliverable template
```
Tenant: [name]
Audit date: [YYYY-MM-DD]
Overall score: [0-100]

### Critical (fix this week)
- [ ] Missing HTTPS
- [ ] GBP not claimed
- [ ] Review response rate <50%

### High (fix this month)
- [ ] Title tags on 12 pages >60 chars
- [ ] 3 location pages missing

### Medium (fix this quarter)
- [ ] 8 images missing alt text
- [ ] No FAQ schema

### Opportunities
- Keyword `emergency plumber [city]` — competitor X ranks, tenant doesn't
```

## Tools / APIs we might integrate
- Google Search Console API (tenant OAuth, read-only)
- Google My Business API (for GBP audit)
- Lighthouse CI (Core Web Vitals)
- Bing Webmaster (optional)
- AccuRanker or SerpAPI (rank tracking)

## Anti-patterns
- Don't recommend keyword stuffing
- Don't buy backlinks (Google penalty risk)
- Don't over-optimize for exact-match anchors (looks manipulative)
- Don't promise rankings — promise correct fundamentals

## Full upstream reference
coreyhaines31/marketingskills — seo-audit SKILL. Note: conflicts with our `.claude/skills/seo/` symlink file (infra-level SEO, not a skill) — this skill is the marketing-addon SEO workflow. Install upstream:
```
npx skillsadd coreyhaines31/marketingskills
```
