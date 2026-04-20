# Winning Concept — 2026-04-20

## Recommendation
Add Check 8 to `scripts/hooks/pre-commit`: detect duplicate migration numbers ≥106 and emit FAIL
(hard block), preventing future migration replay collisions before they ever reach Supabase.

## Why This, Why Now
`audits/audit-architecture-2026-04-18.md` rated migration numbering collisions as HIGH severity and
explicitly proposed this fix: "Enforce strict sequential check in `scripts/hooks/pre-commit` for
numbers ≥106." The existing duplicates (005, 007) are historical and locked — they can't be
renumbered without breaking Supabase replay — but future migrations from 106 onward have no
automated collision detection. With the codebase adding 5+ migrations per sprint and now reaching
migration 107, the risk of a duplicate-number collision grows each week. The pre-commit hook already
handles Python bare-except (Check 3) and `from __future__ import annotations` (Check 2) at this
exact layer — extending it with a filename-pattern check is S-effort with zero infrastructure
uncertainty. Unlike run 3's JS catch WARNING (which nudges), this is a FAIL block — higher
enforcement weight that's harder to accidentally skip.

## Implementation Sketch
1. **Read `scripts/hooks/pre-commit`** — find the final check block (currently around line 197).
2. **Add Check 8** after the last existing check:
   ```bash
   # CHECK 8: Migration number collision guard (≥106 only — pre-106 collisions are historical/locked)
   echo -n "Checking for duplicate migration numbers (≥106)... "
   MIGRATION_CONFLICT=""
   for file in $STAGED_FILES; do
     if [[ "$file" == migrations/*.sql ]]; then
       NUM=$(basename "$file" | grep -oE '^[0-9]+')
       if [[ -n "$NUM" && "$NUM" -ge 106 ]]; then
         EXISTING=$(ls migrations/ 2>/dev/null | grep -E "^${NUM}_" | grep -v "$(basename $file)" || true)
         if [[ -n "$EXISTING" ]]; then
           MIGRATION_CONFLICT="$MIGRATION_CONFLICT\n  $file conflicts with existing: $EXISTING"
         fi
       fi
     fi
   done
   if [[ -n "$MIGRATION_CONFLICT" ]]; then
     echo -e "${RED}FAIL${NC}"
     echo -e "  Duplicate migration number detected:${MIGRATION_CONFLICT}"
     echo -e "  Renumber the new migration to the next available number."
     ERRORS=$((ERRORS + 1))
   else
     echo -e "${GREEN}OK${NC}"
   fi
   ```
3. **Reinstall hook** — `bash scripts/install-hooks.sh` to copy updated hook to `.git/hooks/pre-commit`.
4. **Verify** — stage a file `migrations/107_test_collision.sql` (duplicate of the existing 107) and
   run `git commit --dry-run`. Confirm FAIL fires. Delete the test file.
5. **Document** — add one line to `docs/dev-knowledge/schema-log.md`:
   `2026-04-20: pre-commit Check 8 added — duplicate migration number guard for ≥106.`

## What This Replaces
Previous active direction from run 4: "AI-to-Human Handoff (Explicit Trigger, v1)" — that remains
in the backlog as a feature recommendation pending approval. This run diversifies back to code_health
(run 4 was growth/ux).

## Confidence
HIGH — Evidence triple-backed: (1) architecture audit HIGH finding with explicit fix proposal,
(2) CLAUDE.md Rule 8 ("Schema changes only via numbered migration files"), (3) pre-commit hook
extension pattern already proven for Python bare-except and `from __future__ import annotations`.
Debate: survived all 4 challenges. Implementation is pure bash filename pattern match — zero external
dependencies, zero infrastructure assumptions.
