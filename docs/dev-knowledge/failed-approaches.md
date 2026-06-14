# Failed Approaches — What Didn't Work + What Did

Per-task log of approaches tried that failed, plus the approach that finally worked. Adjacent to `bug-patterns.md` (domain bugs) and `architecture-decisions.md` (locked-in choices). Different shape: this is task-pattern history, not bug taxonomy.

## Why this file
Saves future-me (and future Claude) from re-trying the same dead end. If a task takes 3+ attempts, log it here once it lands.

## Format
```
## <task type / problem>
- Date: YYYY-MM-DD
- Tried: <approach 1> — failed because <reason>
- Tried: <approach 2> — failed because <reason>
- Worked: <approach that landed> — <why it stuck>
- Note for next time: <one-line guidance>
```

## When to add an entry
- Task burned 3+ attempts before landing
- Failure mode was non-obvious (sandbox, schema ghost, framework quirk)
- Future sessions would plausibly hit the same wall
- The fix isn't already captured in `bug-patterns.md`, an ADR, or a rule file

## When NOT to add
- One-shot fixes (no failed attempts)
- Domain bugs — those go in `bug-patterns.md`
- Architectural decisions — those get an ADR in `planning/decisions/`
- Trivial typo/rename failures

---

## Entries

(none yet — add as failures accumulate)
