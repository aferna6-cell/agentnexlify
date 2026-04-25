---
title: GitHub Repo Evaluations — 2026-04-25
date: 2026-04-25
type: research
category: ai-llm
status: raw
tags: [evals, agents, tooling, decisions]
---

# GitHub Repo Evaluations — 2026-04-25

Captured for two viral "must-watch repo" lists evaluated this session. Frozen-in-time snapshot — verify before adopting since stars/maintainers/licenses can shift.

## Decision rubric (used for both lists)

For every repo, score:

1. **Stack fit** — Does it run on Anthropic-native + FastAPI + React + Supabase?
2. **Domain fit** — Does it serve SMB business automation (our wedge)?
3. **License** — MIT/Apache/MPL OK; AGPL = contagion risk; ELv2 = source-available, no hosted resale.
4. **Adoption cost** — Wholesale fork? Pattern-only? Skill-port?
5. **Compounding value** — Does it improve repeatedly or one-shot?

Decision tiers:
- ✅ **Adopt** — port pattern or wire integration
- ⚠️ **Park** — fits one specific feature; revisit when that feature is prioritized
- ❌ **Skip** — wrong stack/domain or duplicates existing work

---

## List 1 — "Future of AI agents" (5 repos)

| # | Repo | Verdict | Why |
|---|------|---------|-----|
| 1 | forrestchang/andrej-karpathy-skills | ⚠️ Mine quotes | Already have karpathy-guidelines skill. Verbatim Karpathy quotes ported as "why" anchors. Done in commit 8aa2dff. |
| 2 | NousResearch/hermes-agent | ❌ Skip | Wrong stack (Llama/Hermes ecosystem, not Anthropic-native) |
| 3 | thedotmack/claude-mem | ⚠️ Pattern-port | 3-layer progressive disclosure (search→timeline→get_observations) ported as `.claude/rules/memory-tiered-retrieval.md` in commit 8aa2dff. |
| 4 | EvoMap/evolver | ❌ Skip | Stochastic self-evolution = compliance/debugging risk for billable multi-tenant SaaS |
| 5 | lsdefine/GenericAgent | ❌ Skip | Duplicates our 57-agent registry + skill-creator workflow |

**Already shipped from this list:** Karpathy verbatim quotes + memory-tiered-retrieval rule (branch `claude-md-improvements`).

---

## List 2 — "Repos that print money" (10 repos)

| # | Repo | Verdict | Why |
|---|------|---------|-----|
| 1 | The-Swarm-Corporation/AutoHedge | ❌ Skip | Crypto trading swarm; wrong domain; needs wallet keys |
| 2 | HKUDS/Vibe-Trading | ❌ Skip | Multi-agent finance research; fintech-only |
| 3 | AgriciDaniel/claude-ads | ⚠️ Park | 7-platform ad audit + 250 checks + PDF reports (MIT). Useful only if Marketing addon prioritizes ad-audit feature. |
| 4 | nowork-studio/toprank | ✅ Adopt | Google Ads + GSC + SEO Claude plugin (MIT). Direct extension to our `seo-audit-marketing` skill. Action: 30-min skill diff. |
| 5 | Fincept-Corporation/fincept-terminal | ❌ Skip | C++/Qt finance desktop, AGPL contagion |
| 6 | cloudflare/agents | ❌ Skip | Cloudflare Durable Objects runtime; we're on Railway+Vercel; infra rebuild not justified |
| 7 | mksglu/context-mode | N/A | Already installed (verified 2026-04-24) |
| 8 | daijro/camoufox | ⚠️ Park | Stealth Firefox-fork for AI agents (MPL-2.0). Park as fallback for `kb-discover` if anti-bot walls emerge. |
| 9 | Anil-matcha/Open-Higgsfield-AI | ❌ Skip | 200-model image/video gen; no widget/dashboard need; Muapi key required |
| 10 | heygen-com/hyperframes | ❌ Skip | HTML→video render pipeline; out of scope |

---

## Top 3 to track

### 1. Toprank (✅ adopt)
- URL: https://github.com/nowork-studio/toprank
- License: MIT
- Stack: Python + Claude Code plugin + MCP servers (AdsAgent for Google Ads)
- Fit: Extends `.claude/skills/seo-audit-marketing/SKILL.md` directly
- Adds: Google Search Console MCP + Google Ads MCP we lack
- Action: Clone, diff against our skill, port skill structure (NOT MCP server install — that needs explicit perm)
- Owner: aidan

### 2. Claude Ads (⚠️ park)
- URL: https://github.com/AgriciDaniel/claude-ads
- License: MIT
- Power: 250+ audit checks, PDF reports, SaaS-vertical templates
- Trigger to revisit: Marketing addon ships ad-audit feature
- Owner: aidan

### 3. Camoufox (⚠️ park)
- URL: https://github.com/daijro/camoufox
- License: MPL-2.0
- Power: C++ stealth fingerprinting, WebRTC IP spoof, hides automation from JS inspection
- Trigger to revisit: `kb-discover` skill hits anti-bot walls on competitor scraping
- Owner: aidan

---

## Money-printing claim — calibration

Influencer framing: "print money while you sleep." Reality of these 10:

- **3 fintech tools** (1, 2, 5) — need capital + license + skill, never passive
- **4 dev tooling** (3, 4, 6, 7) — saves dev time, doesn't print money
- **3 content/automation** (8, 9, 10) — revenue requires distribution, not code

None print money on `git clone`. Same pattern as List 1: systems that COULD compound IF integrated, not turnkey revenue.

Filter rule for future viral lists: ignore "print money" framing, evaluate against rubric above.

---

## List 3 — anthropics/skills (17 skills, evaluated 2026-04-25)

Investigated as candidate for tenant-facing document generation in Marketing/Operations addon.

### License blocker (CRITICAL — re-eval gate)
Doc skills (`docx`/`pdf`/`pptx`/`xlsx`) are **Proprietary**, not Apache 2.0. `LICENSE.txt` forbids: derivative works, third-party distribution, reverse engineering, sublicense. Cannot embed in AgentNexLiFy SaaS or ship to tenants. Only allowed: invoking via Anthropic-hosted Claude API where Anthropic runs the skill server-side.

**If document generation is ever prioritized:** build on OSS libs the skills wrap — `python-docx` (MIT), `reportlab` (BSD), `python-pptx` (MIT), `openpyxl` (MIT). Same capability, no license risk, full control.

### Verdicts
| # | Skill | License | Verdict | Why |
|---|-------|---------|---------|-----|
| 1 | docx | Proprietary | ❌ Skip | License blocks SaaS resale; use python-docx if needed |
| 2 | pdf | Proprietary | ❌ Skip | License blocks SaaS resale; use reportlab/pypdf if needed |
| 3 | pptx | Proprietary | ❌ Skip | License blocks SaaS resale; use python-pptx if needed |
| 4 | xlsx | Proprietary | ❌ Skip | License blocks SaaS resale; use openpyxl if needed |
| 5 | mcp-builder | Apache 2.0 | N/A | Already in `.claude/skills/mcp-builder/` |
| 6 | skill-creator | Apache 2.0 | N/A | Already in `.claude/skills/skill-creator/` |
| 7 | frontend-design | Apache 2.0 | N/A | Already in `.claude/skills/frontend-design/` (project copy wins per `plugins.md`) |
| 8 | webapp-testing | Apache 2.0 | N/A | Equivalent in stack via Playwright MCP |
| 9 | claude-api | Apache 2.0 | N/A | Covered by `.claude/rules/opus-4-7.md` + `model-routing.md` |
| 10 | doc-coauthoring | Apache 2.0 | ⚠️ Park | Pairs with `.claude/skills/write-prd/SKILL.md` — interview→draft→iterate. Diff before porting. Trigger: PRD-quality is active sprint. |
| 11 | theme-factory | Apache 2.0 | ⚠️ Park | 10 preset themes for artifacts. Could power tenant widget themes. Trigger: widget theming sprint. |
| 12 | internal-comms | Apache 2.0 | ❌ Skip | Partner scope (sales/marketing) per `plugins.md` |
| 13 | brand-guidelines | Apache 2.0 | ❌ Skip | Anthropic-specific brand |
| 14 | algorithmic-art | Apache 2.0 | ❌ Skip | Out of scope |
| 15 | canvas-design | Apache 2.0 | ❌ Skip | Out of scope |
| 16 | slack-gif-creator | Apache 2.0 | ❌ Skip | Out of scope |
| 17 | web-artifacts-builder | Apache 2.0 | ❌ Skip | claude.ai artifact sandbox (see Critical Rule 6: no localStorage) |

### Marketing/Operations addon — original hypothesis status
**Killed by license.** Auto-invoices, KPI PPTX reports, contract drafts → cannot use anthropics/skills source. Future addon must use OSS lib path or Anthropic-hosted API path (data-residency tradeoff).

---

## Cross-refs

- `.claude/skills/karpathy-guidelines/SKILL.md` — updated with verbatim quotes (commit 8aa2dff)
- `.claude/rules/memory-tiered-retrieval.md` — new, ports claude-mem 3-layer pattern (commit 8aa2dff)
- `.claude/skills/seo-audit-marketing/SKILL.md` — Toprank target for diff
- `.claude/skills/kb-discover/SKILL.md` — Camoufox fallback owner
- `knowledge-base/raw/ai-llm/competitor-landscape-2026-04-18.md` — broader competitive context

## When to re-eval
Next viral repo list → run through rubric above first. Add row to this doc, don't start a new file. Compounds.
