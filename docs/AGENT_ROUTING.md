# Agent Routing Policy

Use this policy when deciding which coding agent or model class should work on
AgentNexLiFy tasks. The goal is not loyalty to one tool. The goal is to route
each task to the cheapest worker that can complete it safely, then reserve
premium reasoning for high-risk work.

## Current Default

Autopilot remains conservative:

- Classifier: Claude Haiku.
- Executor: Codex with Claude Sonnet-grade instructions.
- Reviewer comment handler: Claude Sonnet brief, Codex execution.
- Human review and merge remain mandatory.

Do not route production autopilot to Kimi Code, Agent Swarm, or another
low-cost worker until the repo-specific eval harness shows repeatable quality.

## Routing Labels

These GitHub labels classify work before a human or future router chooses an
agent. They are advisory unless paired with `ai-ready`.

| Label | Meaning | Default route |
| --- | --- | --- |
| `ai-routine` | Low-risk scoped implementation, cleanup, small parser work, small UI polish | Low-cost candidate after eval |
| `ai-docs` | README, docs, playbooks, sales assets, skill wording | Low-cost candidate after eval |
| `ai-tests` | Test generation, test refactors, focused fixtures, coverage around stable behavior | Low-cost candidate after eval |
| `ai-risky` | Auth, billing, pricing, Stripe, Supabase RLS, migrations, secrets, legal, customer communication, production deploy logic, runtime AI policy | Premium-only with human review |

`ai-ready` is still required before autopilot may attempt an issue. Routing
labels do not override the autopilot workflow contract.

## Route Matrix

### Premium Codex / Claude

Use for:

- Auth, permissions, Supabase RLS, and tenant isolation.
- Stripe, billing, pricing, upgrades, invoices, and payment webhooks.
- Database migrations, destructive data changes, and schema compatibility.
- Production deployment, secrets, domain, or infrastructure changes.
- Runtime customer-facing AI behavior and prompt policy.
- Large cross-surface refactors or ambiguous architecture.

Rules:

- Require a human-readable plan before implementation.
- Run the broadest relevant local checks.
- Require human review before merge.
- Do not use `--yolo`, Agent Swarm, or unreviewed write modes.

### Low-Cost Routine Candidate

Use only after eval success for:

- Small refactors with clear acceptance criteria.
- Parser cleanup.
- Boilerplate.
- Mechanical duplication removal.
- Non-sensitive frontend or backend polish.

Rules:

- Work in an isolated branch or worktree.
- Keep the diff small.
- Run focused tests plus `npm run check:quick`.
- Escalate to premium if the task touches a sensitive surface.

### Low-Cost Docs Candidate

Use only after eval success for:

- README updates.
- Client setup docs.
- Demo scripts.
- Skill wording.
- Internal playbooks.

Rules:

- Avoid changing product behavior.
- Keep docs ASCII unless the file already uses another charset.
- Run `npm run eval:agent-routing` and relevant docs checks.

### Low-Cost Tests Candidate

Use only after eval success for:

- Unit tests around stable APIs.
- Focused regression tests.
- Fixture cleanup.
- Test-only refactors.

Rules:

- Do not rewrite product code unless explicitly asked.
- Match existing test style.
- Run the exact test files touched.

### Batch Candidate

Use for:

- Many similar docs assets.
- Client starter kit variants.
- Bulk issue triage drafts.
- Large prompt or content transformations.

Rules:

- Use read-only or generated-output mode first.
- Review a sample before applying changes broadly.
- Never batch-edit auth, billing, migrations, RLS, secrets, or deploy logic.

## Hard Safety Rules

These rules apply to every agent:

1. Never use `--yolo` in the main checkout.
2. Never use Agent Swarm or broad batch execution on sensitive surfaces.
3. Never allow unreviewed writes to auth, billing, pricing, Stripe, Supabase
   RLS, migrations, secrets, legal, customer communications, production deploy
   logic, or customer-facing runtime AI policy.
4. Never let a low-cost worker commit, push, merge, label, or release.
5. Escalate to premium routing when task scope is unclear or confidence drops.

## Eval Before Adoption

Use the repo-specific harness before adding a new worker to the routing matrix:

```powershell
npm run eval:agent-routing
python scripts/run_python.py scripts/evaluate_agent_routing.py --list
python scripts/run_python.py scripts/evaluate_agent_routing.py --export-prompts output/agent-routing-eval
```

For each candidate worker, run the exported prompts in an isolated worktree and
score:

- Pass/fail against acceptance criteria.
- Verification command result.
- Diff quality.
- Time to completion.
- Estimated cost.
- Human cleanup required.

Promote a low-cost worker only after it passes routine, docs, and tests tasks
without touching sensitive surfaces or creating cleanup churn.
