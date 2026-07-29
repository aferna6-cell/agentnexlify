---
name: feature-docs-trio
description: After any feature PR merges, produce KB wiki article + ADR entry + INDEX update + optional runbook in one [skip ci] commit. Trigger within 48h of feature landing.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- "docs for <feature>"
- "kb article for <feature>"
- "document <feature>"
- "feature docs"
- "feature-docs-trio"
effort: medium
---

# Feature Docs Trio

Post-feature documentation pattern. Run within 48h of any feature PR merging.

## When to Use
- Feature PR merged with no corresponding docs commit in 48h
- User says "docs for <feature>", "kb article for <feature>", "document <feature>"
- Preparing KB articles for tenant AI quality

## When NOT to Use
- Bug fixes, ops-only changes, dependency bumps — no new feature surface
- Feature not yet merged or behind a gate that hasn't shipped

## Steps

### 1. Read the PR
Extract from the merged PR description:
- Feature name (canonical slug for filenames)
- Key design decisions made
- Tier gate (which plan unlocks it: `chatbot`, `agent_os`, or all plans)
- Known failure modes (anything that can break silently)
- Related tables or endpoints

### 2. Write KB wiki article
Path: `knowledge-base/wiki/<category>/<feature-name>.md`

Required frontmatter:
```yaml
---
title: <Feature Name>
category: <category>
tags: [tag1, tag2]
last_updated: YYYY-MM-DD
---
```

Required sections:
- **What it does** — one paragraph, no jargon, tenant-facing language
- **How it works** — prose flow diagram: input → processing → output. Include relevant API endpoints or DB tables.
- **Tier gate** — which plan unlocks this feature; what happens if a lower-tier tenant tries to use it
- **Failure modes** — list each failure class with: symptom, root cause, fix
- **Related articles** — wikilinks to 2–3 connected articles (`[[article-slug]]`)

After writing, run `npm run kb:lint` — must be clean before committing.

### 3. Add ADR entry
File: `docs/dev-knowledge/architecture-decisions.md`

Format:
```
### ADR-YYYY-MM-DD — <Feature Title>
<2–3 sentences: what was decided, why, what alternatives were rejected>
```

Add under the most recent date block. Do not create a new file.

### 4. Update KB INDEX
File: `knowledge-base/INDEX.md`

Add one entry under the correct category section:
```
- [Feature Name](wiki/<category>/<feature-name>.md) — <10-word description>
```

Keep alphabetical order within the category.

### 5. Write runbook (if needed)
Path: `docs/runbooks/<feature>-failures.md`

Only write if the feature has on-call-actionable failure modes (not just "restart the service"). Format per failure class:
```
## <Failure class>
**Symptom:** <what the user or nightly sees>
**Root cause:** <why it happens>
**Fix:**
1. <step>
2. <step>
```

Skip this step for features with no unique failure surface (e.g., pure UI additions with no new async paths).

### 6. Commit
```
docs(<feature-name>): KB article + ADR + runbook [skip ci]
```

`[skip ci]` because this is docs-only — CI runner minutes are not needed for a markdown commit.

## Checklist
- [ ] `knowledge-base/wiki/<category>/<feature>.md` written and lint-clean
- [ ] ADR entry added to `docs/dev-knowledge/architecture-decisions.md`
- [ ] `knowledge-base/INDEX.md` updated
- [ ] `docs/runbooks/<feature>-failures.md` written (or skipped with reason noted)
- [ ] Commit tagged `[skip ci]`
