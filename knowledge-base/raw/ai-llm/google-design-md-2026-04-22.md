---
source: user-relayed announcement
captured_at: 2026-04-22
category: ai-llm
topic: design systems, AI-consumable specs, portable tokens
related: tenant-widget-theming, onboarding-v2
---

# Google DESIGN.md — Plain-Text Design System as AI Contract

## What it is

Google released `DESIGN.md` — a plain-text markdown file that encodes a design system as:

1. **YAML frontmatter/blocks** — precise tokens (colors, typography, spacing, radii)
2. **Natural-language body** — intent and rationale for each decision

Example structure:
```markdown
---
tokens:
  color:
    primary: "#2D5F3F"  # deep green — authority
    background: "#F5EFE4"  # warm beige — softness
  typography:
    heading: "Inter 700"
    body: "Inter 400"
  spacing:
    sm: 8
    md: 16
  radius:
    button: 6
---

# Intent

The primary green conveys authority and trust without the corporate sterility
of navy. Use for primary CTAs and brand anchors. Do NOT use for error states
or destructive actions — those stay red.

The warm beige background softens the interface vs pure white — reduces
scanning fatigue on dense data views.
```

## Why this is a big deal

- **Portable** — any AI agent (Claude, Cursor, Stitch, future Agent-X) consumes same file
- **Version-controllable** — lives in git, diff-able, reviewable
- **Machine + human readable** — single source of truth for both
- **WCAG-aware** — Google's Agent runs accessibility linter on the tokens, auto-suggests fixes
- **Not tool-locked** — escapes Figma + Tailwind config + designer-brain fragmentation

## Live demo (David East, Google)

- Agent generated a button → contrast linter flagged 1.0:1 ratio → Agent auto-fixed to compliant color
- File was handed to multiple agents with identical results
- Design system no longer "locked in Figma"

## Counterintuitive claim worth testing

> "The stricter you write the rules, the more creative the AI gets."

Clear boundaries → AI innovates boldly inside them without breaking interface.
Vague requirements → AI defaults to safe mush.

If true, this generalizes beyond design — applies to any AI agent spec (API contracts, prompt templates, widget config).

## Relevance to AgentNexLiFy

See `specs/design-md-tenant-theming_spec.md` for full analysis. Summary:

**High value:** tenant widget theming — every tenant needs brand-perfect widget on their site. Current form-based config is shallow, no accessibility gate, not portable. DESIGN.md-per-tenant solves all three.

**High value:** tenant onboarding — "paste your design file OR we'll extract from your site" → 10s widget preview. Differentiator vs GoHighLevel's form-based branding.

**Medium value:** tenant landing pages (we generate them via `seo-audit-marketing`). One DESIGN.md per tenant → consistent rendering across widget + pages + emails.

**Low value:** internal dashboard. 1 product, solo dev, `.claude/rules/frontend-patterns.md` already serves.

## Trigger to adopt

- Park spec until >20 paying tenants OR first brand-perfect request OR post-onboarding-v2 phase 1
- Build alongside onboarding-v2 phase 2 to reuse `ui-reference` token extraction

## Pattern generalization

DESIGN.md is a specific case of a broader pattern already present in AgentNexLiFy:
- `.claude/skills/*/SKILL.md` — skill spec as AI contract
- `.claude/references/*.md` (new 2026-04-22) — task-scoped reference packs
- `knowledge-base/wiki/*.md` — Karpathy LLM-wiki pattern
- `CLAUDE.md` — project rules as AI contract

Google is generalizing the same pattern for design. Worth watching for additional formats (API.md? COPY.md? VOICE.md?).

## Open questions to resolve before build

- YAML vs TOML vs JSON frontmatter — what do agents parse most reliably?
- Versioning — do tenants need rollback of design changes?
- Multi-theme — one file per brand variant, or single file with theme sections?
- WCAG target — AA default, AAA opt-in?
- Widget cache strategy — parse tokens once at boot vs re-parse on hot-reload?

## Source

User-relayed announcement, 2026-04-22. David East (Google) public demo. Not yet verified via direct primary source — when official docs land, update this file with URL + any divergences from user summary.
