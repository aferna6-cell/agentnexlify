---
name: ui-reference
description: Extract design tokens (colors, typography, spacing, components) from any URL and use as inspiration when building dashboard pages. Load when user says "use X as reference", "copy the design from", "make it look like", or editing frontend/src/pages/ and wants inspiration source.
version: 1.0.0
origin: claude
triggers:
- use as reference
- copy the design
- copy design system
- make it look like
- extract design tokens
- ui reference
- design inspiration
effort: medium
---

# UI Reference — Design Token Extraction

## When to Use
- Building a new dashboard page and want inspiration from an existing site
- Editing `frontend/src/pages/*.jsx` and need color/spacing/typography hints
- User says "use X as reference" or "copy the design from"
- Auditing visual consistency against a benchmark

## When NOT to Use
- Cloning a page 1:1 (forbidden — use as inspiration only)
- Extracting from sites behind auth without permission
- Extracting from direct competitors (e.g. GoHighLevel) — abstract patterns only
- Tenant sites (multi-tenant privacy)

# UI Reference — Extract design tokens, don't clone

Dev-time skill for inspiration extraction. Not a product feature. Never copies verbatim — extracts tokens, generates artifact, Claude builds fresh UI using artifact as style guide.

## When to load
- User says "use [site] as reference", "make it look like [site]", "copy the design from [url]"
- User building new page in `frontend/src/pages/` and hints at visual inspiration
- Before touching `design.md` to evolve our own palette

## When NOT to load
- User wants verbatim clone of a specific competitor (IP risk — refuse)
- User wants to copy logo/brand marks (refuse)
- Trivial tweak to existing page (skip skill, just edit)
- Widget visual changes (widget is byte-identical in two places — needs widget-test skill, not this one)

## Extraction pipeline

### Step 1 — Capture via installed MCP
Prefer `chrome-devtools-mcp` (stdio, ships with plugins, 91K+ installs). Fallback `playwright` MCP.

```
# Chrome DevTools MCP — open page, snapshot DOM + computed styles
chrome-devtools-mcp.navigate(url)
chrome-devtools-mcp.snapshot()               # full DOM
chrome-devtools-mcp.computedStyles(selector) # per element
```

Or Playwright:
```
playwright.browser_navigate(url)
playwright.browser_snapshot()
playwright.browser_evaluate(
  "() => Array.from(document.querySelectorAll('h1,h2,button,[role=button],nav,main,section')).slice(0,30).map(el => ({tag:el.tagName, cls:el.className, style:getComputedStyle(el)}))"
)
```

### Step 2 — Extract token set
Pull these categories (mirror our `design.md` structure):

| Category | What to extract | How |
|---|---|---|
| **Colors** | Unique background, text, accent, border colors (top 8-12 by frequency) | RGB → hex, dedupe via Euclidean distance (see snippet below) |

**Color dedupe snippet** (paste into `playwright.browser_evaluate` after page load):
```js
() => {
  const props = ['color', 'background-color', 'border-color'];
  const freq = new Map();
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    props.forEach(p => {
      const v = cs.getPropertyValue(p);
      if (v && v !== 'rgba(0, 0, 0, 0)' && v !== 'transparent') {
        freq.set(v, (freq.get(v) || 0) + 1);
      }
    });
  });
  const parse = (s) => { const m = s.match(/\d+/g); return m ? m.slice(0,3).map(Number) : null; };
  const dist = (a, b) => Math.sqrt(a.reduce((s, x, i) => s + (x - b[i]) ** 2, 0));
  const entries = [...freq.entries()].map(([c, n]) => ({ c, n, rgb: parse(c) })).filter(e => e.rgb).sort((a, b) => b.n - a.n);
  const kept = [];
  for (const e of entries) {
    if (!kept.some(k => dist(e.rgb, k.rgb) < 12)) kept.push(e);  // ~5% of sqrt(3*255^2)
    if (kept.length >= 12) break;
  }
  return kept.map(k => ({ rgb: k.rgb, hex: '#' + k.rgb.map(x => x.toString(16).padStart(2, '0')).join(''), count: k.n }));
}
```
Threshold 12 = ~5% of max RGB distance (sqrt(3·255²) ≈ 441). Tune if output too noisy/sparse.
| **Typography** | Font families, weights, sizes (h1/h2/h3/body/small), line-heights | computed `font-family`, `font-size`, `font-weight`, `line-height` on headings + body |
| **Spacing** | Padding + margin scale (4/8/12/16/24/32/…) | computed `padding`, `margin` on cards/sections/buttons |
| **Border radius** | Corner scale (0/4/8/12/16/full) | computed `border-radius` |
| **Shadows** | Elevation ladder (cards, modals, tooltips) | computed `box-shadow` |
| **Components** | Button, card, nav, input patterns | screenshot + computed styles of each |
| **Layout** | Grid/flex patterns, max-width, breakpoints | containers + CSS variables |

### Step 3 — Write artifact
Output path: `.claude/artifacts/design-references/{source-slug}-{YYYY-MM-DD}.md`

Schema (design-tokens markdown, style-dictionary compatible):

```markdown
# Design Reference — {Source Name}
Source: {url}
Extracted: {date}
Extractor: chrome-devtools-mcp | playwright
Mode: dark | light | system

## Colors
- background-primary: #xxxxxx
- background-card: #xxxxxx
- accent: #xxxxxx
- text-primary: #xxxxxx
...

## Typography
- Display: {font-family} {weight} {size}/{line-height}
- Heading: ...
- Body: ...

## Spacing scale
- 4px, 8px, 12px, 16px, 24px, 32px, 48px

## Border radius
- 0, 4, 8, 12, 16, full

## Shadows
- sm: 0 1px 2px rgba(0,0,0,0.05)
- md: 0 4px 6px rgba(0,0,0,0.1)
- lg: ...

## Component patterns
### Primary button
- bg: {color}
- text: {color}
- radius: {px}
- padding: {py}px {px}px
- hover: {bg transform}

### Card
...

## Notes
- What works well: ...
- What NOT to copy: logos, icons, brand marks, proprietary illustrations
- Compare to our `design.md`: deltas in accent hue, heading weight, card radius
```

### Step 4 — Apply as reference
When generating new `frontend/src/pages/*.jsx`:
- Read artifact first
- Use extracted tokens as inspiration BUT map to our CSS variables from `design.md`
- Cite artifact path in PR description: "UI inspired by ref: `.claude/artifacts/design-references/stripe-dashboard-2026-04-15.md`"

## AgentNexLiFy-specific rules
- Our dashboard is **dark theme** (`.claude/rules/frontend-patterns.md`) — extract from dark variant of reference if available
- Our accent is `#00bfff` (`design.md`) — note deltas, don't silently override
- Never extract from tenant sites (multi-tenant privacy) — only from public design inspiration
- Tailwind-style CSS — map tokens to CSS custom properties, not Tailwind classes directly

## Anti-patterns (auto-refuse)
- Cloning logos, icons, illustrations, photos
- Reusing copy/slogans/product names
- Copying complete page layouts 1:1 (use as inspiration, then transform)
- Extracting from sites behind auth without explicit permission
- Extracting from competitor sites for verbatim reproduction (IP risk)

## Deliverable checklist
- [ ] Artifact saved to `.claude/artifacts/design-references/`
- [ ] Source URL + date in frontmatter
- [ ] All 7 token categories present (colors, typography, spacing, radius, shadows, components, layout)
- [ ] "Notes" section lists what to copy + what NOT to copy
- [ ] PR description links artifact

## Alternatives considered
- `chipsxp/design-copier` MCP — ready-made snapshot/extract/apply tools. Skipped: third-party stdio build, 4⭐, no security audit. Skill pattern is safer + uses already-trusted MCPs.
- `BobiTenta/website-design-systems-mcp` — AI-generated README, suspicious. Skipped.
- Custom FastMCP at `backend/mcp-servers/ui-reference/` — deferred until skill pattern proves out.

## Upstream inspiration
Twitter viral post (2026-04): "extract design systems from websites so Claude Code builds clean UI" — no specific repo named. This skill is our local implementation using installed MCPs.
