# Fill Instructions Before Guessing

## Rule
If I'm about to write code, invoke a tool, or make a decision AND the governing rule/doc/instruction is missing, ambiguous, or contradicted by another source — STOP. Fix the instruction first. Then execute.

Guessing in implementation is noisy but local. Guessing in INSTRUCTIONS compounds across every future session.

## Triggers — stop and fix the instruction when

1. **A hook/command references a tool that isn't installed.** Fix the hook before routing work around it.
2. **A plan file claims a blocker that isn't actually in the codebase.** Verify, fix the plan, or delete the claim.
3. **A rule file's example contradicts current code** (e.g. rule says `tenant_id`, code uses `client_id`). Fix the rule — code wins unless rule is the authority.
4. **An ADR conflicts with an audit recommendation.** Follow the ADR, update the audit to record the rejection + reason.
5. **Two rule files disagree on the same topic.** Reconcile before writing code that follows either.
6. **A command description says "X is installed" but `which X` fails.** Update description.
7. **A CLAUDE.md reference points to a file that doesn't exist.** Fix the link or remove the reference.
8. **A model ID in any doc doesn't match `.claude/rules/model-routing.md`.** Update the stale doc.

## Protocol

When a trigger fires:

1. **Stop the in-progress task.** Do NOT barrel through.
2. **Surface the finding to the user.** Quote the specific file + line.
3. **Propose the fix.** One-line edit if obvious; ask if ambiguous.
4. **Apply the fix.**
5. **Resume original task.**

Cost: 2-5 extra minutes. Value: one canonical source of truth; future sessions don't re-hit the same ghost.

## Counter-examples (do NOT stop)

- Style nits (em-dash vs hyphen) — not a blocker
- Rule is just terse — "ask when unsure" is not ambiguous; it's just short
- Reference is to external resource we can't verify — log a TODO, not a stop
- Rule is slightly out of date but not misleading — defer to next doc-updater pass

## Why this rule exists

Real incidents that motivated it:
- `.claude/settings.json:131-139` blocked `WebFetch` + `WebSearch` routing to `agent-browser` CLI that wasn't installed. Every session that needed web research was forced to either install agent-browser blindly or give up. Hook author assumed the CLI was always present.
- `plans/lead-parser-replacement_plan.md:48` said "local pytest blocked: pyiceberg→C++ build tools." But `pyiceberg` was never in `backend/requirements.txt`. Future sessions saw the plan, believed pytest was blocked, and deferred verification. The ghost blocker wasted verification cycles.
- Audit file claimed a rename was "S effort, 1 line" — ignoring 15+ call sites + an existing ADR that said keep the name. Following audit without reading ADR would have created a half-migration.

Each would have cost <5 min to fix at source. Each cost >30 min of compounded wrong-direction work downstream.

## Enforcement
- Self-discipline when drafting tool calls — ask "is the instruction I'm following trustworthy?"
- `scripts/claude-hooks/invoke-opus-47-features.sh` reminder in UserPromptSubmit
- When in doubt, apply `no-assumptions.md` 80% threshold to the INSTRUCTION, not just the task

## Cross-refs
- `rules/no-assumptions.md` — 80% confidence on TASK interpretation
- `rules/user-rules.md` Rule 7 — honor CLAUDE.md + AGENTS.md
- `rules/user-rules.md` Rule 8 — no half migrations
- `rules/workflow-orchestration.md` — quality gates
