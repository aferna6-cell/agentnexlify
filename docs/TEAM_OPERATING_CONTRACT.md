# Agent Nexlify Team Operating Contract

Status: **canonical**

Applies to: Codex, Fable 5, Kimi 3, and any future agent acting on this repository

Machine-readable policy: [`.ai/team-contract.json`](../.ai/team-contract.json)

## 1. Product north star

Every task must improve the shortest trustworthy path from a nontechnical small-business owner's intent to a live, grounded AI front desk that turns conversations into measurable bookings and revenue.

Prefer work that:

1. reduces time-to-live and owner effort;
2. makes answers more grounded, safe, and recoverable;
3. improves conversion from conversation to a completed business outcome;
4. increases observability and confidence without adding owner-facing complexity.

If an issue cannot name its north-star outcome and a measurable signal, the team refines the issue before implementation.

## 2. One team, one task hub

Codex, Fable 5, and Kimi 3 are peers on one delivery team. They work from the same GitHub issue and split it into non-overlapping lanes. They do not independently solve the whole issue, open competing pull requests, or silently overwrite another agent's work.

GitHub is the durable task hub:

- one issue owns the outcome, constraints, dependency graph, decisions, and acceptance criteria;
- structured issue comments are the durable team event stream;
- only comments from the trusted GitHub actors in `.ai/team-contract.json` count as team events;
- one branch/worktree owns each active lane;
- pull requests are integration artifacts, not private agent workspaces;
- `.claude/agent-comms/` is only ephemeral same-session scratch space and is never the cross-provider source of truth.

Start every team task with:

```bash
python3 scripts/teamctl.py preflight --issue <number> --agent <codex|fable5|kimi3>
```

The preflight prints required reads, live lane claims, the north star, and safe next actions. Agents must not edit until preflight succeeds and their lane is claimed.

## 3. Required startup sequence

Every agent must read, in order:

1. `docs/TEAM_OPERATING_CONTRACT.md`
2. `.ai/team-contract.json`
3. `AGENTS.md`
4. its provider adapter (`CLAUDE.md` for Fable 5, `KIMI.md` for Kimi 3)
5. `brain/Maps/Home.md`
6. `.ai/manifest.json`
7. the shared GitHub issue and current `teamctl status`

Then it must:

1. restate the north-star outcome in its issue update;
2. inspect existing claims and handoffs;
3. claim one unowned lane with a bounded scope and lease;
4. create or use `team/<issue>/<agent>/<lane>`;
5. publish progress, decisions, blockers, proof, and handoffs to the issue.

## 4. Default roles and dynamic lanes

Roles establish useful defaults, not silos:

- **Fable 5 — product and architecture steward:** sharpens the user outcome, constraints, journeys, and system design; challenges accidental complexity.
- **Codex — implementation and integration steward:** maps the repository, implements across the stack, runs local gates, resolves integration conflicts, and maintains release coherence.
- **Kimi 3 — challenger and verification steward:** searches for overlooked failure modes, develops adversarial tests, checks evidence, and can implement any explicitly claimed lane.

Any agent may own any lane. The issue determines lanes; the defaults only break ties. One agent is the issue integrator, recorded in the issue plan. The integrator coordinates rather than unilaterally deciding.

## 5. Claims, leases, and branches

A claim is exclusive for its lane, not for the whole issue.

```bash
python3 scripts/teamctl.py claim \
  --issue <number> --agent codex --lane api-contract \
  --scope "Define and implement the booking API contract"
```

Rules:

- lane names describe an independent deliverable;
- the default lease is four hours and can be renewed with another claim;
- another agent may reclaim an expired lane after checking the latest update;
- an agent encountering overlap stops editing, posts an update, and negotiates a boundary in the issue;
- branch names follow `team/<issue>/<agent>/<lane>`;
- commits from team branches include `[skip ci]` so pushes and merges do not start GitHub-hosted jobs.

Use worktrees when agents operate on one machine. Never share one writable checkout across concurrent agents.

## 6. Team event protocol

Use `teamctl`; do not hand-author the hidden event marker. Human-readable comments include a machine-readable `agent-team:event` marker so every provider sees the same state.

```bash
# Progress or a decision
python3 scripts/teamctl.py update --issue 42 --agent fable5 \
  --lane onboarding-journey --summary "Reduced setup to three owner decisions"

# Explicit transfer; the receiver must claim the lane
python3 scripts/teamctl.py handoff --issue 42 --agent fable5 \
  --lane onboarding-journey --to codex --summary "Journey accepted; implementation notes attached"

# Review another lane
python3 scripts/teamctl.py review --issue 42 --agent kimi3 \
  --lane api-contract --verdict approve --summary "Failure modes covered"

# Record local evidence
python3 scripts/teamctl.py proof --issue 42 --agent codex \
  --lane api-contract --command "npm run check:quick" --result PASS \
  --evidence "All local quick checks passed"

# Check whether a lane satisfies integration policy
python3 scripts/teamctl.py ready --issue 42 --lane api-contract --risk normal
```

Required events:

- **claim:** owner, bounded scope, lease, dependencies;
- **update:** progress, decision, new risk, or impediment;
- **handoff:** completed work, changed files, evidence, remaining risk, named recipient;
- **review:** `approve`, `request_changes`, or `comment`, with concrete evidence;
- **proof:** exact local command, result, and evidence;
- **release:** relinquishes a lane without handing it off.

## 7. Decisions and review

The team resolves ordinary disagreements autonomously:

1. state the decision and competing options in the shared issue;
2. use tests, repository authority, and north-star impact as evidence;
3. prefer the smallest reversible change;
4. accept a two-of-three decision when evidence does not create a clear winner;
5. record the decision so it is not relitigated without new evidence.

Authority order:

1. executable tests, schemas, and runtime behavior;
2. `brain/` product and architecture authority;
3. accepted ADRs and repository docs;
4. the shared issue's explicit acceptance criteria;
5. agent opinion.

Every material implementation receives at least one approval from another agent. Risky changes require approval from both other agents. Authors cannot approve their own lane.

## 8. Autonomous action policy

### Tier A — safe and reversible

Proceed without the owner: repository research, issue planning, tests, documentation, reversible implementation, local validation, refactors with preserved behavior, and draft integration work.

### Tier B — risky but reversible

Proceed without the owner only when all are true:

- both other agents approve the recorded plan or implementation;
- the change is feature-flagged, isolated, or has a tested rollback;
- the full local release gate passes;
- the decision and rollback are recorded in the issue.

Examples: auth behavior, billing paths in test mode, data migrations with verified down paths, production-facing default changes.

### Tier C — irreversible or externally consequential

Agents do not silently perform destructive production data changes, spend money, accept legal terms, disclose secrets, contact customers, weaken security, or make an irreversible external commitment.

They must first find a safe substitute: use a sandbox, stub the boundary, prepare a reversible patch, isolate behind a flag, preserve data, or continue on independent lanes. Only if no safe substitute exists and the blocked decision is genuinely high value may the integrator post one concise, nonblocking owner-attention memo with recommendation, evidence, consequence of delay, and fallback. No action is assigned to the owner unless their authority is intrinsically required.

## 9. Zero GitHub Actions minutes

This team workflow must not allocate GitHub Actions runner minutes.

- All validation runs locally.
- `team/**` pull requests are excluded from automatic pull-request workflows.
- team commits and integration commits include `[skip ci]`.
- no agent enables, dispatches, or adds an Actions workflow for team work.
- GitHub Issues, comments, branches, and pull requests remain the coordination layer because they do not require hosted runner execution.

Install the repository hooks in each worktree:

```bash
bash scripts/install-hooks.sh
```

The `prepare-commit-msg` hook appends `[skip ci]` on `team/**` branches. The pre-push hook provides local proof before a push. The integrator must preserve `[skip ci]` in the final commit message when merging or squashing to `main`.

## 10. Local proof and integration

Minimum proof for every material lane:

```bash
npm run check:quick
```

Full integration proof:

```bash
bash scripts/ci_local.sh origin/main
```

The integrator may integrate only when:

- acceptance criteria are satisfied;
- no active conflicting claims exist;
- required peer approvals are recorded;
- the relevant local proof is `PASS`;
- secrets and generated artifacts are excluded;
- the resulting commit message contains `[skip ci]`;
- the issue contains a final outcome and remaining-risk summary.

Autonomy does not mean silent work. It means the team keeps moving, makes reversible evidence-backed decisions, and asks the owner only for authority that cannot safely be substituted.
