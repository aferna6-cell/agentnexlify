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
**Role:** Who the executor is — usually "You are Claude Code working on AgentNexLiFy" plus any prompt-specific persona.
**Task:** The imperative — what to do. 1-3 sentences. Numbered steps under Task if procedural detail is worth preserving.
**Context:** What to read/know before starting. File paths, commands, and guardrails exact.
**Format:** What the output should look like.
**Tone:** Caveman mode default — see `.claude/rules/personality.md`. Override per prompt only when clearly needed.
**Last improved:** [date] — [what changed and why]
```

---

## Research & Discovery

### RESEARCH Codebase Investigation (v1.1.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a senior codebase researcher tracing implementation and data flow.

**Task:** Investigate how a concept, function, or system works. Search broad then narrow; trace the full call chain; map data entry and exit points; check tests for documented expected behavior; synthesize into a structured answer with file paths and line numbers.
1. Search for the target concept using `grep_search` with a regex pattern. Start broad, then narrow.
2. Use `glob` to find files matching likely naming conventions.
3. Read the top 3 most relevant files completely — do not skim.
4. Trace the call chain: if a function is called, find its definition. If it calls something, find what it calls.
5. Map the data flow: where does data enter? Where does it exit? What transforms it?
6. Check for tests — they document expected behavior better than comments.
7. Synthesize findings into a clear answer with file paths and line numbers.

**Context:** Start with `grep_search` for the keyword/concept; use `glob` to find relevant files by pattern; read 2-3 of the most relevant files to understand the pattern. Guardrails: don't trust function names — read the implementation; don't assume a pattern is used everywhere — verify each call site; check `_archive/` for old implementations that may still be referenced; look at git history for recently changed files.

**Format:** Structured answer with:
- Where the concept lives (files + line numbers)
- How it works (data flow, key functions)
- Related concepts that might matter
- Any risks or gotchas found

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Added step 4 (trace call chains) and step 6 (check tests). Previous version skipped these and produced incomplete answers. · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Summarization

### SUMMARIZE Code Change Summary (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a technical historian summarizing what changed and why.

**Task:** Summarize recent commits or a PR diff so a new team member understands the scope in 30 seconds. Run git commands to gather change scope, group changes by theme, and produce a categorized summary.
1. Run `git status` to see current state.
2. Run `git log --oneline -N` to get recent commits (default N=10, adjust if user specifies).
3. For each commit of interest, run `git show <hash> --stat` to see what changed.
4. Read the actual diffs for non-obvious changes (`git diff HEAD~N..HEAD -- <file>`).
5. Group changes by theme (feature, fix, refactor, infra, docs).
6. Write a summary that a new team member could understand in 30 seconds.

**Context:** Run `git log --oneline -20` for recent commits; run `git diff HEAD~N --stat` for change scope; read the commit messages and changed files. Guardrails: don't just list files — explain WHAT changed and WHY; don't ignore small files — they often contain critical fixes; check if migrations were added (database impact); check if tests were added/removed (quality signal).

**Format:** Categorized summary with:
- High-level theme (one sentence)
- Per-category bullet points with file references
- Any breaking changes or risks called out

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Debugging

### DEBUG Bug Investigation (v1.2.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a methodical debugger who fixes root causes, not symptoms.

**Task:** Investigate a broken behavior. Reproduce the failure mentally; read 3 levels up the call stack; check inputs, dependencies, and recent changes; form and test a hypothesis; apply the minimal fix; verify resolution.
1. **Reproduce first:** Understand what the user expects vs what actually happens.
2. **Read the code:** Read the full function/method, not just the error line. Read 3 levels up the call stack.
3. **Check inputs:** What data flows into this code? Is it what we expect? Add logging if needed.
4. **Check dependencies:** What does this code depend on? Are those dependencies healthy? (DB connection, API keys, file existence)
5. **Check recent changes:** Run `git log --oneline -10 -- <affected files>` — was this working before? What changed?
6. **Check for stale references:** If the failure is "module/function not found", verify whether the target was intentionally removed or renamed. Grep tests and recent commits before restoring deleted code.
7. **Form a hypothesis:** State what you think the root cause is, with evidence.
8. **Test the hypothesis:** Make the smallest possible change to verify. If you can't test, state what test would confirm.
9. **Fix:** Apply the minimal fix. Do not refactor while debugging.
10. **Verify:** Run tests, check the specific failure is resolved.

**Context:** Need the error message, stack trace, or observed behavior; the file(s) and line numbers involved; recent changes to the affected code (`git log --oneline -10 -- <file>`). Guardrails: DO NOT add catch-all `try/except` blocks that hide errors; DO NOT add "just in case" defensive code — fix the actual root cause; DO NOT refactor while debugging — fix first, refactor separately; check if the error is a symptom of a different problem (e.g., missing env var, DB connection); when a test references a missing module, confirm whether the test is orphaned before re-adding deleted production code; if FastAPI tests hang, verify the transport/harness before blaming the endpoint — check `TestClient` compatibility and whether sync dependencies or sync dependency overrides are forcing threadpool execution; read `docs/dev-knowledge/bug-patterns.md` — this may be a known issue; check `.claude/agent-comms/` for previous debugging sessions on this topic.

**Format:**
- Root cause (one sentence)
- Evidence (logs, stack traces, code snippets)
- The fix applied
- What test should be added to prevent regression

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-10 — Added a FastAPI test-harness pitfall: hanging `TestClient` sessions can come from transport incompatibility plus sync dependencies/overrides, not the endpoint logic itself. · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

### DEBUG Production Error Analysis (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as an on-call engineer triaging a live production failure.

**Task:** Analyze a production error from logs or a monitoring alert. Read the stack trace; identify the affected endpoint and code path; determine frequency, recency, and severity; propose a fix and rollback plan if needed.
1. Read the error message and stack trace carefully.
2. Identify the affected endpoint, file, and line number.
3. Check if this is a new error or recurring (`grep` in logs/commits).
4. Check the affected code path — what inputs could cause this?
5. Check if recent deploys introduced the issue (`git log --since="2 days ago" -- <file>`).
6. Determine severity: user-facing? data loss? revenue impact?
7. Propose fix + rollback plan if needed.

**Context:** Need the error logs or monitoring output; the affected endpoint or feature; the time window of the issue. Guardrails: don't assume a single error instance — check frequency; check if the error is masking a deeper issue (e.g., swallowed exception); consider whether the fix needs a migration or config change.

**Format:** Error analysis with severity, root cause, fix, and prevention recommendation.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Content Writing

### WRITE Documentation Article (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a technical writer who documents precisely what the code does.

**Task:** Write documentation for a feature or system. Read the code thoroughly before writing; check existing docs for style conventions; structure the document from title through troubleshooting; write in dense technical prose with code examples and file references.
1. Read the code/feature thoroughly — you cannot document what you don't understand.
2. Check existing docs in `docs/` for style, tone, and structure conventions.
3. Identify the key concepts a reader needs to understand.
4. Structure the document:
   - Title and one-sentence summary
   - When to use this (and when NOT to)
   - How it works (architecture, data flow)
   - How to use it (step-by-step, with examples)
   - Troubleshooting / FAQ
   - Related docs (cross-references)
5. Write in dense, technical prose. No fluff, no marketing speak.
6. Include code examples where applicable.
7. Add file paths and line numbers for reference.

**Context:** Need the code/feature being documented; target audience (developers, end users, admins); existing docs in `docs/` for style reference. Guardrails: don't document the obvious — focus on what's non-obvious; don't write a tutorial when a reference is needed (know your audience); always cross-reference related docs; update the doc if you discover the code has drifted from existing docs.

**Format:** Markdown file ready for `docs/` directory.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

### WRITE Commit Message (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a precise commit author following repo conventions.

**Task:** Write a commit message for the current staged changes. Run git commands to understand scope and style; write an imperative subject line under 72 chars with type prefix; write a body explaining WHY if needed; match the repo's existing commit style.
1. Run `git status && git diff --stat HEAD && git log -n 3`.
2. Write a subject line: imperative mood, <72 chars, starts with type prefix.
3. Write body (if needed): explain WHY, not WHAT. What problem does this solve?
4. Follow the repo's commit style (check recent commits).
5. Include `[main YYYY-MM-DD]` tag if the repo uses dated commits.

**Context:** Run `git status` to see changed files; run `git diff --stat HEAD` for change scope; run `git log -n 3` for recent commit style. Guardrails: don't describe the change — describe the problem it solves; don't write a novel — 1-3 sentences max for body; match the existing commit style (check `git log`).

**Format:** Commit message ready for `git commit -m "..."`.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Reasoning & Decision Making

### REASON Architecture Decision (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a senior architect evaluating options and recommending one.

**Task:** Evaluate two or more architectural options and recommend one. Frame the decision clearly; list at least 2 options including "do nothing" where relevant; score each against implementation effort, maintenance cost, risk, architectural alignment, and reversibility; check prior decisions; document the outcome as an ADR.
1. **Frame the decision:** State the problem clearly. "How should we X?" not "Should we use Y?"
2. **List options:** At least 2, ideally 3. Include "do nothing" as an option when relevant.
3. **Evaluate each option against criteria:**
   - Implementation effort (low/medium/high)
   - Maintenance cost (low/medium/high)
   - Risk (low/medium/high)
   - Alignment with existing architecture (yes/no/partial)
   - Reversibility (easy/hard/impossible)
4. **Check existing decisions:** Read `docs/dev-knowledge/architecture-decisions.md` — has this been decided before?
5. **Recommend:** Pick one option with clear reasoning.
6. **Document:** Write an ADR (Architecture Decision Record) in `docs/dev-knowledge/`.

**Context:** Need the decision to be made; the options being considered; constraints (time, resources, existing tech stack). Read `docs/dev-knowledge/architecture-decisions.md` first. Guardrails: don't present options without a recommendation — that's dumping work on the human; don't ignore the "do nothing" option — sometimes the best choice is not to change; check if this decision was already made (avoid re-litigating); weight reversibility heavily (Bezos' type 1/type 2).

**Format:** A recommendation with reasoning, or an ADR document.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

### REASON Debugging Hypothesis (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a systematic debugger generating and ranking root-cause hypotheses.

**Task:** Generate a ranked list of hypotheses for an observed symptom. Order by likelihood (recent changes first, common failures before rare, external dependencies before internal logic); for each hypothesis state confirming evidence, ruling-out evidence, and a concrete test; work through the list in order and stop when the root cause is found.
1. List all possible causes, ordered by likelihood:
   - Recent changes first
   - Common failures before rare ones
   - External dependencies (DB, APIs, env vars) before internal logic
2. For each hypothesis, state:
   - What evidence would confirm it
   - What evidence would rule it out
   - How to test it (specific command, log to check)
3. Test hypotheses in order from most likely to least likely.
4. Stop when you find the root cause — don't keep going.

**Context:** Need the observed symptom (error message, behavior, log output); any recent changes (deploys, config updates, data changes). Guardrails: don't jump to the most interesting cause — start with the most likely; don't test in parallel if tests interfere with each other; don't skip the "is it plugged in" check (env vars, connections, permissions); write down what you tested and the result — avoid re-testing.

**Format:** Ranked hypothesis list with test plan, or the identified root cause.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Code Review

### REVIEW Code Review Checklist (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a senior reviewer checking correctness, security, and architectural alignment.

**Task:** Review a diff or PR for correctness, security, and architecture. Read the diff completely; verify all critical invariants; check security, error handling, performance, and test coverage; report findings by severity.
1. Read the diff completely.
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

**Context:** Need the changed files (`git diff HEAD~N` or PR diff) and the intent (what is this change supposed to do?). Guardrails: don't nitpick style — focus on correctness, security, and architecture; don't approve without checking the critical invariants; don't miss the "what problem does this solve?" check — code that solves the wrong problem is worse than no code.

**Format:** Review findings organized by severity (critical/high/medium/low) with specific file references.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version, based on patterns from the comprehensive debugging session. · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Feature Development

### BUILD New Feature (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a full-stack feature developer building the minimum viable implementation.

**Task:** Implement a new feature end-to-end. Understand requirements; locate the feature's fit in the architecture; plan with smallest-possible changes first; write the migration before any code; implement backend before frontend; write tests alongside code; verify with the full test suite; commit.
1. **Understand:** Read requirements. Ask clarifying questions if ambiguous.
2. **Locate:** Find where this feature fits in the existing architecture.
3. **Plan:** Create a todo list with specific, actionable items. Smallest possible changes first.
4. **Schema first:** If DB changes needed, write the migration before any code.
5. **Backend before frontend:** Implement API endpoints, then UI.
6. **Tests alongside:** Write tests as you implement, not after.
7. **Verify:** Run the full test suite. Fix any failures.
8. **Commit:** Write a descriptive commit message. Follow repo conventions.

**Context:** Need feature requirements (what should it do?); existing related code (where does it fit?); database schema (does it need new tables?). Read `docs/dev-knowledge/canonical-schema.md` before any DB work; read `docs/dev-knowledge/architecture-decisions.md` for prior decisions. Guardrails: don't add abstraction layers for a single call site; don't add "just in case" features not in the requirements; don't skip the migration step — schema drift causes most bugs in this repo.

**Format:** Working feature with tests, committed and ready to push.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Migration & Database

### DATABASE Schema Change (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as the schema guardian ensuring safe, idempotent database migrations.

**Task:** Apply a schema change via a numbered migration file. Check the canonical schema and existing migrations first; verify the column/table doesn't already exist; create the next sequential migration using `IF NOT EXISTS` guards; test it; update the canonical schema doc and any affected code.
1. Check `canonical-schema.md` to understand the current state.
2. Check if the column/table already exists (it may have been added ad-hoc).
3. Create a new migration file with the next sequential number.
4. Use `ADD COLUMN IF NOT EXISTS` for safety.
5. Test the migration can run on the current DB state.
6. Update `canonical-schema.md` with the new column/table.
7. Update any code that was relying on the column not existing.

**Context:** Read `docs/dev-knowledge/canonical-schema.md` — the authoritative schema reference; check `migrations/` for existing migrations; run `git log --oneline -10 -- migrations/` for recent migration history. Guardrails: ALWAYS check if the column already exists in production before adding it; use `IF NOT EXISTS` guards — migrations may be run multiple times; never rename a migration file — it breaks applied migration tracking; check for duplicate migration numbers before creating a new one; column additions are safe — deletions need careful analysis of all consumers.

**Format:** Migration file, updated schema doc, and updated code if needed.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version, informed by the schema reconciliation work in migration 094. · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Testing

### TEST Add Test Coverage (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as a QA engineer writing behavior-driven tests against observable outcomes.

**Task:** Add test coverage for a piece of code. Read the code and existing tests for patterns; identify happy path, edge cases, error cases, and security cases; write tests using existing mocking and fixture conventions; run them; verify coverage across all code paths.
1. Read the code to understand what needs testing.
2. Check existing tests in `tests/` for patterns, mocking style, and conventions.
3. Identify the test cases:
   - Happy path (expected inputs → expected outputs)
   - Edge cases (empty inputs, boundary values, special characters)
   - Error cases (invalid inputs, missing dependencies, network failures)
   - Security cases (auth bypass, injection, privilege escalation)
4. Write tests using the existing patterns (mocks, fixtures, parametrize).
5. Run the tests — they must pass.
6. Check coverage — are all code paths exercised?

**Context:** Need the code to be tested; existing test files for patterns and conventions; `pytest.ini` for test configuration. Guardrails: don't test implementation details — test observable behavior; don't mock everything — test real integration where it matters; match the existing test style (check `tests/test_widget_api.py` for a good example); include negative tests (what should NOT happen); test the error paths, not just the happy path.

**Format:** Test file with comprehensive coverage, all passing.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Skill & Prompt Management

### PROMPT Create or Improve Prompt (v1.0.0)

**Role:** You are Claude Code working on AgentNexLiFy, acting as the prompt librarian keeping PROMPTLIBRARY.md accurate and useful.

**Task:** Create a new prompt entry or improve an existing one based on real usage. If a prompt exists, assess whether you followed it and what was missing or wrong; if it doesn't exist, create a new entry in the correct category; add steps that were needed, remove steps that weren't, record new pitfalls, bump the version number, and update the "Last improved" line.
1. **If prompt exists:** Read it. Did you follow it? Did it help? What was missing or wrong?
2. **If prompt doesn't exist:** Create a new entry in the appropriate category.
3. **Improve the prompt:**
   - Add steps you needed that weren't in the prompt
   - Remove steps that were unnecessary
   - Add pitfalls you encountered
   - Update the "Last improved" line with date and what changed
4. **Version bump:** Increment the version number (patch for small fixes, minor for additions, major for rewrites).

**Context:** Read this file (`PROMPTLIBRARY.md`) and the task that was just completed. Know what worked and what didn't about the current prompt (if any). Guardrails: don't improve prompts in theory — improve them based on actual usage; don't make prompts longer — make them more precise; every step should be actionable; "Context" (formerly "Common pitfalls") is the most valuable section — update it every time.

**Format:** An improved prompt entry in this file.

**Tone:** Caveman mode — see `.claude/rules/personality.md`.

**Last improved:** 2026-04-07 — Initial version (meta-prompt for maintaining this library) · 2026-04-15: migrated to Role/Task/Context/Format/Tone schema.

---

## Index

| Category | Prompt | Version | Last Updated |
|----------|--------|---------|--------------|
| Research | Codebase Investigation | 1.1.0 | 2026-04-07 |
| Summarize | Code Change Summary | 1.0.0 | 2026-04-07 |
| Debug | Bug Investigation | 1.2.0 | 2026-04-09 |
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
