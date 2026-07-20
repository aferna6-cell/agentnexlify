# Agent Routing Policy

Use this policy when deciding which coding agent or model class should work on
AgentNexLiFy tasks. The goal is not loyalty to one tool. The goal is to route
each task to the team member best positioned to complete it safely, then use
peer review and local evidence in proportion to risk.

## Cross-Provider Product Team

Codex, Fable 5, and Kimi 3 are one autonomous peer team for issue-driven
product work. The canonical rules are in `docs/TEAM_OPERATING_CONTRACT.md` and
`.ai/team-contract.json`.

- Fable 5 defaults to product and architecture stewardship.
- Codex defaults to implementation and integration stewardship.
- Kimi 3 defaults to challenge and verification, and may implement any claimed lane.
- All three work from one GitHub issue and claim non-overlapping lanes with
  `python3 scripts/teamctl.py`.
- Material work requires another agent's approval. Risky but reversible work
  requires both other agents, a flag or tested rollback, and the full local gate.
- Irreversible or externally consequential work is replaced with a safe local
  substitute where possible; intrinsic owner authority is the only reason for
  a nonblocking owner-attention memo.
- Team proof is local. Team and integration commits contain `[skip ci]`; no
  GitHub Actions workflow is dispatched for this path.

Kimi 3 may join discovery, planning, challenge, and review immediately. Its
promotion into a production-autopilot executor remains separately governed by
the routing eval; that legacy autopilot restriction does not make it an
independent team or prevent explicitly claimed, peer-reviewed product lanes.

## Current Default

The unattended, single-agent autopilot workflow remains conservative and is
separate from the cross-provider product team:

- Classifier: Claude Haiku.
- Executor: Codex with Claude Sonnet-grade instructions.
- Reviewer comment handler: Claude Sonnet brief, Codex execution.
- Its existing human review and merge requirements remain mandatory.

Do not route legacy production autopilot to an unevaluated low-cost worker
until the repo-specific eval harness shows repeatable quality.

## Routing Labels

These GitHub labels classify work before a human or future router chooses an
agent. They are advisory unless paired with `ai-ready`.

| Label | Meaning | Default route |
| --- | --- | --- |
| `ai-routine` | Low-risk scoped implementation, cleanup, small parser work, small UI polish | Low-cost candidate after eval |
| `ai-docs` | README, docs, playbooks, sales assets, skill wording | Low-cost candidate after eval |
| `ai-tests` | Test generation, test refactors, focused fixtures, coverage around stable behavior | Low-cost candidate after eval |
| `ai-risky` | Auth, billing, pricing, Stripe, Supabase RLS, migrations, secrets, legal, customer communication, production deploy logic, runtime AI policy | Cross-provider Tier B/C policy; legacy autopilot blocked |

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

- Require a shared, human-readable issue plan before implementation.
- Run the broadest relevant local checks.
- Require both other team agents for Tier B work; legacy autopilot still requires human review.
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
4. Cross-provider agents may commit and push explicitly claimed team lanes with
   local proof and `[skip ci]`; integration still obeys the peer-review quorum.
5. Legacy autopilot workers remain unable to merge, label, or release.
6. Escalate to premium peer review when task scope is unclear or confidence drops.
7. Never spend GitHub Actions runner minutes on cross-provider team work.

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

Promote a low-cost worker into the legacy unattended autopilot only after it
passes routine, docs, and tests tasks without touching sensitive surfaces or
creating cleanup churn. The cross-provider team may use it earlier in claimed,
peer-reviewed lanes because the shared issue, approvals, and local proof are
the control boundary.
