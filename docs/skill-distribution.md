# Skill Distribution

_Last updated: 2026-04-22_

## Convention

- Canonical skills live in `skills/canonical/<skill-name>/SKILL.md`.
- Canonical skill folders may include supporting files, but not README files.
- The sync script copies canonical skill trees into selected distribution targets.
- The script never deletes files. Existing target-only files stay in place.
- Dry-run is the default. Use `--write` to make changes.
- Dry-run exits non-zero when canonical-managed skill copies are out of sync.

## Distribution Targets

- `.claude/skills`
- `.codex/skills`
- `.agents/skills`
- `skills/generated`

## Current Canonical Set

- `ddup`
- `skillify`
- `tech-debt`
- `verify`

## Commands

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --target claude
python scripts/sync_skills.py --target codex --write
python scripts/sync_skills.py --target repo --write
python scripts/sync_skills.py --target all --write
npm run sync-skills:check
npm run sync-skills
```

## Notes

- The script is deterministic: it sorts skills and files before reporting or copying.
- If a canonical skill changes, rerun the sync command for the target tree that needs the update.
- The repo keeps canonical skill definitions separate from distribution copies to make drift visible.
- `npm run check:quick` fails early when canonical-managed targets drift.
