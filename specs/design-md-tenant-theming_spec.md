# Feature: DESIGN.md Tenant Theming — Spec (STUB)

**Status:** parked — phase-2 of onboarding-v2
**Owner:** Aidan
**Created:** 2026-04-22
**Tenant scope:** gated (feature flag `design_md_theming`)
**Priority:** P2 (build after onboarding-v2 phase 1 ships)
**Phase:** post-onboarding-v2 phase 1
**Depends on:** `specs/onboarding-v2_spec.md`
**Related skills:** `.claude/skills/ui-reference/` (token extraction), `.claude/skills/tenant-chatbot-audit/`
**Inspired by:** Google DESIGN.md release (2026-04-22) — see `knowledge-base/raw/ai-llm/google-design-md-2026-04-22.md`

---

## 1. Executive Summary

Google shipped `DESIGN.md` — plain-text design system spec with YAML tokens + natural-language intent. Portable across agents (Claude, Cursor, Stitch). Built-in WCAG linter. Consumable by any AI agent.

AgentNexLiFy's widget embeds on arbitrary tenant domains. Brand fidelity is the #1 perceived quality signal. Current state: form-based brand fields (color picker, font dropdown) → shallow, no accessibility gate, no portability.

This feature turns tenant branding into a declarative artifact:
- Tenant provides (or we generate) a `tenant_design.md` file
- YAML tokens drive widget CSS custom properties at render
- Natural-language intent guides AI when generating copy/UI variants
- WCAG contrast linter blocks inaccessible combinations at save time
- One file, many surfaces: widget theme + tenant landing pages + email templates

## 2. Goals

1. Tenant brand captured once, rendered everywhere (widget, landing page, emails)
2. WCAG AA accessibility enforced at theme-save, not at customer-report time
3. Brand updates propagate in one file edit, not N form fields
4. Portable format — tenant can take file to any other vendor if we lose them (trust signal)
5. AI agents (including our Managed Agents) consume tokens + intent when generating copy

## 3. Non-Goals

- Not a replacement for Figma or designer workflow — complements it
- Not a real-time collaborative design tool
- Not internal dashboard theming — internal stays on `.claude/rules/frontend-patterns.md`
- Not multi-theme per tenant (one canonical brand per client; seasonal variants = phase 3)

## 4. User Stories

- **As a new tenant** I paste my brand style guide URL → AI generates `tenant_design.md` → widget preview matches my site in 10s
- **As an existing tenant** I update my primary color in `tenant_design.md` → widget across all embeds updates on next script load
- **As a tenant** I try to set white text on yellow → WCAG linter blocks save with "contrast 1.8:1, need 4.5:1" → suggests compliant adjacent color
- **As AgentNexLiFy** we consume `tenant_design.md` in the widget render, landing page builder, and email template engine — single source of truth

## 5. Acceptance Criteria

- [ ] `tenant_design.md` format spec published (YAML tokens + MD intent sections)
- [ ] `backend/services/design_parser.py` parses file → validated `DesignTokens` Pydantic model
- [ ] WCAG contrast linter runs on every token-pair at save
- [ ] Widget boot reads tokens, applies via CSS custom properties in shadow DOM
- [ ] Tenant dashboard shows live preview on file edit
- [ ] AI theme generation from URL: `POST /api/tenant/design/generate-from-url` → returns draft `tenant_design.md`
- [ ] Migration auto-generates `tenant_design.md` for existing tenants from current brand fields
- [ ] Schema: `clients.design_md TEXT` OR Supabase Storage `tenant-designs/<client_id>.md`
- [ ] Cross-tenant isolation verified — tenant A cannot read tenant B's design file

## 6. Open Questions

- Storage: column vs blob? (column simpler, blob scales + versioned)
- Versioning: keep history of design changes? (tenant rollback UX)
- Priority rules: DESIGN.md vs legacy brand fields during migration window?
- WCAG target: AA (4.5:1) vs AAA (7:1)? Default AA, AAA opt-in?
- Does widget cache parsed tokens or re-parse on every boot? (perf vs freshness)
- Does generation-from-URL reuse `ui-reference` skill or needs separate service?

## 7. Success Metrics

- Time-to-branded-widget: <2min (current: 30min form-filling + back-and-forth)
- WCAG AA compliance: 100% of saved themes (current: unmeasured, probably ~60%)
- Brand-update time: 1 file edit vs 15 form fields
- Tenant quote: "this is the first tool that actually matched my brand"

## 8. Trigger to Build

Do NOT build until ANY of:
- >20 active paying tenants, OR
- First tenant explicitly asks for brand-perfect widget, OR
- Onboarding-v2 phase 1 has shipped and we need next differentiator

Default: park this spec until 2026-06-01 and re-evaluate.

## 9. Fight-Me (steelman against building)

- 5 tenants today. None have complained about branding depth. Premature.
- WCAG linter can bolt onto existing form fields without DESIGN.md ceremony.
- Adds file-upload UX complexity for tenants who just want "pick a color."
- Portability argument weak — if tenant leaves, they leave. File doesn't retain them.
- Google's announcement is week-one hype; pattern may not survive contact with real use.

Counter: low cost to build alongside onboarding-v2 phase 2 (tokens already extracted by `ui-reference`). High cost to retrofit at 100 tenants. Defer but don't kill.

## 10. Cross-refs

- `knowledge-base/raw/ai-llm/google-design-md-2026-04-22.md` — source concept
- `specs/onboarding-v2_spec.md` — parent feature
- `.claude/skills/ui-reference/SKILL.md` — token extraction
- `.claude/references/widget_invariants.md` — widget constraints
- `.claude/references/tenant_isolation.md` — design file RLS rules
