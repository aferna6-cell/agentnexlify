# Idea 5: Skill Freshness Marker — Track Last-Verified Date in SKILL.md Files

**Category:** workflow_efficiency
**Effort:** M (schema + tooling)
**Confidence:** LOW

## Evidence
- 45d41c2 (2026-09-12): "fix(skill): account for centralized demo-role middleware" — route-security-guard-audit SKILL.md updated because codebase pattern changed.
- Skills can go stale silently when underlying code patterns change. No tracking exists for when a skill was last verified against current code.
- 80+ skills in .claude/skills/. Stale skills give wrong guidance.
- Only discovered stale by accident during code review, not by systematic check.

## Action
Add `last_verified` frontmatter field to all SKILL.md files. Add Step 9N to nightly: list all skills, check last_verified date, flag skills with `last_verified` > 90 days ago or missing. Log count.

## Weaknesses
- M effort: updating 80+ SKILL.md files' frontmatter is non-trivial.
- False signal: many skills don't reference code patterns and age gracefully.
- No automated way to update last_verified — requires human to run skill + confirm it works.
- Low urgency compared to credential expiry and Dependabot PRs.
