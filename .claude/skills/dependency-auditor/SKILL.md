---
name: dependency-auditor
description: Scan backend/requirements.txt, frontend/package.json, widget package files for outdated, vulnerable, or abandoned packages. Output prioritized fix list. Load when user says "audit dependencies", "check for vulns", "outdated packages", "npm audit", "pip audit", or before a release.
origin: inspired by ComposioHQ/awesome-claude-skills/dependency-auditor
version: 1.0.0
triggers:
  - audit dependencies
  - check for vulns
  - outdated packages
  - npm audit
  - pip audit
  - dependency security
  - abandoned packages
---

# Dependency Auditor — Security + Freshness Pass

Pairs with `trailofbits/supply-chain-risk-auditor`. Project-side runner that knows AgentNexLiFy package layout.

## When to Use
- Pre-release / pre-deploy gate
- Monthly dependency hygiene
- After a public CVE announcement matching our stack
- New tool/lib added — sanity-check first
- Build/test failure suspected to be transitive dep

## When NOT to Use
- Single-package upgrade with known good version (just bump)
- User already ran the audit this session
- Pinned version explicitly (e.g., `claude-code@2.1.98` per `.claude/rules/claude-version-pin.md`) — flag, don't bump

## Targets
| File | Tool | Output |
|---|---|---|
| `backend/requirements.txt` | `pip-audit`, `pip list --outdated` | known CVEs + outdated |
| `frontend/package.json` + `frontend/package-lock.json` | `npm audit`, `npm outdated` | known CVEs + outdated |
| `widget/package.json` (if exists) | `npm audit`, `npm outdated` | same |
| `package.json` (root) | `npm audit`, `npm outdated` | same |

## Process
1. **Inventory** — list all `package.json` and `requirements*.txt` files
2. **Run audits** in parallel — npm audit + pip-audit per file
3. **Cross-check** with `trailofbits:supply-chain-risk-auditor` if installed
4. **Score** by severity × usage (a critical vuln in a never-loaded dev-only dep is lower priority than a high vuln in `fastapi`)
5. **Identify abandoned** — last commit >18mo + <100 stars on transitive deps
6. **Output report** to `docs/dependency-audit-YYYY-MM-DD.md`
7. **Hand off** — file `ai-ready` GH issues for safe upgrades

## Audit commands
```bash
# Frontend
cd frontend && npm audit --json > /tmp/npm-audit.json
cd frontend && npm outdated --json > /tmp/npm-outdated.json

# Backend
cd backend && pip-audit --format json > /tmp/pip-audit.json
cd backend && pip list --outdated --format json > /tmp/pip-outdated.json

# Widget (if separate package)
[ -f widget/package.json ] && cd widget && npm audit --json
```

## Report template
```markdown
# Dependency Audit — YYYY-MM-DD

## Summary
- Critical: <n> (action required immediately)
- High: <n> (this sprint)
- Medium: <n> (next sprint)
- Low: <n> (backlog)
- Outdated (no CVE): <n>
- Abandoned suspects: <n>

## Critical (block deploy)
| Package | Current | Fixed in | CVE | Path | Action |
|---|---|---|---|---|---|
| <name> | <ver> | <ver> | CVE-XXXX | <where used> | Bump + test |

## High
<same table>

## Medium / Low
<same table>

## Outdated (no CVE, freshness only)
| Package | Current | Latest | Major upgrade? | Notes |

## Abandoned suspects (review)
| Package | Last commit | Used by | Replacement candidate |

## Pinned versions (DO NOT bump without review)
| Package | Pin | Reason | Sunset criteria |
| claude-code | 2.1.98 | phantom 20k tokens in 2.1.100+ | see .claude/rules/claude-version-pin.md |

## Recommended PRs (in priority order)
1. <package> <current → fixed> — Critical CVE-XXXX
2. <package> <current → latest> — High vuln
3. <minor bumps batched> — Medium

## Test plan per upgrade
- Backend: `pytest backend/tests/`
- Frontend: `cd frontend && npm run build && npm run test`
- Widget: cross-origin embed test per `.claude/skills/widget-test/SKILL.md`
```

## Risk filters
- Skip auto-bump for: anything with breaking-change in CHANGELOG, anything matching `.claude/rules/claude-version-pin.md` pins, anything in widget (byte-sync risk)
- Auto-OK to bump: patch versions of devDependencies, security-only patches with no API change

## Issue filing
For each High+ finding, file via `gh issue create`:
```
Title: [security] Bump <package> <current> → <fixed> (<CVE>)
Labels: security, severity/<level>, layer/<backend|frontend|widget>, ai-ready
```

## Cross-refs
- `trailofbits:supply-chain-risk-auditor` — deeper SBOM analysis
- `.claude/skills/security-audit/SKILL.md` — broader codebase scan
- `.claude/rules/claude-code-security.md` — security hardening baseline
- `.claude/rules/claude-version-pin.md` — known intentional pins
