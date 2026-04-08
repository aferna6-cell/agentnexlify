# Claude Code Platform Improvement Plan — AgentNexLiFy

**Date:** 2026-04-08  
**Audited against:** "Claude Code: The Developer's Operating System" feature inventory  
**Current state:** Extensive setup with gaps in key areas that limit throughput and quality

---

## Executive Summary

AgentNexLiFy already uses Claude Code more deeply than most teams — 38 skills, 16 agents, 18 commands, 8 hook events, 6 MCP servers. But the audit against the full Claude Code platform reveals **7 high-impact gaps** that are leaving significant developer leverage on the table. The biggest: a 539-line CLAUDE.md that degrades instruction adherence, no headless CI integration, and unused Agent Teams / Channels features that could 3-5x throughput on multi-domain tasks.

---

## Current State Scorecard

| Feature | Status | Score | Notes |
|---------|--------|-------|-------|
| CLAUDE.md | ⚠️ Bloated | 4/10 | 539 lines — 2.7x recommended max of 200 |
| CLAUDE.md Hierarchy | ⚠️ Partial | 5/10 | Project + global exist. No CLAUDE.local.md. No managed policy. |
| Rules Directory | ⚠️ Underused | 2/10 | 1 rule file. Should have 8-12 path-scoped rules. |
| Commands | ✅ Strong | 8/10 | 18 commands covering full workflow |
| Skills | ✅ Excellent | 9/10 | 38 skills across all domains |
| Agents | ✅ Excellent | 9/10 | 16 specialized agents with tool restrictions |
| Tasks | ✅ Active | 7/10 | Using Tasks for session work. Not yet cross-session. |
| Agent Teams | ❌ Unused | 0/10 | Not enabled. Missing 3-5x parallel throughput. |
| Channels | ❌ Unused | 0/10 | No Telegram/Discord. No remote control. |
| Hooks | ✅ Good | 7/10 | 8 events, 13 hooks. Missing PostCompact, ExitWorktree. |
| MCP Servers | ✅ Good | 7/10 | 6 servers. No token cost monitoring. |
| Plugins | ❌ None | 0/10 | No packaged plugins for team distribution. |
| Headless CI | ❌ None | 0/10 | No Claude in GitHub Actions. PR reviews manual. |
| Security Scanning | ⚠️ Manual | 4/10 | Skills exist but not automated in CI. |
| Voice Mode | ❌ Unused | 0/10 | Not configured. |
| Path-Scoped Rules | ⚠️ Minimal | 2/10 | 1 rule with `**/*` (global). No targeted rules. |

**Overall: 58/160 (36%)** — Strong foundation, major gaps in automation and scaling.

---

## Phase 1: CLAUDE.md Diet (Week 1) — HIGH IMPACT

### Problem
At 539 lines, the CLAUDE.md competes with Claude Code's own system prompt for attention. The article is explicit: **instruction adherence drops past ~200 lines**. Our file contains architecture docs, schema tables, tool references, and workflow docs that belong in rules files or linked documents.

### Actions

#### 1.1 Split CLAUDE.md into Rules Files
Move domain-specific sections out of CLAUDE.md into `.claude/rules/`:

```
.claude/rules/
├── codex-subagents.md          # (existing)
├── schema-discipline.md        # DB schema gotchas, column rules
├── python-fastapi.md           # Backend patterns, __future__ ban, Pydantic rules
├── frontend-patterns.md        # Dark theme, empty states, design.md reference
├── testing-standards.md        # Test-first, coverage requirements
├── security-rules.md           # RLS, tenant isolation, OWASP, secret handling
├── migration-discipline.md     # Numbered files, apply via Supabase MCP, flag in commits
├── api-conventions.md          # Endpoint patterns, Pydantic models, error responses
├── widget-rules.md             # Widget JS sync, CORS, tenant-scoped config
└── model-routing.md            # Which Claude model for which task type
```

#### 1.2 Add Path Scoping to Rules
Each rule file gets YAML frontmatter with glob patterns so it only loads when relevant:

```yaml
# schema-discipline.md
---
paths:
  - "backend/**/*.py"
  - "migrations/**/*.sql"
---

# frontend-patterns.md  
---
paths:
  - "frontend/**/*.jsx"
  - "frontend/**/*.js"
  - "frontend/**/*.css"
---

# widget-rules.md
---
paths:
  - "widget/**/*"
  - "frontend/public/widget/**/*"
---

# testing-standards.md
---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "backend/tests/**/*"
---
```

**Benefit:** Rules only load when touching matching files = less context consumed = better adherence.

#### 1.3 Trim CLAUDE.md to Core
Keep only in CLAUDE.md:
- One-paragraph project description
- Tech stack (5 lines)
- Key directories (5 lines)
- Build/test/lint commands (5 lines)
- Top 5 critical rules (the ones that burn you weekly)
- Links to workspace CONTEXT.md files
- GitNexus quick reference

**Target: under 150 lines.** Everything else lives in rules files.

#### 1.4 Create CLAUDE.local.md
For personal preferences that shouldn't affect other team members:
- Personal MCP server configs
- Editor-specific paths
- Local dev URLs
- Debug preferences

Add to `.gitignore` (should already be auto-ignored).

---

## Phase 2: Headless CI Integration (Week 2) — HIGH IMPACT

### Problem
6 GitHub Actions workflows exist but none use Claude Code. PR reviews, security scans, and test generation are all manual. The article specifically calls out: "Takes about 15 minutes to set up and catches issues before any human reviews."

### Actions

#### 2.1 Automated PR Review
New workflow: `.github/workflows/claude-pr-review.yml`

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install Claude Code
        run: npm install -g @anthropic-ai/claude-code
      - name: Review PR
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude -p "Review this PR diff for bugs, missing tests, security issues, 
          and missing tenant isolation. Be specific and actionable. 
          Flag CRITICAL issues that must be fixed before merge." \
          --output-format json > review.json
      - name: Post Review Comments
        uses: actions/github-script@v7
        with:
          script: |
            const review = require('./review.json');
            // Parse and post as PR review comments
```

**Key principle from article:** Use an independent Claude instance for review — never the same session that wrote the code.

#### 2.2 Automated Security Scan
New workflow triggered weekly and on PRs touching auth/payment files:

```yaml
name: Claude Security Scan
on:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am
  pull_request:
    paths:
      - 'backend/routers/auth.py'
      - 'backend/routers/stripe_webhooks.py'
      - 'backend/routers/billing.py'
```

The article cites <5% false positive rate with Opus 4.6 and 500+ vulnerabilities found in well-reviewed OSS. We should point it at our codebase weekly.

#### 2.3 Automated Test Generation
When a PR adds new endpoints without tests, Claude generates test stubs:

```bash
claude -p "Generate integration tests for new endpoints in this diff. 
Use existing test patterns from the codebase." --output-format json
```

---

## Phase 3: Rules Directory Buildout (Week 2) — MEDIUM IMPACT

### Problem
One rule file exists. The article describes rules as the scalable replacement for a bloated CLAUDE.md. Path scoping reduces token usage because rules only load when relevant.

### Actions

#### 3.1 Create 9 Path-Scoped Rules
(Detailed in Phase 1.1 above)

Each rule file follows the article's guidance:
- **Tell it why, not just what.** Every rule includes the incident or reason behind it.
- **Under 50 lines each.** Focused, scannable, actionable.
- **Updated constantly.** Every time Claude is corrected twice on the same thing, add a rule.

#### 3.2 Security Rules with `allowed-tools` Restriction
For security-sensitive paths, rules can restrict available tools:

```yaml
---
paths:
  - "backend/routers/auth.py"
  - "backend/routers/stripe_webhooks.py"
  - ".env*"
---
# Security-Critical Files
Never commit changes to these files without running the security-audit skill.
Never log secret values. Never bypass auth checks.
All changes require explicit user confirmation.
```

---

## Phase 4: Agent Teams (Week 3) — HIGH IMPACT

### Problem
Agent Teams shipped Feb 5 with Opus 4.6. We have 16 agents but they only run as isolated subagents. The article describes: "A task that takes one session 90 minutes finishes in 30."

### Actions

#### 4.1 Enable Agent Teams
Add to `.claude/settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

#### 4.2 Design Team Compositions
For feature work (API + Frontend + Tests):
- **Lead:** Coordinates via shared task list
- **Backend teammate:** API endpoints, Pydantic models, DB queries
- **Frontend teammate:** React components, API integration
- **QA teammate:** Integration tests, E2E tests
- All coordinate through shared Tasks with dependency tracking

For deploy prep:
- **Lead:** Orchestrates
- **Security teammate:** Vulnerability scan
- **DevOps teammate:** Build validation, env check
- **QA teammate:** Regression tests

#### 4.3 Define When NOT to Use Teams
Per the article: "Use them when parallel exploration adds real value and teammates can operate independently. For sequential tasks or same-file edits, stick to single sessions or subagents."

Rules:
- 3+ independent domains → Teams
- Same-file edits → Single session
- Sequential logic → Subagents
- Simple bug fix → Single session

---

## Phase 5: Channels Setup (Week 3) — MEDIUM IMPACT

### Problem
No remote control. Can't steer sessions from phone. The article describes: "I told it to refactor an auth flow from my phone while grabbing coffee. Came back to my desk and the PR was ready for review."

### Actions

#### 5.1 Set Up Telegram Channel
```bash
/plugin install telegram@claude-plugins-official
/telegram:configure <BOT_TOKEN>
claude --channels plugin:telegram@claude-plugins-official
```

Run in tmux to persist across terminal disconnects.

#### 5.2 Use Cases
- Monitor long-running builds/deploys from phone
- Steer overnight agent work
- Quick code questions while away from desk
- Emergency fixes from mobile

#### 5.3 Security
- Pairing locks bot to specific Telegram user ID
- Permission approvals still require terminal (safety feature)
- Don't use for destructive operations (delete, force-push) without terminal access

---

## Phase 6: Plugin Architecture (Week 4) — MEDIUM IMPACT

### Problem
No plugins. The article says: "One person builds a plugin that captures your team's code review standards... Consistent, on-brand, process-compliant output across the entire organization."

### Actions

#### 6.1 Package AgentNexLiFy Standards Plugin
Bundle our team standards into a distributable plugin:
- Code review skill + pre-commit hook + security subagent
- Tenant isolation verification hook
- Schema validation pre-query hook
- Widget sync check

This would let any developer (or partner) working on AgentNexLiFy get consistent behavior by installing one plugin.

#### 6.2 Create Vertical Industry Plugin
For onboarding new industries/verticals:
- Industry content skill
- FAQ generation skill
- Widget customization templates
- Tenant chatbot audit

---

## Phase 7: Hook Improvements (Week 4) — LOW IMPACT

### Problem
Good hook coverage (8 events, 13 entries) but missing newer hooks and some optimizations.

### Actions

#### 7.1 Add PostCompact Hook
Fires after context compaction. Log what was compressed:
```json
{
  "PostCompact": [{
    "command": "bash scripts/claude-hooks/log-compaction.sh"
  }]
}
```
Useful for debugging when context loss causes regressions.

#### 7.2 Add ExitWorktree Hook
Clean up temporary resources when leaving a worktree:
```json
{
  "ExitWorktree": [{
    "command": "bash scripts/claude-hooks/cleanup-worktree.sh"
  }]
}
```

#### 7.3 MCP Token Cost Monitoring
The article warns: "I've seen projects where a forgotten MCP connection was eating 15% of the context window every session."

Add a periodic check:
```bash
# Run /mcp periodically to check token costs
# Disconnect unused servers
```

Create a command `/mcp-audit` that reports token consumption per MCP server.

---

## Phase 8: Miscellaneous Optimizations (Ongoing)

### 8.1 Voice Mode
Enable `/voice` for hands-free code review sessions. Particularly useful when reviewing diffs on a second monitor while dictating feedback.

### 8.2 Structured Output in CI
Use `--output-format json --json-schema` for all CI Claude invocations to get machine-parseable results that can be posted as PR comments or fed into dashboards.

### 8.3 Independent Review Instances
The article emphasizes: "Always use an independent Claude instance for code review, not the same session that wrote the code."

Enforce this in our compound engineering pipeline:
- Executor agent writes code in session A
- Reviewer agent reviews in session B (fresh context, no reasoning bias)

### 8.4 Cross-Session Task Coordination
Tasks are stored in `~/.claude/tasks` and support cross-session access. Use this for:
- Long-running refactors spanning multiple sessions
- Overnight build-loop work where morning session continues from evening's task list
- Multi-developer coordination where both see the same task board

### 8.5 Skill Effort Frontmatter
New feature: skills support `effort` frontmatter to override model thinking effort. Apply to:
- Security audit skill → high effort (thorough analysis)
- Dead code sweep → medium effort (pattern matching)
- Quick formatting skills → low effort (fast execution)

---

## Implementation Priority

| Phase | Impact | Effort | Timeline | Dependencies |
|-------|--------|--------|----------|-------------|
| 1. CLAUDE.md Diet | 🔴 High | Medium | Week 1 | None |
| 2. Headless CI | 🔴 High | Medium | Week 2 | ANTHROPIC_API_KEY in GitHub Secrets |
| 3. Rules Buildout | 🟡 Medium | Low | Week 2 | Phase 1 |
| 4. Agent Teams | 🔴 High | Low | Week 3 | None |
| 5. Channels | 🟡 Medium | Low | Week 3 | Telegram bot token |
| 6. Plugins | 🟡 Medium | High | Week 4 | Phases 1-3 |
| 7. Hook Improvements | 🟢 Low | Low | Week 4 | None |
| 8. Misc Optimizations | 🟢 Low | Ongoing | Ongoing | Various |

---

## Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| CLAUDE.md line count | 539 | <150 | `wc -l CLAUDE.md` |
| Rules files | 1 | 10+ | `ls .claude/rules/` |
| Path-scoped rules | 0 | 8+ | `grep -l 'paths:' .claude/rules/*.md` |
| CI Claude integration | 0 workflows | 3 workflows | GitHub Actions count |
| Agent Teams enabled | No | Yes | Settings check |
| Channels configured | 0 | 1+ | Plugin list |
| PR review automation | Manual | Automated | Check workflow runs |
| Security scan frequency | Ad-hoc | Weekly + PR | Check workflow schedule |
| Context window efficiency | ~60% useful | ~85% useful | Token monitoring via /mcp |

---

## Risk Mitigation

1. **CLAUDE.md split breaks existing behavior** — Test each rules file extraction incrementally. Verify Claude still follows critical rules after each split. Keep CLAUDE.md backup.

2. **CI costs with headless Claude** — Start with Haiku for lightweight PR reviews. Only escalate to Sonnet/Opus for security scans. Set spend alerts.

3. **Agent Teams token consumption** — The article warns teams "consume significantly more tokens." Start with 3-teammate compositions. Monitor costs for a week before scaling to 5+.

4. **Channels security** — Telegram pairing locks to user ID. Never enable for destructive ops without terminal confirmation. Review Anthropic's safety docs before deploying.

---

## Quick Wins (Do This Week)

1. ✅ Enable Agent Teams in settings.json
2. ✅ Create `CLAUDE.local.md` template
3. ✅ Move schema discipline section from CLAUDE.md to `.claude/rules/schema-discipline.md` with path scoping
4. ✅ Add MCP token audit command (`/mcp-audit`)
5. ☐ Try `/voice` for next code review session (manual)

## Implementation Status (Updated 2026-04-08)

| Phase | Status | What Shipped |
|-------|--------|-------------|
| 1. CLAUDE.md Diet | ✅ Done | 539→99 lines. 9 rules files with path scoping. |
| 2. Headless CI | ✅ Done | PR review (Haiku) + security scan (Sonnet) workflows. Needs ANTHROPIC_API_KEY secret. |
| 3. Rules Buildout | ✅ Done | 10 rules files total (9 new + 1 existing). All path-scoped. |
| 4. Agent Teams | ✅ Done | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` enabled. |
| 5. Channels | ⏭️ Skipped | Needs Telegram bot token. |
| 6. Plugins | ⏭️ Deferred | High effort, week 4. |
| 7. Hook Improvements | ✅ Done | PostCompact + WorktreeRemove hooks added. |
| 8. Misc | ✅ Partial | MCP audit command, CLAUDE.local.md. Voice/effort frontmatter pending. |

---

*Generated from audit of Claude Code platform features against AgentNexLiFy codebase configuration.*
*Last updated: 2026-04-08*
