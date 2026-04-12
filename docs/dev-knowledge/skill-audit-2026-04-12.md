# Skill Audit — 2026-04-12

Audited 47 project skills in `.claude/skills/` against canonical rubric from Anthropic's `skill-creator` SKILL.md.

## Rubric (from canon)

1. **Frontmatter** — `name` + `description` required (YAML)
2. **Description quality** — describe WHAT and explicit WHEN-to-trigger. "Pushy" — include trigger phrases so Claude routes to the skill instead of undertriggering
3. **Body length** — under 500 lines ideal; split into `references/` if longer
4. **Progressive disclosure** — `scripts/`, `references/`, `assets/` for bundled content
5. **Imperative voice**, explain WHY, avoid heavy `MUST`/`NEVER`/`ALWAYS` caps (yellow flag)
6. **No surprise** — skill purpose matches description

## Results

- **Clean: 10** — `ai-feature-pattern`, `autonomous-webapp-test`, `debug-api`, `deploy-workflow`, `feature-build`, `industry-content`, `karpathy-guidelines`, `migration-workflow`, `schema-guard`, `team-orchestration`
- **Flagged: 37** — dominant issue is missing explicit trigger phrases in description
- **Body >500 lines: 3** — `coding-standards` (540), `compound-engineering` (568), `wiki` (523)
- **All skills have valid frontmatter** — zero YAML errors

## Dominant finding: description triggering

Canon quote: *"Currently Claude has a tendency to 'undertrigger' skills — to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit 'pushy'."*

Clean skills open with explicit triggers: `"Use when…"`, `"Use this skill when…"`, `"Use BEFORE…"`.

Flagged skills describe capability only: `"Test, debug, or verify the chat widget covering load, conversation, data capture…"` — no trigger phrase, so Claude reads it as "what the skill does" but not "when to reach for it."

### Fix pattern

Before: `"Tamagotchi-style coding companion. Deterministic creature generated from user ID."`

After: `"Tamagotchi-style coding companion. Deterministic creature generated from user ID. Use when the user says 'buddy', 'pet', 'tamagotchi', or asks about session health/mood — include the buddy in responses whenever the skill is loaded."`

## Length violations

- `coding-standards/SKILL.md` (540 lines) → split framework-specific sections into `references/typescript.md`, `references/react.md`, `references/nodejs.md`
- `compound-engineering/SKILL.md` (568 lines) → split per-agent instructions into `references/brainstorm.md`, `references/planner.md`, etc.
- `wiki/SKILL.md` (523 lines) → split per-source-type handlers (URL, YouTube, file, image) into `references/`

## Flagged skills (full list)

| Skill | Desc len | Lines | Caps | Issues |
|-------|----------|-------|------|--------|
| autopilot-loop | 167 | 88 | 0 | no-trigger |
| buddy | 183 | 118 | 0 | no-trigger |
| build-loop | 196 | 119 | 0 | no-trigger |
| challenge-assumptions | 141 | 195 | 0 | no-trigger |
| coding-standards | 116 | 540 | 2 | no-trigger, too-long |
| compound-engineering | 220 | 568 | 3 | no-trigger, too-long |
| coordinator | 109 | 439 | 1 | no-trigger |
| dead-code-sweep | 144 | 132 | 0 | no-trigger |
| deep-research | 148 | 166 | 0 | no-trigger |
| e2e-testing | 133 | 343 | 0 | no-trigger |
| eval-harness | 107 | 245 | 0 | no-trigger |
| gitnexus/cli | 132 | 97 | 0 | no-trigger |
| gitnexus/debugging | 111 | 107 | 0 | no-trigger |
| gitnexus/exploring | 119 | 95 | 0 | no-trigger |
| gitnexus/guide | 122 | 86 | 0 | no-trigger |
| gitnexus/impact-analysis | 112 | 106 | 0 | no-trigger |
| gitnexus/refactoring | 114 | 130 | 0 | no-trigger |
| kairos | 92 | 135 | 1 | no-trigger |
| kb-compile | 175 | 204 | 0 | no-trigger |
| kb-discover | 125 | 105 | 0 | no-trigger |
| kb-health | 140 | 152 | 0 | no-trigger |
| kb-ingest | 155 | 97 | 0 | no-trigger |
| kb-query | 112 | 118 | 0 | no-trigger |
| kevin-mode | 123 | 73 | 0 | no-trigger |
| last30days | 146 | 384 | 0 | no-trigger |
| obsidian-sync | 127 | 372 | 0 | no-trigger |
| prompt-library | 188 | 70 | 1 | no-trigger |
| security-audit | 156 | 132 | 0 | no-trigger |
| security-patch-from-review | 184 | 102 | 0 | no-trigger |
| strategic-compact | 139 | 110 | 0 | no-trigger |
| subconscious | 141 | 220 | 0 | no-trigger |
| tdd-workflow | 150 | 418 | 1 | no-trigger |
| tenant-chatbot-audit | 119 | 166 | 0 | no-trigger |
| verification-loop | 127 | 144 | 0 | no-trigger |
| widget-test | 119 | 59 | 0 | no-trigger |
| wiki | 121 | 523 | 0 | no-trigger, too-long |
| worktree-orchestrator | 122 | 400 | 1 | no-trigger |

Note: `caps` = count of `MUST`/`NEVER`/`ALWAYS`. All are well under the yellow-flag threshold (15) — tone is generally good across the repo.

## Recommended next steps

1. **Rewrite 37 descriptions** — add explicit trigger phrases. Haiku task. Mechanical.
2. **Split 3 oversize skills** — `coding-standards`, `compound-engineering`, `wiki` into `references/`. Sonnet task, needs content decisions.
3. **Run description-optimizer** — canon's `skill-creator` has `scripts/run_loop.py` that benchmarks trigger accuracy. Optional. Defer.

## Raw data
`/tmp/claude/skill-audit.json`
