# Skill Checker

Run the deterministic skill linter with:

```powershell
python scripts/check_skills.py
npm run check:skills
```

The checker scans:

- `.claude/skills`
- `.codex/skills`
- `.agents/skills`
- `skills/canonical`
- `skills/generated`

It reports hard failures for:

- missing YAML frontmatter
- missing `name` or `description`
- invalid skill names
- side-effect skills that do not set `disable-model-invocation: true`
- obvious full-looking secret tokens in the skill body

It prints warnings for:

- generic descriptions without an obvious use/when cue
- directory/name mismatches
- skill bodies over 500 lines, which should be split into references over time
- missing referenced local paths when the reference is easy to detect

The checker uses only the Python standard library and is safe to run from Windows PowerShell.

`npm run check:quick` runs this checker, the canonical skill sync dry-run, the trigger evals, and then the project/widget checks.
