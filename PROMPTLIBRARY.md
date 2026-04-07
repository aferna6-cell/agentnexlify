# Prompt Library — AgentNexLiFy

**Treat prompts like reusable software components.** Each prompt is versioned, tested in production, and iteratively improved.

## How to Use This Library

1. **You receive a task** → Find the matching prompt below by category
2. **Read the prompt** → Follow its instructions exactly
3. **Gather context** → The prompt will tell you what files/data to read
4. **Execute** → Run the task
5. **Improve the prompt** → After completing the task, update this file with what you learned. If the prompt was wrong, incomplete, or could be better — fix it NOW. Every interaction is a chance to improve.

### If no prompt exists for your task:
1. Create a new entry in the appropriate category below
2. Write the prompt you wish you had been given
3. Execute the task using your prompt
4. After completion, refine the prompt with what you learned

---

## Prompt Format

Each prompt follows this structure:

```
### [CATEGORY] Prompt Name (v1.0.0)
**When to use:** [triggers]
**Context needed:** [files, data, commands to run first]
**Steps:**
1. ...
2. ...
**Output:** [what to produce]
**Common pitfalls:** [what to watch for]
**Last improved:** [date] — [what changed and why]
```

---

## Research & Discovery

### RESEARCH Codebase Investigation (v1.1.0)

**When to use:** "Find how X works", "Where is Y implemented?", "What calls Z?", "Understand the flow of..."

**Context needed:**
- Start with `grep_search` for the keyword/concept
- Use `glob` to find relevant files by pattern
- Read 2-3 of the most relevant files to understand the pattern

**Steps:**
1. Search for the target concept using `grep_search` with a regex pattern. Start broad, then narrow.
2. Use `glob` to find files matching likely naming conventions.
3. Read the top 3 most relevant files completely — do not skim.
4. Trace the call chain: if a function is called, find its definition. If it calls something, find what it calls.
5. Map the data flow: where does data enter? Where does it exit? What transforms it?
6. Check for tests — they document expected behavior better than comments.
7. Synthesize findings into a clear answer with file paths and line numbers.

**Output:** A structured answer with:
- Where the concept lives (files + line numbers)
- How it works (data flow, key functions)
- Related concepts that might matter
- Any risks or gotchas found

**Common pitfalls:**
- Don't trust function names — read the implementation
- Don't assume a pattern is used everywhere — verify each call site
- Check `_archive/` for old implementations that may still be referenced
- Look at git history for recently changed files

**Last improved:** 2026-04-07 — Added step 4 (trace call chains) and step 6 (check tests). Previous version skipped these and produced incomplete answers.

---

## Summarization

### SUMMARIZE Code Change Summary (v1.0.0)

**When to use:** "What changed?", "Summarize recent commits", "What does this PR do?", "Explain these diffs"

**Context needed:**
- Run `git log --oneline -20` for recent commits
- Run `git diff HEAD~N --stat` for change scope
- Read the commit messages and changed files

**Steps:**
1. Run `git status` to see current state
2. Run `git log --oneline -N` to get recent commits (default N=10, adjust if user specifies)
3. For each commit of interest, run `git show <hash> --stat` to see what changed
4. Read the actual diffs for non-obvious changes (`git diff HEAD~N..HEAD -- <file>`)
5. Group changes by theme (feature, fix, refactor, infra, docs)
6. Write a summary that a new team member could understand in 30 seconds

**Output:** A categorized summary with:
- High-level theme (one sentence)
- Per-category bullet points with file references
- Any breaking changes or risks called out

**Common pitfalls:**
- Don't just list files — explain WHAT changed and WHY
- Don't ignore small files — they often contain critical fixes
- Check if migrations were added (database impact)
- Check if tests were added/removed (quality signal)

**Last improved:** 2026-04-07 — Initial version

---

## Debugging

### DEBUG Bug Investigation (v1.1.0)

**When to use:** "Something is broken", "This error is happening", "Why doesn't X work?", "Investigate this bug"

**Context needed:**
- The error message, stack trace, or observed behavior
- The file(s) and line numbers involved
- Recent changes to the affected code (`git log --oneline -10 -- <file>`)

**Steps:**
1. **Reproduce first:** Understand what the user expects vs what actually happens
2. **Read the code:** Read the full function/method, not just the error line. Read 3 levels up the call stack.
3. **Check inputs:** What data flows into this code? Is it what we expect? Add logging if needed.
4. **Check dependencies:** What does this code depend on? Are those dependencies healthy? (DB connection, API keys, file existence)
5. **Check recent changes:** Run `git log --oneline -10 -- <affected files>` — was this working before? What changed?
6. **Form a hypothesis:** State what you think the root cause is, with evidence.
7. **Test the hypothesis:** Make the smallest possible change to verify. If you can't test, state what test would confirm.
8. **Fix:** Apply the minimal fix. Do not refactor while debugging.
9. **Verify:** Run tests, check the specific failure is resolved.

**Output:** 
- Root cause (one sentence)
- Evidence (logs, stack traces, code snippets)
- The fix applied
- What test should be added to prevent regression

**Common pitfalls:**
- **DO NOT** add catch-all `try/except` blocks that hide errors
- **DO NOT** add "just in case" defensive code — fix the actual root cause
- **DO NOT** refactor while debugging — fix first, refactor separately
- Check if the error is a symptom of a different problem (e.g., missing env var, DB connection)
- Read the `docs/dev-knowledge/bug-patterns.md` — this may be a known issue
- Check `.claude/agent-comms/` for previous debugging sessions on this topic

**Last improved:** 2026-04-07 — Added "check recent changes" step and "check bug patterns doc". Previous version didn't check git history and missed regression-caused bugs.

---

### DEBUG Production Error Analysis (v1.0.0)

**When to use:** "This error showed up in logs", "Users are reporting X", "Monitoring alert fired"

**Context needed:**
- Error logs or monitoring output
- Affected endpoint or feature
- Time window of the issue

**Steps:**
1. Read the error message and stack trace carefully
2. Identify the affected endpoint, file, and line number
3. Check if this is a new error or recurring (`grep` in logs/commits)
4. Check the affected code path — what inputs could cause this?
5. Check if recent deploys introduced the issue (`git log --since="2 days ago" -- <file>`)
6. Determine severity: user-facing? data loss? revenue impact?
7. Propose fix + rollback plan if needed

**Output:** Error analysis with severity, root cause, fix, and prevention recommendation.

**Common pitfalls:**
- Don't assume a single error instance — check frequency
- Check if the error is masking a deeper issue (e.g., swallowed exception)
- Consider whether the fix needs a migration or config change

**Last improved:** 2026-04-07 — Initial version

---

## Content Writing

### WRITE Documentation Article (v1.0.0)

**When to use:** "Write docs for X", "Document this feature", "Create a guide for..."

**Context needed:**
- The code/feature being documented
- Target audience (developers, end users, admins)
- Existing docs in `docs/` for style reference

**Steps:**
1. Read the code/feature thoroughly — you cannot document what you don't understand
2. Check existing docs in `docs/` for style, tone, and structure conventions
3. Identify the key concepts a reader needs to understand
4. Structure the document:
   - Title and one-sentence summary
   - When to use this (and when NOT to)
   - How it works (architecture, data flow)
   - How to use it (step-by-step, with examples)
   - Troubleshooting / FAQ
   - Related docs (cross-references)
5. Write in dense, technical prose. No fluff, no marketing speak.
6. Include code examples where applicable
7. Add file paths and line numbers for reference

**Output:** A markdown file ready for `docs/` directory.

**Common pitfalls:**
- Don't document the obvious — focus on what's non-obvious
- Don't write a tutorial when a reference is needed (know your audience)
- Always cross-reference related docs
- Update the doc if you discover the code has drifted from existing docs

**Last improved:** 2026-04-07 — Initial version

---

### WRITE Commit Message (v1.0.0)

**When to use:** After completing a task, before committing

**Context needed:**
- `git status` to see changed files
- `git diff --stat HEAD` for change scope
- `git log -n 3` for recent commit style

**Steps:**
1. Run `git status && git diff --stat HEAD && git log -n 3`
2. Write a subject line: imperative mood, <72 chars, starts with type prefix
3. Write body (if needed): explain WHY, not WHAT. What problem does this solve?
4. Follow the repo's commit style (check recent commits)
5. Include `[main YYYY-MM-DD]` tag if the repo uses dated commits

**Output:** A commit message ready for `git commit -m "..."`

**Common pitfalls:**
- Don't describe the change — describe the problem it solves
- Don't write a novel — 1-3 sentences max for body
- Match the existing commit style (check `git log`)

**Last improved:** 2026-04-07 — Initial version

---

## Reasoning & Decision Making

### REASON Architecture Decision (v1.0.0)

**When to use:** "Should we use X or Y?", "What's the best approach for...", "Evaluate these options"

**Context needed:**
- The decision to be made
- The options being considered
- Constraints (time, resources, existing tech stack)

**Steps:**
1. **Frame the decision:** State the problem clearly. "How should we X?" not "Should we use Y?"
2. **List options:** At least 2, ideally 3. Include "do nothing" as an option when relevant.
3. **Evaluate each option against criteria:**
   - Implementation effort (low/medium/high)
   - Maintenance cost (low/medium/high)
   - Risk (low/medium/high)
   - Alignment with existing architecture (yes/no/partial)
   - Reversibility (easy/hard/impossible)
4. **Check existing decisions:** Read `docs/dev-knowledge/architecture-decisions.md` — has this been decided before?
5. **Recommend:** Pick one option with clear reasoning
6. **Document:** Write an ADR (Architecture Decision Record) in `docs/dev-knowledge/`

**Output:** A recommendation with reasoning, or an ADR document.

**Common pitfalls:**
- Don't present options without a recommendation — that's dumping work on the human
- Don't ignore the "do nothing" option — sometimes the best choice is not to change
- Check if this decision was already made (avoid re-litigating)
- Consider the reversible vs irreversible distinction heavily (Bezos' type 1/type 2)

**Last improved:** 2026-04-07 — Initial version

---

### REASON Debugging Hypothesis (v1.0.0)

**When to use:** "What could be causing this?", "I have no idea where to start"

**Context needed:**
- The observed symptom (error message, behavior, log output)
- Any recent changes (deploys, config updates, data changes)

**Steps:**
1. List all possible causes, ordered by likelihood:
   - Recent changes first
   - Common failures before rare ones
   - External dependencies (DB, APIs, env vars) before internal logic
2. For each hypothesis, state:
   - What evidence would confirm it
   - What evidence would rule it out
   - How to test it (specific command, log to check)
3. Test hypotheses in order from most likely to least likely
4. Stop when you find the root cause — don't keep going

**Output:** A ranked hypothesis with test plan, or the identified root cause.

**Common pitfalls:**
- Don't jump to the most interesting cause — start with the most likely
- Don't test in parallel if tests interfere with each other
- Don't skip the "is it plugged in" check (env vars, connections, permissions)
- Write down what you tested and the result — avoid re-testing

**Last improved:** 2026-04-07 — Initial version

---

## Code Review

### REVIEW Code Review Checklist (v1.0.0)

**When to use:** "Review this code", "Check this PR", "Is this safe to merge?"

**Context needed:**
- The changed files (`git diff HEAD~N` or PR diff)
- The intent (what is this change supposed to do?)

**Steps:**
1. Read the diff completely
2. Check for the critical invariants (from `AGENTS.md`):
   - No `from __future__ import annotations` in FastAPI router files
   - `client_id` used for `leads` and `conversations` queries
   - `status` used for lead status (not `lead_stage`)
   - Widget files in sync (or symlinked)
   - Migrations used for schema changes
   - No raw secret values committed
   - MCP API keys used for MCP access (not widget API keys)
3. Check security:
   - Input validation on all external inputs
   - Auth checks on protected endpoints
   - No SQL injection (parameterized queries)
   - No XSS (HTML escaping on user input)
4. Check error handling:
   - No bare `except:` clauses
   - No silent exception swallowing
   - Errors logged with context
5. Check performance:
   - No N+1 queries
   - No unbounded loops on user data
   - Caching where appropriate
6. Check tests:
   - Tests added for new behavior
   - Tests updated for changed behavior
   - Edge cases covered

**Output:** Review findings organized by severity (critical/high/medium/low) with specific file references.

**Common pitfalls:**
- Don't nitpick style — focus on correctness, security, and architecture
- Don't approve without checking the critical invariants
- Don't miss the "what problem does this solve?" check — code that solves the wrong problem is worse than no code

**Last improved:** 2026-04-07 — Initial version, based on patterns from the comprehensive debugging session.

---

## Feature Development

### BUILD New Feature (v1.0.0)

**When to use:** "Add feature X", "Implement Y", "Build Z"

**Context needed:**
- Feature requirements (what should it do?)
- Existing related code (where does it fit?)
- Database schema (does it need new tables?)

**Steps:**
1. **Understand:** Read requirements. Ask clarifying questions if ambiguous.
2. **Locate:** Find where this feature fits in the existing architecture.
3. **Plan:** Create a todo list with specific, actionable items. Smallest possible changes first.
4. **Schema first:** If DB changes needed, write the migration before any code.
5. **Backend before frontend:** Implement API endpoints, then UI.
6. **Tests alongside:** Write tests as you implement, not after.
7. **Verify:** Run the full test suite. Fix any failures.
8. **Commit:** Write a descriptive commit message. Follow repo conventions.

**Output:** Working feature with tests, committed and ready to push.

**Common pitfalls:**
- Don't add abstraction layers for a single call site
- Don't add "just in case" features not in the requirements
- Don't skip the migration step — schema drift causes most bugs in this repo
- Check `docs/dev-knowledge/canonical-schema.md` before any DB work
- Check `docs/dev-knowledge/architecture-decisions.md` for prior decisions

**Last improved:** 2026-04-07 — Initial version

---

## Migration & Database

### DATABASE Schema Change (v1.0.0)

**When to use:** "Add a column", "Create a table", "Change a constraint", "Fix the schema"

**Context needed:**
- `docs/dev-knowledge/canonical-schema.md` — the authoritative schema reference
- `migrations/` — existing migrations
- `git log --oneline -10 -- migrations/` — recent migration history

**Steps:**
1. Check `canonical-schema.md` to understand the current state
2. Check if the column/table already exists (it may have been added ad-hoc)
3. Create a new migration file with the next sequential number
4. Use `ADD COLUMN IF NOT EXISTS` for safety
5. Test the migration can run on the current DB state
6. Update `canonical-schema.md` with the new column/table
7. Update any code that was relying on the column not existing

**Output:** Migration file, updated schema doc, and updated code if needed.

**Common pitfalls:**
- **ALWAYS** check if the column already exists in production before adding it
- Use `IF NOT EXISTS` guards — migrations may be run multiple times
- Never rename a migration file — it breaks applied migration tracking
- Check for duplicate migration numbers before creating a new one
- Column additions are safe — deletions need careful analysis of all consumers

**Last improved:** 2026-04-07 — Initial version, informed by the schema reconciliation work in migration 094.

---

## Testing

### TEST Add Test Coverage (v1.0.0)

**When to use:** "Add tests for X", "This needs test coverage", "Write tests for this code"

**Context needed:**
- The code to be tested
- Existing test files for patterns and conventions
- `pytest.ini` for test configuration

**Steps:**
1. Read the code to understand what needs testing
2. Check existing tests in `tests/` for patterns, mocking style, and conventions
3. Identify the test cases:
   - Happy path (expected inputs → expected outputs)
   - Edge cases (empty inputs, boundary values, special characters)
   - Error cases (invalid inputs, missing dependencies, network failures)
   - Security cases (auth bypass, injection, privilege escalation)
4. Write tests using the existing patterns (mocks, fixtures, parametrize)
5. Run the tests — they must pass
6. Check coverage — are all code paths exercised?

**Output:** Test file with comprehensive coverage, all passing.

**Common pitfalls:**
- Don't test implementation details — test observable behavior
- Don't mock everything — test real integration where it matters
- Match the existing test style (check `tests/test_widget_api.py` for a good example)
- Include negative tests (what should NOT happen)
- Test the error paths, not just the happy path

**Last improved:** 2026-04-07 — Initial version

---

## Skill & Prompt Management

### PROMPT Create or Improve Prompt (v1.0.0)

**When to use:** After completing any task where a prompt was used or should have been used

**Context needed:**
- This file (`PROMPTLIBRARY.md`)
- The task that was just completed
- What worked and what didn't about the current prompt (if any)

**Steps:**
1. **If prompt exists:** Read it. Did you follow it? Did it help? What was missing or wrong?
2. **If prompt doesn't exist:** Create a new entry in the appropriate category
3. **Improve the prompt:**
   - Add steps you needed that weren't in the prompt
   - Remove steps that were unnecessary
   - Add pitfalls you encountered
   - Update the "Last improved" line with date and what changed
4. **Version bump:** Increment the version number (patch for small fixes, minor for additions, major for rewrites)

**Output:** An improved prompt in this file.

**Common pitfalls:**
- Don't improve prompts in theory — improve them based on actual usage
- Don't make prompts longer — make them more precise
- Every step should be actionable
- "Common pitfalls" is the most valuable section — update it every time

**Last improved:** 2026-04-07 — Initial version (meta-prompt for maintaining this library)

---

## Index

| Category | Prompt | Version | Last Updated |
|----------|--------|---------|--------------|
| Research | Codebase Investigation | 1.1.0 | 2026-04-07 |
| Summarize | Code Change Summary | 1.0.0 | 2026-04-07 |
| Debug | Bug Investigation | 1.1.0 | 2026-04-07 |
| Debug | Production Error Analysis | 1.0.0 | 2026-04-07 |
| Write | Documentation Article | 1.0.0 | 2026-04-07 |
| Write | Commit Message | 1.0.0 | 2026-04-07 |
| Reason | Architecture Decision | 1.0.0 | 2026-04-07 |
| Reason | Debugging Hypothesis | 1.0.0 | 2026-04-07 |
| Review | Code Review Checklist | 1.0.0 | 2026-04-07 |
| Build | New Feature | 1.0.0 | 2026-04-07 |
| Database | Schema Change | 1.0.0 | 2026-04-07 |
| Test | Add Test Coverage | 1.0.0 | 2026-04-07 |
| Prompt | Create or Improve Prompt | 1.0.0 | 2026-04-07 |

---

## Related Resources

- **Skills index:** `skills/index.json` — machine-readable skill registry
- **Agent definitions:** `.claude/agents/` — specialized agent roles
- **Commands:** `.claude/commands/` — executable workflow commands
- **Architecture decisions:** `docs/dev-knowledge/architecture-decisions.md`
- **Canonical schema:** `docs/dev-knowledge/canonical-schema.md`
- **Bug patterns:** `docs/dev-knowledge/bug-patterns.md`
- **Schema log:** `docs/dev-knowledge/schema-log.md`
