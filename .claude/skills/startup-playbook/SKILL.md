---
name: startup-playbook
description: Compressed AgentNexLiFy-specific version of startup-skill plugin patterns. Triggers competitive audit, positioning refresh, or messaging update when the user mentions competitors, pricing changes, category drift, or new entrant threats. Use when a full competitive+positioning refresh is overdue (>90 days) or when a named competitor (GHL, Podium, Birdeye, Drillbit) makes a material move.
version: 1.0.0
---

# Startup Playbook — AgentNexLiFy Competitive + Positioning Discipline

Distilled from `startup@startup-skill` plugin (startup-competitors + startup-positioning skills) + first-pass execution 2026-04-23. Project-scoped, AgentNexLiFy-specific, grounded in our KB.

## When to fire this skill

**Fires automatically when user mentions:**
- "competitive audit", "battle card", "positioning", "market category"
- A specific competitor name (GHL, GoHighLevel, Podium, Birdeye, Drillbit, Phonely, Toma, Intercom, Drift)
- "how do we compete", "why are we different", "who do we sell against"
- Pricing experiments ("should we raise / lower / tier")
- Messaging changes ("update the home page copy", "new landing page")

**Fires on cadence:**
- Quarterly (once every 90 days) — full refresh
- After any major competitor event (pricing change, new tier, acquisition)

**Does NOT fire:**
- For customer-specific deal battlecards (use the existing battle-card files)
- For internal engineering decisions (category / rule files handle this)
- For product roadmap debates (use `write-prd` + `grill-me` instead)

---

## Pre-flight checklist (before running)

1. ✅ Check `audits/competitive/` for most recent `competitors-report.md` date
2. ✅ Check `audits/positioning/` for most recent `positioning-doc.md` date
3. ✅ If either is >90 days old, run full refresh
4. ✅ If <90 days but a named competitor changed pricing/tiers, run that competitor's battle card refresh only
5. ✅ Read `knowledge-base/wiki/competitors/` for latest KB data before starting — data may already be fresh enough to skip intake

---

## Two modes

### Mode A — Competitive Refresh
**Output files:** `audits/competitive/competitors-report.md`, `competitive-matrix.md`, `pricing-landscape.md`, `battle-cards/{competitor}.md`

**Steps:**
1. **Intake** — write `audits/competitive/intake.md` with target customer, competitive set, scope decisions
2. **Research** — consume `knowledge-base/wiki/competitors/*.md`. If KB data >60 days old, run `/kb-discover competitors` or `/kb-ingest <url>` for targeted refresh
3. **Synthesis** (writes in parallel):
   - `competitors-report.md` — executive summary, strategic opportunities/risks, moat assessment
   - `competitive-matrix.md` — feature-by-feature comparison table
   - `pricing-landscape.md` — tier analysis, value metrics, switching costs
4. **Battle cards** — one per direct competitor. Structure: snapshot, tiers, where they win, where we win, discovery questions, objection handlers, escalation signals
5. **Deliver** — link all files from `audits/competitive/README.md` (create if absent)

### Mode B — Positioning Refresh
**Output files:** `audits/positioning/positioning-doc.md`, `positioning-statement.md`, `competitive-alternatives.md`, `market-category-analysis.md`, `messaging-implications.md`

**Steps:**
1. **Intake** — write `audits/positioning/intake.md`. Cite upstream competitive audit.
2. **Dunford 5+1 analysis** (writes `positioning-doc.md`):
   - Competitive Alternatives (3 tiers including status quo)
   - Unique Attributes (filter each through TRUE × DIFFERENT × VALUABLE)
   - ⏸ **PAUSE** — confirm unique attributes with user before continuing
   - Value Themes (cluster attributes into 2-3 themes)
   - Best-Fit Customers (ICP + disqualifiers)
   - Market Category (5+ candidates, decision)
   - Trend Overlay (macro trends that amplify positioning)
3. **Positioning statements** (writes `positioning-statement.md`):
   - Moore template ("For X who Y, [Product] is Z")
   - Neumeier Onliness ("the only X that Y")
   - Elevator pitch (30 seconds)
   - Home-page hero (3 variants, one per value theme)
   - Tagline candidates
   - 10-word positioning
4. **Market category** (writes `market-category-analysis.md`):
   - Score 5-10 category candidates on buyer-language, disqualification, empty-cell, headline-fit
   - Choose winner with rationale
   - SEO / content / category-defense plan
5. **Messaging map** (writes `messaging-implications.md`):
   - Words to USE
   - Words to AVOID
   - Replace-anti-language table
   - Home-page / pricing / ad / sales-email copy blocks
   - Brand voice cross-ref to `.claude/rules/personality.md`
6. **Deliver** — link all files from `audits/positioning/README.md` (create if absent)

---

## AgentNexLiFy-specific rules

### Current positioning (as of 2026-04-23)
- **Category:** Vertical AI Chat Widget for Small Business
- **Primary tagline:** "Your hardest working employee. It answers, follows up, and sells — while you sleep."
- **ICP:** 1-3 location SMB in dental, legal, salon, med-spa, real estate, restaurant, auto, medical, tutoring, fitness
- **Pricing:** $99 Starter / $150 Growth / $250 Pro / $899 Enterprise (flat)
- **Six unique attributes:** per-tenant vertical KB, widget-first identity, transparent pricing, flat pricing, 30-second embed, no CRM migration, self-serve

### Non-negotiables (never change without explicit decision)
- **"Widget" not "chatbot"** — category language
- **"Per-tenant knowledge base"** — the core moat phrase
- **Flat pricing** — not per-location; direct anti-pattern vs Birdeye/Podium/Drillbit
- **Transparent public pricing** — no Configurator; direct anti-pattern vs Birdeye
- **Direct-to-business** — no agency reseller motion; direct anti-pattern vs GHL

### Don'ts
- ❌ Never use "chatbot" — older framing
- ❌ Never use "CRM" except in "lives next to your CRM"
- ❌ Never use marketing-fluff ("leverage", "unlock", "seamless", "best-in-class")
- ❌ Never claim voice/phone primary — that's Drillbit/Phonely
- ❌ Never position as "enterprise" — SMB-only

---

## Trigger-response templates

### When user says: "I'm thinking about raising prices"
→ Load `audits/competitive/pricing-landscape.md` + `audits/positioning/positioning-doc.md`.
→ Run stress-test pattern (see `.claude/rules/claude-usage-patterns.md` pattern 7).
→ Produce: price elasticity analysis + positioning-doc delta if category frame shifts.

### When user says: "Should we match Podium's Jerry AI Employee?"
→ Load `audits/competitive/battle-cards/podium.md`.
→ Check "Imitation moves" + "What NOT to copy" sections.
→ Run a decision-framework prompt (pattern 5) with criteria: buyer-value × positioning-fit × build-effort × copycat-signal.

### When user says: "New competitor just launched — should we care?"
→ Run `/kb-ingest <url>` for the new competitor site.
→ Generate a 1-page battle card scaffold matching our template.
→ Evaluate: does this competitor break our moat claim? Yes = positioning refresh; no = file + monitor.

### When user says: "Update the home page copy"
→ Load `audits/positioning/messaging-implications.md`.
→ Use the home-page copy map section as source.
→ Produce copy with Words-to-USE anchors; avoid Words-to-AVOID list.

---

## Quality gates (all outputs must pass)

1. ✅ Every file has a source cite to KB or parent audit
2. ✅ Every competitor claim is KB-grounded, not invented
3. ✅ Every unique-attribute claim passes TRUE × DIFFERENT × VALUABLE
4. ✅ Every piece of copy uses Words-to-USE and avoids Words-to-AVOID
5. ✅ Home-page hero variants test each of 3 value themes
6. ✅ Market category passes 5-test scorecard
7. ✅ Battle cards include discovery questions + objection handlers (not just feature comparison)
8. ✅ Status quo (contact form + email) treated as Tier C alternative — the #1 real fight

---

## Anti-patterns (don't do these)

- Never write competitive audit without KB cites — invention is banned
- Never skip the ⏸ pause in Dunford 5+1 after Unique Attributes
- Never declare a market category without the 5-test scorecard
- Never position against status quo only with "we're faster" — always tie to specific buyer pain
- Never duplicate work the KB already covers — grep before synthesizing
- Never ship positioning without running it past the Writing Tone + personality.md discipline

---

## First-run execution (2026-04-23)

Reference outputs produced by first execution of this skill:
- `audits/competitive/` — 8 files (intake, report, matrix, pricing, 4 battle cards)
- `audits/positioning/` — 6 files (intake, positioning doc, statement, alternatives, category, messaging)

Use those as templates for future refreshes. Don't rewrite from scratch — update in place.

---

## Cross-refs

- Plugin source: `~/.claude/plugins/marketplaces/startup-skill/{startup-competitors,startup-positioning}/SKILL.md`
- KB: `knowledge-base/wiki/competitors/*.md`
- Design: `design.md` (Writing Tone section)
- Voice: `.claude/rules/personality.md`
- Usage patterns: `.claude/rules/claude-usage-patterns.md` (fight-me, stress-test, compress-long-docs, decision-framework)
- Rule: `.claude/rules/prompt-library.md` — every audit adds reusable prompt components
