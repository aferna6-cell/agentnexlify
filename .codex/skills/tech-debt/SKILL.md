---
name: tech-debt
effort: high
description: "Use when asked to /tech-debt, audit Agent Nexlify technical debt, or rank architecture, dead-code, security, dependency, and launch-readiness risks."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: [Read, Edit, Bash, Grep, Glob]
depends_on: [improve-architecture, dead-code-sweep]
triggers: ["/tech-debt", "tech debt", "technical debt", "debt audit", "code health", "risk backlog", "launch readiness risks"]
---

# Tech Debt

## When to Use
- The user asks for a technical debt audit or code health report.
- Agent Nexlify needs a ranked backlog before a cleanup sprint.
- Launch readiness, architecture, security, dead code, or dependency signals should be combined into one report.

## When NOT to Use
- Do not use to fix every issue automatically.
- Do not use for a narrow bug with a known failing test.
- Do not use as a substitute for security incident response or release verification.

## Read First
- Read existing audits, launch-readiness docs, recent git history, and changed files before creating new findings.
- Inspect relevant dependency, security, architecture, and test signals already present in the repo.
- Reuse newer audit evidence instead of duplicating stale backlog entries.

## Workflow
1. Run or reuse focused signals:
   - Architecture: load `improve-architecture` for structural review.
   - Dead code: load `dead-code-sweep` for candidate discovery, not automatic deletion.
   - Security: review Semgrep, secret-scan, auth, webhook, and rate-limit findings when available.
   - Launch readiness: compare against `planning/launch-readiness-rubric.md` when present.
   - Dependencies: use existing dependency audit scripts or package-manager audit output when appropriate.
2. Rank findings by severity, blast radius, confidence, and estimated effort.
3. Write or update an audit report under `audits/` when the user asks for durable output or the audit spans multiple surfaces.
4. Recommend a short execution plan for the top critical/high items. Fix only the explicitly scoped item if the user asks for implementation.

## Output Format
Return a ranked backlog table with:
- Priority
- Area
- Evidence
- Risk
- Confidence
- Estimated effort
- Recommended next action

Then list top execution steps and unresolved assumptions.

## Constraints
- Separate evidence from inference. Mark uncertain items as candidates.
- Do not delete, refactor, or upgrade packages during the audit unless the user explicitly asks.
- Do not bury blockers behind nice-to-have cleanup.
- Avoid duplicate backlog entries already covered by a newer audit unless the risk changed.

## Examples
- Use when asked: "/tech-debt"
- Use when asked: "rank the biggest Agent Nexlify debt"
- Use when asked: "what should we clean up before launch"
- Use when asked: "combine architecture and security risks into a backlog"
