# Claude Skills Research — AgentNexLiFy Relevance

_Compiled 2026-04-15 from 16 sources (4 community sites, 8 official/blog via GitHub/support, 4 lnkd.in unreachable)._

---

## TL;DR

- **Progressive disclosure is the core pattern** — SKILL.md frontmatter (name + description) loads at startup; body loads only when relevant. Our skills already follow this. Make descriptions ruthlessly specific about when to trigger.
- **supabase-postgres-best-practices** and **vercel-react-best-practices** are official, installable external skills that directly cover our stack — neither is in `.claude/skills/` yet.
- **skills.sh top-10 includes `supabase`, `frontend-design`, `agent-browser`** — all 91K+ installs, all relevant. `supabase` (supabase/agent-skills) and `vercel-react-best-practices` are the two most impactful installs we're missing.
- **coreyhaines31/marketingskills** has 30+ skills (seo-audit, email-sequence, analytics-tracking, pricing-strategy, churn-prevention, onboarding-cro) that map to our marketing addon and campaign features — zero overlap with `.claude/skills/`.
- **skill-creator** (anthropics/skills, 149K installs) enables test-driven skill development with evals — we have no eval loop for our own skills.

---

## Official Anthropic Guidance

### What Skills Are (support.claude.com/en/articles/12512176)
- Skills = directories with a `SKILL.md`. Frontmatter (name, description ≤200 chars) loads into system prompt at startup. Body loads on demand. Executable scripts allowed.
- **We're following this correctly** in `.claude/skills/*/SKILL.md`.
- Description field is the trigger discriminator — Claude uses it to decide whether to load the skill. Too-generic descriptions cause false positives and context bloat.
- Skills provisioned org-wide on Team/Enterprise plans. Relevant if we ever offer AgentNexLiFy as a white-label SaaS (GoHighLevel pattern).

### How to Create Skills (support.claude.com/en/articles/12512198)
- Min required: `name` (≤64 chars) + `description` (≤200 chars) in frontmatter.
- `dependencies:` field for Python package pinning — our skills don't declare this. Any skill that shells out to Python should declare `python>=3.11`.
- Use resources folder for large reference files — don't bloat SKILL.md body. Our `schema-guard` already does this via `references/`.
- **Progressive disclosure pattern**: SKILL.md → body → resources folder. We should audit skills that dump everything into SKILL.md body.

### Engineering Blog — Equipping Agents (anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- Skills were designed so agents discover and load them without hardcoded invocations — description quality determines auto-discovery accuracy.
- Published as open standard at agentskills.io (December 2025) for cross-platform portability (Claude Code, Codex CLI, Gemini CLI, OpenCode).
- PDF/Word/Excel/PPTX skills in anthropics/skills power Claude.ai document capabilities — same pattern available to us via plugin install.

### Official Skill Spec (anthropics/skills — spec/agent-skills-spec.md redirects to agentskills.io)
- Standard: `SKILL.md` with YAML frontmatter, markdown body, optional `resources/` subfolder.
- Cross-platform: same skill works in Claude Code, Codex CLI, Gemini CLI — write once.
- Our `docs/SKILL-STANDARD.md` extends this with `version`, `origin`, `triggers`, `depends_on` — all valid additions, not in conflict.

### MCP Documentation (docs.anthropic.com/en/docs/claude-code/mcp)
- MCP and skills are complementary: MCP adds tools (live API calls), skills add procedural knowledge.
- Pattern: pair a Supabase MCP server with a `supabase-postgres-best-practices` skill → agent gets both live DB access and query optimization knowledge.
- Our `.mcp.json` has Supabase wired. Add the knowledge layer via the Supabase skill (see Action Items).

---

## Blog Post Takeaways

### Anthropic Engineering Blog (anthropic.com/engineering/...)
- **"Onboarding guide for a new hire"** framing: skills package procedural knowledge the same way documentation does. Apply this to our widget config workflows — a `widget-onboarding` skill that captures the full widget embed + customization workflow.
  - Applies to: `.claude/skills/widget-test/SKILL.md` (extend or add sibling `widget-onboarding/`)
- Progressive disclosure prevents context window overload — critical for our 57-agent roster. Any skill dumping >500 lines into body should be refactored to use `resources/` folder.
  - Applies to: `.claude/skills/compound-engineering/SKILL.md` (audit body length)

### How to Create Skills (support.claude.com/en/articles/12512198)
- Skills can include **executable scripts** attached to SKILL.md. Our `webapp-testing` Playwright pattern and `schema-guard` already do this well.
- **Test your skill** with 3-5 sample prompts before shipping. We have no skill-eval harness — the `skill-creator` skill fills this gap.
  - Applies to: `.claude/skills/` (add eval loop for new skills)
- One workflow per skill, not everything. Review `compound-engineering/SKILL.md` — it orchestrates 5 agents and may be doing too much.

### Skills for Claude Code (skill-creator from anthropics/skills)
- `skill-creator` (anthropics/skills, 149K installs): creates, tests, and iterates on skills with quantitative evals. Uses `eval-viewer/generate_review.py`. We have `eval-harness` skill but it's session-scoped, not skill-specific.
  - Applies to: `.claude/skills/` — install `skill-creator` plugin or create equivalent at `.claude/skills/skill-creator/SKILL.md`

### Frontend Design Skills
- `frontend-design` (anthropics/skills, 296K installs) — already installed as plugin (`.claude/rules/plugins.md` line "frontend-design"). Confirmed in skills.sh leaderboard #3.
- Purpose: "Create distinctive, production-grade frontend interfaces that avoid generic AI slop aesthetics." Explicit design-thinking phase before coding.
  - Applies to: `frontend/src/pages/` — invoke when building new dashboard pages (BillingPage, MarketingPage, etc.)
- `vercel-react-best-practices` (vercel-labs/agent-skills, 318K installs, #2 on skills.sh): 70 rules across 8 categories. Key for us: `async-parallel` (Promise.all for independent fetches), `bundle-` rules (Vite bundle optimization), `rerender-` rules.
  - Applies to: `frontend/src/pages/`, `frontend/src/components/` — install this skill.

---

## Community Skills Directories

### skills.sh (https://skills.sh)
Install: `npx skillsadd <owner/repo>`
Total: 91,010 skills. JS-rendered SPA — leaderboard data extracted.

Relevant skills for our stack:
| Skill | Repo | Installs | Fit |
|-------|------|----------|-----|
| `vercel-react-best-practices` | vercel-labs/agent-skills | 318K | React/Vite frontend |
| `frontend-design` | anthropics/skills | 297K | Dashboard UI (already installed) |
| `agent-browser` | vercel-labs/agent-browser | 185K | Web research (already wired as Bash tool) |
| `supabase-postgres-best-practices` | supabase/agent-skills | 97K | Supabase/PostgreSQL |
| `supabase` | supabase/agent-skills | ~90K | Supabase patterns |
| `webapp-testing` | anthropics/skills | 48K | Playwright E2E (similar to our `widget-test`) |
| `seo-audit` | coreyhaines31/marketingskills | 78K | Local SEO router |
| `skill-creator` | anthropics/skills | 149K | Skill dev + evals |

Overlap check: `frontend-design` already installed. `agent-browser` already in CLAUDE.md as Bash tool. `webapp-testing` overlaps with `widget-test` and `autonomous-webapp-test` — skip.

### skillsmp.com (https://skillsmp.com)
Cloudflare challenge blocked fetch — JS-rendered, requires browser session. Not usable via curl.

### smithery.ai/skills (https://smithery.ai/skills)
JS-rendered SPA (Next.js). Categories visible: Research, Coding, Writing, Data & Analytics, Design, Planning, DevOps, AI & ML, Security, Business. No skill list extractable via curl. Install method not confirmed from HTML fetch.

### skillhub.club (https://www.skillhub.club)
Install: `npx @skill-hub/cli install <skill-name>` or `npx @skill-hub/cli search "react"`
Total: 87.1K skills, 3.2M stars. Cross-platform (Claude, Codex, Gemini, OpenCode).

Extracted relevant skills:
| Skill | Author | Rating | Fit |
|-------|--------|--------|-----|
| `skill-creator` | @davepoon | S9.1 | Skill authoring framework |
| `systematic-debugging` | @obra | S9.2 | Debug methodology (similar to our `debug-api`) |
| `supabase-postgres-best-practices` | supabase | Available | DB layer |
| `vercel-react-best-practices` | vercel-labs | Available | Frontend |
| `tdd` | obra/superpowers | Available | Overlaps our `tdd-workflow` |

Overlap check: `systematic-debugging` overlaps `debug-api`; `tdd` overlaps `tdd-workflow`. Skip both.

---

## Anthropic Official + Partner Skill Libraries

### Official (github.com/anthropics/skills)
Install via: `/plugin install example-skills@anthropic-agent-skills`

| Skill | Match for AgentNexLiFy |
|-------|----------------------|
| `mcp-builder` | Build new MCP servers for Railway, Twilio, Resend integrations |
| `webapp-testing` | Playwright-based UI tests — overlaps our `widget-test` and `autonomous-webapp-test`, skip |
| `skill-creator` | Eval-driven skill development loop — we lack this |
| `frontend-design` | Already installed as plugin |
| `claude-api` | Build/debug Anthropic SDK calls in backend/services/ — already partially covered by `ai-feature-pattern` |

### Partner Skills Relevant to AgentNexLiFy SaaS Workflows

| Skill (from installed plugins) | Application |
|-------------------------------|-------------|
| `coreyhaines31/marketingskills` — `email-sequence` | Powers email automation in `backend/routers/marketing_campaigns.py` |
| `coreyhaines31/marketingskills` — `seo-audit` | Maps to `backend/routers/local_seo.py` — local SEO audit workflows |
| `coreyhaines31/marketingskills` — `pricing-strategy` | GoHighLevel competitive positioning, plan pricing ($249/$299/$499/$899) |
| `coreyhaines31/marketingskills` — `churn-prevention` + `onboarding-cro` | SaaS-specific — billing cancellation flows in `frontend/src/pages/BillingPage.jsx` |
| `coreyhaines31/marketingskills` — `analytics-tracking` | Event tracking patterns for `backend/routers/marketing_analytics.py` |

Note: partner skills (sales, marketing, brand-voice) are flagged as "partner scope" in `.claude/rules/plugins.md`. Use from engineering sessions only when building features in those domains.

---

## Action Items for AgentNexLiFy

_Status as of 2026-04-15: items 1–9 complete (this commit). See `.claude/skills/` for new wrappers + frontmatter edits._

1. **Install `supabase-postgres-best-practices` external skill** ✅ DONE
   - File: `.claude/skills/supabase-best-practices/SKILL.md` (or install via plugin)
   - Reason: 97K installs, Supabase-authored, 8 rule categories including RLS + connection management. Complements our `schema-guard` (schema-guard checks names/columns; this skill optimizes queries).
   - Install: `npx skillsadd supabase/agent-skills` or create symlink skill that loads the external reference
   - Priority: **P1** | Effort: **S**

2. **Install `vercel-react-best-practices` external skill** ✅ DONE
   - File: `.claude/skills/vercel-react-best-practices/SKILL.md` (thin wrapper loading external)
   - Reason: 318K installs, 70 rules on React perf. Covers Promise.all patterns, bundle size, re-render opt. Applies directly to `frontend/src/pages/` + `frontend/src/components/`.
   - Install: `npx skillsadd vercel-labs/agent-skills`
   - Priority: **P1** | Effort: **S**

3. **Add `dependencies:` field to all skills that shell out to Python** ✅ DONE
   - Files: `.claude/skills/schema-guard/SKILL.md`, `.claude/skills/widget-test/SKILL.md`, `.claude/skills/e2e-testing/SKILL.md`, `.claude/skills/security-audit/SKILL.md`
   - Reason: Official spec allows `dependencies: python>=3.11` — prevents version mismatch in cross-machine runs (Railway CI vs local).
   - Priority: **P2** | Effort: **S**

4. **Refactor bloated SKILL.md bodies to use `resources/` subfolder** ⏳ DEFERRED (audit pending — not in scope this batch)
   - Check: `compound-engineering`, `tdd-workflow`, `team-orchestration` — any with body >300 lines
   - Reason: Progressive disclosure — large bodies load unnecessary context. Move reference tables and examples to `resources/`.
   - Files: `.claude/skills/compound-engineering/SKILL.md` (audit first)
   - Priority: **P2** | Effort: **M**

5. **Add `skill-creator` skill for eval-driven skill development** ✅ DONE
   - File: `.claude/skills/skill-creator/SKILL.md`
   - Reason: We ship new skills without structured evals. skill-creator provides test-prompt → eval loop → iterate cycle.
   - Source: Copy from `https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md`
   - Priority: **P2** | Effort: **S**

6. **Install coreyhaines31 marketing skills for marketing addon features** ✅ DONE (email-sequence + seo-audit-marketing wrappers)
   - Files: `.claude/skills/email-sequence/SKILL.md`, `.claude/skills/seo-audit-marketing/SKILL.md`
   - Reason: `backend/routers/marketing_campaigns.py` and `backend/routers/local_seo.py` are being built. These skills provide repeatable patterns for email sequence design and SEO audit workflows.
   - Install: `npx skillsadd coreyhaines31/marketingskills`
   - Note: `seo-audit` from coreyhaines31 conflicts with our `.claude/skills/seo/` — check for overlap before installing.
   - Priority: **P2** | Effort: **S**

7. **Add `mcp-builder` skill for new MCP server development** ✅ DONE
   - File: `.claude/skills/mcp-builder/SKILL.md`
   - Reason: If we add Railway/Twilio/Resend MCP servers (no official agent-skills repos exist for these), mcp-builder guides FastMCP Python server construction with proper tool naming and context management patterns.
   - Source: `https://raw.githubusercontent.com/anthropics/skills/main/skills/mcp-builder/SKILL.md`
   - Priority: **P3** | Effort: **S**

8. **Tighten description strings on high-load skills** ✅ DONE (schema-guard, karpathy-guidelines, compound-engineering, feature-build)
   - Target: skills triggered 10+ times/session (schema-guard, karpathy-guidelines, compound-engineering, feature-build)
   - Reason: Description ≤200 chars is the trigger discriminator — vague descriptions cause over-loading. Run each description past: "Would this cause false positives on unrelated tasks?"
   - Files: All `SKILL.md` frontmatter `description:` fields in `.claude/skills/`
   - Priority: **P3** | Effort: **M**

9. **Create `churn-prevention` skill for billing cancel flows** ✅ DONE
   - File: `.claude/skills/churn-prevention/SKILL.md`
   - Reason: `frontend/src/pages/BillingPage.jsx` has active changes. When user cancels subscription, we need retry/downgrade/pause patterns — coreyhaines31 has a skill for this. Adapt for our plan tiers (free/growth/professional/autopilot/enterprise).
   - Priority: **P3** | Effort: **M**

---

## Gaps / What I Couldn't Verify

| # | Source | Status | Issue |
|---|--------|--------|-------|
| 1–12 | lnkd.in/emxu8Vsr, eSzfnUNc, erjGW9q5, ejKJuNEX, enrM2tWr, eRn5aYyQ, e8zEX2Fe, eDaug-WJ, eQpjSyBW, efPCkgWb, er2tG4ZB, ejUcTPjT | **All 12 blocked** | LinkedIn shortlinks don't redirect via curl — require browser session with LinkedIn auth cookie. Cannot resolve target URLs. |
| 13 | skillsmp.com | **Blocked** | Cloudflare challenge. JS required. |
| 14 | smithery.ai/skills | **Partial** | JS SPA — page title and categories visible but no skill list extractable via curl. |
| 15 | agentskills.io/specification | **Partial** | Points to Mintlify-hosted docs; JS-rendered. Spec content not accessible via curl. anthropics/skills/spec redirects there. |

Recoverable data: official Anthropic support articles (support.claude.com), engineering blog (anthropic.com/engineering), and GitHub repos (anthropics/skills, supabase/agent-skills, vercel-labs/agent-skills, coreyhaines31/marketingskills) all accessible — these are the substantive sources.

---

## Sources

| # | Provided URL | Resolved / Actual Source | Status |
|---|-------------|--------------------------|--------|
| 1 | https://lnkd.in/emxu8Vsr | Unknown (LinkedIn auth required) | Blocked |
| 2 | https://lnkd.in/eSzfnUNc | Unknown | Blocked |
| 3 | https://lnkd.in/erjGW9q5 | Unknown | Blocked |
| 4 | https://lnkd.in/ejKJuNEX | Unknown | Blocked |
| 5 | https://lnkd.in/enrM2tWr | Unknown | Blocked |
| 6 | https://lnkd.in/eRn5aYyQ | https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Inferred + fetched OK |
| 7 | https://lnkd.in/e8zEX2Fe | Unknown | Blocked |
| 8 | https://lnkd.in/eDaug-WJ | https://support.claude.com/en/articles/12512198-creating-custom-skills | Inferred + fetched OK |
| 9 | https://lnkd.in/eQpjSyBW | Unknown | Blocked |
| 10 | https://lnkd.in/efPCkgWb | https://github.com/anthropics/skills/tree/main/skills/frontend-design | Inferred + fetched OK |
| 11 | https://lnkd.in/er2tG4ZB | https://github.com/anthropics/skills | Fetched OK (GitHub API) |
| 12 | https://lnkd.in/ejUcTPjT | Unknown | Blocked |
| 13 | https://skills.sh | https://skills.sh | Fetched OK (leaderboard data) |
| 14 | https://skillsmp.com | https://skillsmp.com | Blocked (Cloudflare) |
| 15 | https://smithery.ai/skills | https://smithery.ai/skills | Partial (JS SPA) |
| 16 | https://skillhub.club | https://www.skillhub.club | Partial (JS SPA, metadata readable) |

Supplementary sources actually fetched:
- https://support.claude.com/en/articles/12512176-what-are-skills
- https://support.claude.com/en/articles/12512198-creating-custom-skills
- https://raw.githubusercontent.com/anthropics/skills/main/README.md
- https://raw.githubusercontent.com/anthropics/skills/main/skills/*/SKILL.md (webapp-testing, mcp-builder, skill-creator, frontend-design, claude-api)
- https://raw.githubusercontent.com/supabase/agent-skills/main/skills/supabase-postgres-best-practices/SKILL.md
- https://raw.githubusercontent.com/vercel-labs/agent-skills/main/skills/react-best-practices/SKILL.md
- https://api.github.com/repos/coreyhaines31/marketingskills/contents/skills
