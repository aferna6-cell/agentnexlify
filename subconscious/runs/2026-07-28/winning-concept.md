# Winning Concept — 2026-07-28 (Run 101)

## Recommendation
Create `.claude/skills/feature-docs-trio/SKILL.md` encoding the 6-step post-feature documentation pattern observed 3× in 7 days. Nightly commit-review executes the file creation autonomously — same channel as prior SKILL.md commits.

## Why This, Why Now

Three occurrences of the same pattern in 7 days (717c7f3 photo-quote, 14ebe8e drive-kb, d50d1e8 zapier) — all documented by skill-discovery-2026-07-27 with step-by-step detail already extracted. The design work is done. Only the execution remains.

AgentNexLiFy is in a feature-heavy sprint (SHOW_BOOKING_PANEL, route introspection, router semantics, agent graph runtime shipped in one week). Each feature that ships without this skill costs 30-45 min of overhead per occurrence: "which sections do I need?", kb:lint violations, missing INDEX entries. At 2-3 features/week, that's 60-135 min/week of recoverable waste.

The `feature-docs-trio` pattern also directly feeds KB quality: documented features → more accurate wiki articles → better widget AI responses for tenants. This compounds tenant value without requiring any code changes.

Prior carry-forward candidates (Step 9G) were eliminated this run: the original Step 9G is now OBSOLETE because a Claude Code cloud Routine ("KB Auto-Populate (CCR)") was deployed 2026-07-23 to handle KB autopopulate without needing GitHub Actions secrets (GH Actions currently broken repo-wide, #500). Implementing original Step 9G would produce incorrect diagnostics on GH #403. Governance updated below.

## Implementation Sketch

Write `.claude/skills/feature-docs-trio/SKILL.md`:

```markdown
---
name: feature-docs-trio
description: After any feature PR merges, produce KB wiki article + ADR entry + INDEX update + optional runbook in one [skip ci] commit. Trigger within 48h of feature landing.
---

## Trigger
Feature PR merged with no corresponding docs commit in 48h. User says "docs for <feature>", "kb article for <feature>", "document <feature>".

## Steps

1. **Read PR** — extract feature name, key decisions, tier gates, failure modes from PR description.

2. **Write `knowledge-base/wiki/<category>/<feature-name>.md`**:
   - Frontmatter: `title`, `category`, `tags`, `last_updated`
   - Required sections: What it does, How it works (prose flow diagram), Tier gate (which plan unlocks it), Failure modes, Related articles (wikilinks)
   - Run `npm run kb:lint` — must be clean before committing

3. **Add ADR entry to `docs/dev-knowledge/architecture-decisions.md`**:
   - Format: `ADR-YYYY-MM-DD-NNN — <title>` + 2-3 sentence rationale + alternatives rejected

4. **Update `knowledge-base/INDEX.md`** — add entry under correct category section.

5. **Write `docs/runbooks/<feature>-failures.md`** (if the feature has on-call-actionable failure modes):
   - Format per failure class: symptom → root cause → fix steps

6. **Commit** as `docs(<feature>): KB article + ADR + runbook [skip ci]`
   — skip ci because this is docs-only; CI runner minutes aren't needed.
```

Also update `feature-build/SKILL.md` to add: "After the feature PR merges, run `feature-docs-trio` to produce KB article + ADR + runbook in a follow-up `[skip ci]` commit."

Total new lines: ~50 SKILL.md content + ~3 lines in feature-build update. No code changes. No schema changes.

## Step 9G Governance Note

Original Step 9G (run 100 winner) is marked OBSOLETE in this run's governance update:
- Designed to: `gh workflow run kb-autopopulate.yml` when KB stale > 7 days
- Why obsolete: CCR Routine deployed 2026-07-23 handles KB autopopulate via cloud Routine without GH Actions secrets; GH Actions broken repo-wide (#500); implementing original Step 9G would trigger GH workflow (fail due to #500), then comment on #403 with "Check ANTHROPIC_API_KEY" — incorrect diagnostic since CCR Routine is the active path
- Corrected monitoring approach (carry-forward to run 102): verify CCR Routine health via `gh pr list --search "kb autopopulate"` check — if KB >7 days stale AND no KB PR in 48h, comment "CCR Routine may be stalled"

## Backlog Recommendations

1. **(MEDIUM) Silent-green tenant heartbeat** — nightly Step 9H: query conversations table, alert if any paid tenant has 0 conversations in 7 days. Prevents Keys Koffee-class silent churn. Requires: verify SUPABASE_URL + SUPABASE_SERVICE_KEY available in nightly bash environment; design dedup logic to prevent alert fatigue. Owner approval needed before implementing.

2. **(LOW) `widget-ai-marker-add` SKILL.md** — create skill for adding new LLM-triggered UI action markers. 2 occurrences observed, ~1/month frequency. Most error-prone step: byte-identical sync. Nightly-executable, lower urgency than feature-docs-trio.

3. **(LOW) `round-iteration-loop` SKILL.md** — create skill for iterative Agent OS-style refinement rounds. 3 occurrences in 7 days. Natural next skill after agent graph runtime ships.

## Confidence
**HIGH** — Same channel (SKILL.md creation) proven across all prior subconscious run implementations. Evidence is 3 direct instances with design already extracted by skill-discovery. Failure surface: zero (creating a SKILL.md file cannot break production). Current feature velocity makes this immediately load-bearing.
