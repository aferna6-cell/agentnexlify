# User Rules — AgentNexLiFy Session Discipline

Four rules the user set on 2026-04-15. Non-negotiable for this project. All four are either enforced by hooks or cross-link to existing rules for reinforcement.

## Rule 1 — Plan First, Build Last
Before ANY implementation: present a plan, get approval, then execute. Plans state files touched, rule mappings, edge cases, commit intent.

**Cross-provider team authorization (2026-07-20):** For an issue governed by `docs/TEAM_OPERATING_CONTRACT.md`, the shared GitHub issue plan and required peer quorum are the approval. Codex, Fable 5, and Kimi 3 do not pause for owner approval on Tier A or contract-compliant Tier B work.

**Why:** prevents wasted work when the user's intent differs from mine. Also gates 2+-file changes through review.

**How to apply:**
- Non-trivial work (2+ files, schema change, new service, architectural shift) → plan in text, wait for explicit "yes" / "looks good" / equivalent
- Trivial work (one-line fix, rename, typo) → execute directly
- Cross-provider issue work → publish the plan, claim lanes, and proceed under the contract without waiting for the owner
- Plan format: bullet list of files, rule mappings where relevant, edge cases, commit intent
- Reinforced by `ultrathink.md` plan-mode gate and `no-assumptions.md` 80% threshold

## Rule 2 — Ask When Unsure
Confidence below 80% on interpretation → ASK. Never guess scope, target, env, or destructive action.

For cross-provider issue work, first resolve uncertainty with repository evidence and a two-of-three peer decision. Ask the owner only when the missing choice requires their intrinsic authority under Tier C and no safe substitute exists.

**Why:** one clarifying question saves hours of wrong-direction work. Session transcripts show many bugs originated from assumed intent.

**How to apply:**
- Use `AskUserQuestion` tool for 2-4 structured choices
- Plain-text question for open-ended clarification
- Show the ambiguity explicitly ("X could mean A or B")
- Full spec: `.claude/rules/no-assumptions.md`

## Rule 3 — Every 15 Messages, Generate a Handoff Summary
Counter hook fires at the 15th, 30th, 45th, … user prompt. Inject directive forcing a summary before responding.

**Why:** long sessions risk context loss, compaction, or model drift. 15-message summary lets user paste into a fresh session without starting over.

**How to apply:**
- Enforcement: `scripts/claude-hooks/message-counter.sh` — reads `.claude/state/message-count`, increments each turn, outputs hookSpecificOutput when `count % 15 == 0`
- Summary format:
  1. What we're working on
  2. Decisions made this session
  3. Files changed + key paths (file:line references)
  4. Open questions / blockers
  5. Concrete next step
- Reset counter: delete `.claude/state/message-count` to restart cadence

## Rule 4 — Short Tasks Use Sonnet or Haiku; Opus Only for Deep Multi-Step Work
Tasks under ~30s → Haiku or Sonnet. Opus reserved for planning, architecture, complex decomposition.

**Why:** Opus is ~5x Sonnet, ~15x Haiku per token. Codeburn 30-day snapshot showed 99% of spend going to Opus ($312.42 of $316.13). Most of that was mechanical work that Sonnet/Haiku could have handled.

**How to apply:**
- If running in an Opus session and the task is mechanical (rename, format, lookup, grep, one-file edit) → delegate via `Agent` with `subagent_type` that routes to Sonnet/Haiku
- Keep Opus turns for: plan generation, architecture review, security-critical code review, decomposing ambiguous requirements
- Cross-reference: `.claude/rules/model-routing.md` advisor-executor pattern (Opus plans → Sonnet executes → Haiku cleans)

## Engineering Discipline (rules 5-12 added 2026-04-15)

## Rule 5 — Don't Speed Toward "Working"
Slow is smooth, smooth is fast. A feature that boots but leaks invariants is worse than no feature. Before the next action, say what the step is and why.

**Why:** pressure to ship degrades code review reflexes. Regressions slip when I chase green instead of correct.

**How to apply:**
- Before every tool call that mutates state, state the intent in the user-facing text
- If I catch myself wanting to "just try this and see," stop and think instead
- Urgency is almost never real in an async dev loop — user is not watching the clock

## Rule 6 — Stop Mid-Task to Rethink or Refactor, Unprompted
If I'm halfway through implementation and notice the design is wrong, stop. Rethink. Tell the user. Don't barrel on because the plan said to.

**Why:** better to waste 15 minutes of planning than to ship a bad foundation and spend days undoing it.

**How to apply:**
- Smells that trigger a stop: branching logic growing past 3 levels, copy-paste of the same 5 lines twice, a test that needs mocking to exercise, a param list past 5 args
- On stop, summarize the smell and propose a refactor. In cross-provider issue work, record it and obtain peer quorum; otherwise ask for go/no-go.
- Never silently pivot — always surface

## Rule 7 — Never Ignore CLAUDE.md or AGENTS.md
Both files are the source of truth. If a rule in them conflicts with my instinct, the file wins. If CLAUDE.md says `client_id not tenant_id`, I use `client_id` even if a function-name hint says otherwise.

**Why:** those files are distilled from past bugs. Ignoring them re-opens fixed bugs.

**How to apply:**
- Both files autoload into system prompt — no excuse for forgetting
- On every schema/API touch, check the relevant section (`Critical Rules` in CLAUDE.md, agent roster in AGENTS.md)
- If a rule is stale, UPDATE the file, don't route around it

## Rule 8 — No Half-Done Migrations
A migration finishes in one PR or it stays unstarted. Never leave the codebase with some call sites on the old API and some on the new — that's where bugs live.

**Why:** mid-migration state is ambiguous. Future me (or future Claude) can't tell which branch is canonical. Users hit inconsistencies.

**How to apply:**
- Before starting a rename/signature change, grep ALL call sites
- If the migration touches too many files to fit one PR, plan it as staged deprecation with the OLD path still working until the last call site moves
- Never ship a commit titled "WIP migration"

## Rule 9 — Don't Extend God Classes — Factor Them Out
If a file is already >600 lines and I'm about to add more, stop. Factor the existing code into modules first. Then add.

**Why:** god classes are where bugs compound. Every additional concern makes the blast radius bigger.

**How to apply:**
- Check file size before editing: `wc -l <file>`
- At 600+ lines and adding new responsibility, propose a split first
- New concerns → new file; only extend existing files when the new code is the same concern as what's already there

## Rule 10 — Never Change Tests to Match My Assumed Intent
A failing test is either a real bug OR a wrong test. I do not get to decide it's a wrong test without evidence. Default assumption: the code is wrong, the test is right.

**Why:** changing tests to match code is how regressions stop being regressions. It's the single fastest path to silent rot.

**How to apply:**
- On test failure, FIRST read the test to understand what contract it encodes
- Change code to meet the contract; if the contract is wrong, raise it as a question, don't quietly edit
- If editing a test, commit message must state WHY the old contract was wrong (with link to spec or prior decision)

## Rule 11 — Do Additive Things I Didn't Ask For (Without Scope Creep)
When I notice a small adjacent win while doing the main task — a missing log line, a misnamed variable in the file I just touched, a doc typo — ship it. Don't wait for permission on obvious improvements.

**Why:** compounding wins. A codebase improves one small fix at a time.

**How to apply:**
- Only additive, reversible, obviously-right changes (logs, docs, typos, rename to match convention)
- Must be in a file already touched this session — no wandering
- Mention it in the summary ("also fixed typo in comments at line 42")
- NEVER: refactoring, api changes, new features, anything that could surprise user

## Rule 12 — Create New Files Instead of Bloating Existing Ones
When adding a concern, default to a new file. Only extend existing files when the new code serves the SAME concern as what's already there.

**Why:** small files are easier to review, refactor, delete. Bloat creates merge conflicts and hides dead code.

**How to apply:**
- Ask: "is this the same concern as what the file already does?" If no → new file
- Prefer many small modules over one catch-all `utils.py`
- One exported thing per file where reasonable

## Enforcement Summary
| Rule | Enforcement |
|---|---|
| 1. Plan first | Self-discipline + `ultrathink.md` plan-mode gate |
| 2. Ask when unsure | Self-discipline + `no-assumptions.md` hook (existing) |
| 3. 15-msg summary | `message-counter.sh` hook (non-bypassable) |
| 4. Model routing | Self-discipline + `model-routing.md` cross-ref |
| 5. Don't speed | Self-discipline — state intent before each action |
| 6. Stop mid-task to rethink | Self-discipline — surface smells, never silent pivot |
| 7. Honor CLAUDE.md / AGENTS.md | Both autoload; no excuse |
| 8. No half migrations | Pre-work: grep all call sites |
| 9. Factor god classes | Pre-edit: `wc -l`; >600 lines → split first |
| 10. Don't change tests | Code is wrong until test-author proves otherwise |
| 11. Additive wins | Ship small, in-scope, reversible improvements |
| 12. New files over bloat | Default to new module |

## Scope
These rules apply to AgentNexLiFy sessions only (this repo). They do not bind sessions in other projects.
