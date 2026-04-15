# /audits — Proof (verify)

Verification artifacts. Things ALREADY checked, results ALREADY recorded.

## Role
This folder answers: **"Has X been verified? What did the check find?"**

## What goes here
- Security scans (`audit-security-YYYY-MM-DD.md`)
- Dependency audits (`audit-dependencies-YYYY-MM-DD.md`)
- Code health audits (`audit-codebase-health-YYYY-MM-DD.md`)
- Performance benchmarks (`audit-perf-<feature>-YYYY-MM-DD.md`)
- Accessibility audits (`audit-a11y-<page>-YYYY-MM-DD.md`)
- Tenant chatbot audits (`audit-tenant-<client>-YYYY-MM-DD.md`)
- Post-mortems (`postmortem-<incident>-YYYY-MM-DD.md`)
- Pre-deploy verification reports

## What does NOT go here
- Code reviews on PRs (use GitHub PR comments)
- Future audit plans (those go in `/plans/`)
- Audit methodology (that's a `/docs/` page)
- Spec compliance criteria (those are in `/specs/`)

## Naming
`audit-<topic>-YYYY-MM-DD.md` or `postmortem-<incident>-YYYY-MM-DD.md`

## Producer skills
- `dependency-auditor` → `audits/audit-dependencies-*.md`
- `security-audit` → `audits/audit-security-*.md`
- `health-check` → `audits/audit-codebase-health-*.md`
- `tenant-chatbot-audit` → `audits/audit-tenant-*.md`
- `seo-audit-marketing` → `audits/audit-seo-*.md`
- `kb-health` → `audits/audit-kb-health-*.md`
- `verification-loop` → `audits/audit-verification-*.md`
- `triage-issue` (root cause) → `audits/postmortem-*.md`

## Cross-refs
- See `/STRUCTURE.md` for the 4-folder convention
