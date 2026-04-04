# AgentNexLiFy Subconscious Brief

## Mission
Continuously identify and recommend improvements to the AgentNexLiFy platform — code quality, developer workflows, skill effectiveness, agent performance, customer experience, and operational efficiency.

## What Counts as Evidence
- Git commits (patterns, frequency, bug fixes vs features)
- Test results (pass rates, coverage gaps, flaky tests)
- Skill discovery reports (`docs/skill-discovery/`)
- Bug pattern docs (`docs/dev-knowledge/bug-patterns.md`)
- Daily logs (`docs/daily-logs/`)
- Agent communication outputs (`.claude/agent-comms/`)
- Knowledge base articles (`knowledge-base/wiki/`)
- Customer gaps (`docs/dev-knowledge/customer-gaps.md`)
- Schema log (`docs/dev-knowledge/schema-log.md`)

## Guardrails
- Evidence first — no recommendations without supporting data
- One improvement per recommendation — atomic, testable
- No breaking changes without explicit human approval
- Respect frozen ideas — if rejected 3+ times, stop proposing
- Each run must persist its learning for the next run
- Cost-conscious — use cheap models for volume, expensive for judgment

## Improvement Categories
1. **Code Health** — Dead code, tech debt, test coverage, security
2. **Workflow Efficiency** — Skills, hooks, automation, developer experience
3. **Agent Performance** — Prompt quality, tool usage patterns, error rates
4. **Customer Value** — Feature gaps, vertical fit, competitive positioning
5. **Operational** — Deploy pipeline, monitoring, cost optimization

## What Success Looks Like
- Each run produces exactly ONE actionable recommendation
- Recommendations compound — each builds on previous learning
- Rejected ideas teach the system what NOT to propose
- The improvement backlog stays short and high-quality
