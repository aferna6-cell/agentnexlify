# Plugin Routing — When to use which plugin

36 plugins installed at project scope (2026-04-12). Use these by intent, not habit. Many overlap with existing MCPs/skills — prefer the built-in skill first, fall back to plugin only when it adds capability.

## Stack-relevant (use often)

### Frontend / widget
| Intent | Plugin | Over |
|--------|--------|------|
| UI generation | `frontend-design` | default skill for new dashboard pages |
| React/Next patterns | `vercel` (skills: react-best-practices, runtime-cache, nextjs) | docs lookup |
| TS type check | `typescript-lsp` | Vite build-time errors |
| Widget debug (network/console on embedded sites) | `chrome-devtools-mcp` | Playwright when you need real Chrome session |
| E2E UI tests | `playwright` | existing `webapp-testing` skill |

### Backend / DB
| Intent | Plugin | Over |
|--------|--------|------|
| Python type check | `pyright-lsp` | grep |
| DB ops | `supabase` MCP (already wired) | plugin is redundant — prefer existing MCP |
| Code search across repo | `sourcegraph` | Grep for small, Sourcegraph for cross-service |
| Live docs | `context7` | already had MCP — same server, plugin exposes skills |

### Payments / integrations
| Intent | Plugin |
|--------|--------|
| Stripe webhook debug, subscription queries | `stripe` (skills: stripe-best-practices, stripe-projects) |
| Deployment logs, env vars, failed builds | `vercel` |
| Production errors, stack traces | `sentry` |
| Issues / PRs | `github` (we already use `gh` CLI — plugin adds skills) |

### Security / quality
| Intent | Plugin |
|--------|--------|
| Pre-merge review | `code-review` (plugin) or existing `code-reviewer` agent |
| Security scan | `security-guidance` + existing `security-audit` skill |
| Supply chain | trailofbits `supply-chain-risk-auditor` (already installed) |

## Low-priority for AgentNexLiFy (off-stack)

Keep installed but don't invoke unless context demands:
- `rust-analyzer-lsp`, `ruby-lsp` — no Rust/Ruby in codebase
- `deploy-on-aws` — we use Railway + Vercel
- `data-engineering`, `data` — no Airflow/DBT pipeline
- `amplitude` — no product analytics yet
- `mintlify` — no public docs site
- `ralph-loop` — `autopilot-loop` skill already covers autonomous issue loop
- `firecrawl` — `agent-browser` via Bash is the sanctioned web tool
- `feature-dev` — `compound-engineering` skill is the project standard
- `plugin-dev` — only when authoring new plugins
- `linear` — issues live in GitHub; only use if we migrate
- `slack` — solo engineer; no team workflow yet
- `pagerduty` — no on-call rotation

## Knowledge-work plugins (partner scope)

Partners handle sales/marketing. Don't invoke from engineering sessions unless user asks:
- `sales`, `marketing`, `brand-voice` — partner tooling
- `legal` — first-pass only, never legal advice
- `finance` — budgets, forecasts
- `productivity` — meetings, tasks

## Disabled plugins (collision — do not enable)

These duplicate project-level MCPs or skills. Re-enabling will cause dispatch ambiguity or auth failures:

- `supabase@claude-plugins-official` — plugin registers HTTP MCP without project-ref; project `.mcp.json` has correct stdio+token
- `context7@claude-plugins-official` — duplicates project `.mcp.json` entry
- `playwright@claude-plugins-official` — duplicates project `.mcp.json` entry
- `frontend-design@claude-plugins-official` — same skill name as `.claude/skills/frontend-design/`; project copy is the source of truth

## Conflict resolution

When plugin skill + existing project skill overlap:
1. **Project skill wins** for AgentNexLiFy-specific patterns (widget rules, client_id, schema-discipline)
2. **Plugin skill wins** for generic vendor patterns (Stripe webhook sig verify, Vercel env precedence, Next.js 15 migration)
3. **Tie → ask** if unsure which to follow

## Context cost

36 plugins = non-trivial system prompt bloat. If a session feels slow, disable unused ones:
```
claude plugin disable <name>
```
Candidates to disable first: `rust-analyzer-lsp`, `ruby-lsp`, `deploy-on-aws`, `data-engineering`, `amplitude`, `mintlify`, `ralph-loop`, `firecrawl`, `feature-dev`, `linear`, `slack`, `pagerduty`, `legal`, `finance`, `human-resources`, `productivity`, `marketing`, `sales`, `brand-voice`.

Enable only what the session needs:
```
claude plugin enable <name>
```

## Install source of truth

`~/.claude/plugins/installed_plugins.json` — scope is `project` (tied to /home/aidan/agentnexlify).

Browse catalog: `claude plugin marketplace list` → `claude plugin list`.
