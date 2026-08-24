# Audit — Anthropic agent-management guidance vs AgentNexLiFy

**Date:** 2026-08-24
**Scope:** Claude Managed Agents platform surface + Anthropic's long-running-agent doctrine, mapped against this repo's design-time control plane (`.claude/`) and runtime (`backend/services/managed_agents*.py`, `config/managed_agents.yaml`, `scripts/managed_agents/`).

**Verdict:** This repo does not have an agent-doctrine problem. It has already *written down* almost every practice Anthropic teaches — adversarial evaluators, weighted rubrics, anti-sycophancy prompts, verdict loops, veto-authority fan-out, LLM graders at the hook layer. The problem is that a large share of it is **specified but never wired**, and the parts that do run are pinned to models this repo's own docs call legacy. The highest-value work here is finishing and pruning, not building.

---

## 0. Sourcing caveat — read this first

The prompt referenced "a 37 minute Anthropic video on how to use managed agents." **I could not uniquely identify that video**, and I won't pretend otherwise:

- YouTube is IP-blocked from this container, so no transcript could be pulled directly.
- The viral posts describing a "free 37-minute Anthropic guide to building AI agents" ([Threads](https://www.threads.com/@aliansari0/post/DY9oFt8l2Wg), [X](https://x.com/mikenevermiss/status/2086591051041587708), ~2026-05-30) do not link a video.
- The nearest official candidates have different runtimes: ["Ship your first Managed Agent"](https://claude.com/code-with-claude/session/ldn-ext-ship-your-first-managed-agent) (Isabella He, Code w/ Claude London, **45 min**) and ["Build Agents That Run for Hours"](https://sozai.app/transcript/anthropic-workshop-build-long-running-agents/) (Prabaker & Wilson, **75 min**).

So this audit is grounded in the **primary sources those talks teach from** — the Managed Agents docs on `platform.claude.com`, Anthropic's [managed-agents engineering post](https://www.anthropic.com/engineering/managed-agents), the [multi-agent systems guidance](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them), and the full long-running-agents workshop transcript. Every finding cites one of those or a file in this repo. **No recommendation rests on the unidentified video.** Send the link and I'll diff its specifics against this.

---

## 1. The doctrine, in five claims

1. **Self-evaluation is a trap.** A model grading its own work declares half-built features done. Training a harsh *standalone* critic is "very tractable"; training a self-critical builder is not.
2. **Compaction ≠ coherence.** Lossy summaries drift. Structured handoffs into clean contexts beat compaction on long runs.
3. **Subjective quality is gradable.** Write opinions down as a weighted rubric. Anthropic's app rubric weights Design / Originality / Craft / Functionality — deliberately away from functionality alone.
4. **Read traces obsessively.** The debugging loop is reading agent transcripts line-by-line to find where model judgment diverges from yours.
5. **Delete harness as models improve.** Opus 4.6 held 12 hours with minimal scaffolding vs ~1 hour for 3.7. Moving 4.5 → 4.6 they dropped context-resetting and per-sprint evaluation entirely: **half the cost, same runtime.** Scaffolding written for a weaker model becomes dead weight you keep paying for.

Plus the cost discipline: multi-agent setups burn **3–10× the tokens** of single-agent. Only three things justify it — context protection, parallelization, specialization.

---

## 2. What this repo already gets right

This is a genuinely strong control plane. Credit where due:

| Doctrine | Where it lives |
|---|---|
| **Weighted rubric** (claim #3) | `.claude/agents/gan-evaluator.md:117` — `design*0.3 + originality*0.2 + craft*0.3 + functionality*0.2`, PASS threshold 7.0, with a 1–10 calibration ladder at `:106-113` anchored to human-dev quality. This is Anthropic's own rubric, independently arrived at. |
| **Anti-sycophancy** (claim #1) | `gan-evaluator.md:25-32` — "Your natural tendency is to be generous. Fight it… Do NOT talk yourself out of issues you found." |
| **Builder must not self-judge** (claim #1) | `gan-generator.md:18-23` — "Don't self-evaluate — Your job is to build, not to judge." |
| Structured handoff, not compaction (claim #2) | `opus-advisor.md` → file brief → `sonnet-executor.md`, with a 15-tool-call budget on the advisor (`:49`) |
| Adversarial fan-out with veto | `plan-review-fanout/SKILL.md:44-81` — 8 specialists batched in one turn, `PASS/CONCERN/VETO`, 5 holding veto authority |
| Verdict loop with bounded re-dispatch | `compound-engineering/SKILL.md:56` — Reviewer `PASS/FIX/BLOCK`, VerticalChecker `ALL CLEAR/WARNINGS/BLOCKED` |
| Debate with kill authority | `subconscious/SKILL.md:93-108` — Sonnet ideates 5, Opus challenges, verdict `SURVIVES/WEAKENED/KILLED`, one winner |
| LLM graders at the hook layer | `.claude/settings.json:106-110` (pre-push commit review → `BLOCK`/`PASS`) and `:202-206` (post-edit security scan → exit 2) — both on Haiku, correctly cheap |
| Adversarial *human*-layer peer | `docs/TEAM_OPERATING_CONTRACT.md:69` — Kimi 3's standing role is challenger; 2-of-3 quorum, no self-approval (`:147`) |
| Real Managed Agents client | `backend/services/managed_agents.py` — correct beta header, SSE, retry/backoff, and (`:411-429`) the *correct* terminal-state gate that doesn't break on bare `session.status_idle` |
| Agents as versioned config, not code | `config/managed_agents.yaml` is the source of truth; `provision.py` is idempotent and never creates agents in the hot path |
| Least-privilege tools | Per-agent toolsets with `default_config.enabled: false` + explicit allowlists (`lead_qualifier`, `support_agent`, `field_monitor`) |
| Autonomy gates as code, not prompts | `scripts/autonomy/gates.py` — value floor 0.35, risk allowlist, 4 PRs/day, deploy-pressure ceiling 60, `preflight()` refuses dirty tree or `main`; verify runs `ci_local.sh` **in-process** rather than asking the agent whether its own work passed |

The hosted product is genuinely in production, not a prototype: `lead_qualification.py`, `document_drafting.py`, `support_agent.py`, `structured_extractor.py`, `appointment_booker.py` and `routers/managed_agent_runs.py` all create real sessions, and `widget_chat_fallback.py:75` puts it on the live widget path.

---

## 3. Gaps, ranked

### G1 — The flagship GAN loop has never been run (HIGH)

The three GAN agents are the best expression of doctrine claims #1 and #3 in the repo. They are also dead:

- `gan-harness/` — the directory all three agents read and write (`spec.md`, `eval-rubric.md`, `generator-state.md`, `feedback/feedback-NNN.md`) — **does not exist in the repo.**
- **No driver.** Grepping `gan-harness|gan-planner|gan-generator|gan-evaluator` across `.claude/`, `scripts/`, `package.json`, `docs/` hits only the three agent files plus three docs that *mention* them. No script, no slash command, no skill invokes them.
- `docs/AGENT_SYSTEM_PLAN.md:109` already classifies them as **"experimental / research harnesses"** and names `coordinator` the canonical orchestrator instead.

Meanwhile all three are pinned `model: opus` — the most expensive tier — for a loop nothing calls.

This is the sharpest instance of a pattern that repeats below: the doctrine is written down correctly and then not connected to anything. It is also, per doctrine claim #5, a decision that has been deferred rather than made. Either wire it or delete it; leaving three Opus-pinned agents as unreferenced spec is the one option with no upside.

### G2 — The agent fleet runs on legacy models (HIGH)

`config/managed_agents.yaml` pins **7 of 8** production agents to models `CLAUDE.md` itself classifies as "legacy-but-valid":

| Agent | Model | Status per `CLAUDE.md` |
|---|---|---|
| `lead_qualifier` `:35`, `support_agent` `:211`, `field_monitor` `:375` | `claude-sonnet-4-6` | legacy |
| `document_drafter` `:86`, `codebase_reviewer` `:164`, `deep_researcher` `:323`, `data_analyst` `:432` | `claude-opus-4-7` | legacy |
| `structured_extractor` `:276` | `claude-haiku-4-5-20251001` | current |

The control plane is worse: **98 references to `claude-opus-4-7`, 3 to `claude-opus-4-8`, 0 to `claude-opus-5`** — and `claude-opus-5` is a current model ID (the Managed Agents docs use it in their canonical coordinator example). `.claude/rules/opus-4-7.md` still calls itself the "Canonical Reference"; 21 files under `.claude/` reference the 4.7 era; `advisor_executor.py:61` and `managed_agents_registry.py:14` both default the advisor to `claude-opus-4-7`.

This is `fill-instructions-before-guessing.md` trigger #8 — *"a model ID in any doc doesn't match `model-routing.md`"* — firing at scale, and doctrine claim #5 inverted.

Also: **`.claude/agents/vertical-checker.md` has no `model:` pin at all** (same for `a11y-architect.md`, `devops.md`), so the compound pipeline's terminal gate silently inherits the session model — Opus, per the project default. That's an unpriced Opus call on every pipeline run.

### G3 — Cost control is documented but not implemented (HIGH)

Two independent failures here:

**Advisory budgets don't exist in code.** `.claude/rules/task-budgets.md` assigns budget tiers to `llm_runtime.py`, `advisor_executor.py`, `managed_agents_registry.py`, and `scheduled_jobs.py`. **None of those files contain `task_budget` or the `task-budgets-2026-03-13` header.** The rule describes intent, not shipped code — and reads as though it were shipped.

**Hard budgets aren't in the vocabulary.** That rule is built entirely around Messages-API `task_budget`: token-denominated, *advisory*, model self-paces. It never mentions Managed Agents **session budgets**, which are a different primitive — a **hard dollar cap in cents**, enforced by the platform between model requests. `ManagedAgentsClient.create_session` (`managed_agents.py:278`) has no `budget` param, so no autonomous session has a spend ceiling of any kind.

Semantics to know before wiring it: the cap is checked *between* requests, so a session lands a fraction past it (a 50¢ cap can stop at 53¢); removing a budget is **one-way** — a session that had one removed can never be given a new one; multiagent sessions share **one** budget across all threads, advisor consultations included.

For scale: Anthropic's own retro-game-maker demo ran ~6 hours for ~$200. An unbudgeted autonomous loop is not a theoretical risk.

### G4 — Seven platform primitives shipped since April are unused (HIGH)

Grep confirms **zero** occurrences of `multiagent`, `coordinator`, `deployment`, `memory_store`, `webhook`, or `effort` anywhere in the Managed Agents surface. `vault` appears only as a pass-through `vault_ids` param — nothing creates a vault.

| Primitive | What it does | What it would replace here |
|---|---|---|
| `multiagent` coordinator | Roster of delegates, each in a context-isolated **session thread**, sharing one sandbox | Nothing — no runtime fan-out exists |
| **`advisor` roster entry** | Native "consult a stronger model mid-turn," delivered as a thread event | The hand-rolled `advisor_executor.py` (346 lines) |
| Session `budget` | Hard dollar cap, idle at `budget_reached`, resumes when raised | Nothing (G3) |
| Scheduled deployments | Cron + IANA timezone, per-run budget, run records, auto-pause on failure | 16 GitHub Actions cron workflows |
| Memory stores | Versioned, auditable, redactable cross-session memory at `/mnt/memory/` | The file-based `memory/` system |
| Vaults | Per-end-user credentials substituted **at egress** — the agent never sees the secret | Nothing |
| Webhooks | Push delivery of session/deployment/credential events | Polling |

The **advisor** is the sharpest. `.claude/rules/advisor-consult.md` describes in detail a pattern the platform now ships natively:

```json
"multiagent": { "type": "coordinator",
  "agents": [{"type": "advisor", "model": "claude-opus-4-8"}] }
```

One caveat before adopting: Opus 5 is a *redacted-result* advisor — your client sees a `[{"type":"redacted"}]` placeholder while the agent reads the full advice server-side. Opus 4.8 returns readable advice on the event stream. Given doctrine claim #4 (read the traces), pick 4.8.

### G5 — Weekly digest burns CI runner minutes for no reason (MEDIUM, cheap fix)

`.github/workflows/field-monitor-weekly.yml` provisions an `ubuntu-latest` runner every Monday 12:00 UTC purely to invoke a Managed Agent that runs on Anthropic's infrastructure. The runner checks out the repo, waits, and commits a Markdown file.

That sits oddly against the team contract in `CLAUDE.md`, which requires `[skip ci]` on team commits specifically "so no GitHub Actions runner minutes are allocated," and against `scripts/autonomy/ROUTINE.md:4-7`, which chose cloud Routines over Actions precisely because Actions are dark and hit spending limits. A scheduled deployment does the same job with native cron, per-run budget, run records, webhooks — and **zero** runner minutes. Five or six of the 16 cron workflows are LLM-driven and are candidates for the same move.

### G6 — Control-plane drift: counts, dead links, broken skills (MEDIUM)

Every one of these is a `fill-instructions-before-guessing.md` trigger, and they compound because they're what future sessions read first:

- **Counts are wrong everywhere.** `CLAUDE.md` says 57 agents (actual **60**). `.claude/rules/claude-execution-layers.md` says "50+ skills, 19 commands, 30+ hooks, 57 agents" (actual **79 skill dirs, 21 commands, 31 hook entries, 60 agents**).
- **`.claude/TEAM.md:20`** claims 16 agents and its model table is wrong on 4 rows — `gan-generator` and `gan-evaluator` listed `sonnet` (both actually `opus`), `security-reviewer` listed `opus` (actually `sonnet`), `vertical-checker` listed `sonnet` (actually unpinned).
- **Six skills are non-loadable, in the repository itself.** `accessibility`, `deploy-to-vercel`, `frontend-design`, `nodejs-backend-patterns`, `nodejs-best-practices`, `seo` are 24–44 byte plain-text files containing `../../.agents/skills/<name>`. These were meant to be symlinks, and it is not a local checkout artifact: `git ls-files -s .claude/skills/accessibility` returns mode **`100644`** (regular file), not `120000` (symlink). They are committed broken, so **every clone gets six dead skills**. Real content exists at `.agents/skills/`.
- **Advertised commands don't exist.** `eval-harness` advertises `/eval define|check|report`; `.claude/TEAM.md:76-78` references `/orchestrate` and `/compound`. None exist in `.claude/commands/`.
- **`appointment_booker` is a half-wired 9th agent** — it has a registry accessor (`managed_agents_registry.py:231`, reading `os.environ` directly because the field was never added to `Settings`) and a full 316-line service, but **no `config/managed_agents.yaml` entry**, so `provision.py` never creates it. `APPOINTMENT_BOOKER_AGENT_ID` must be set by hand. That's a `user-rules.md` Rule 8 half-migration sitting in a production path.
- **Advisor budget drift.** `advisor_executor.py:62` sets `max_tokens=800`; `.claude/rules/advisor-consult.md:47` says it was "bumped to 1200 for headroom" on the 4.7 tokenizer. Code is at the old value, and the rule warns the cost model breaks if this is wrong.

### G7 — Two stale claims in the Managed Agents client (LOW, but load-bearing)

- **`managed_agents.py:4-8`** justifies the raw-HTTP wrapper because "the currently-pinned SDK version (0.42.0) predates the `client.beta.agents` bindings." `backend/requirements.txt:15` pins `anthropic>=0.95.0,<1`. The stated reason no longer holds. (I could not verify the bindings — `anthropic` isn't installed in this container — so confirm before ripping anything out.)
- **`managed_agents.py:402,415`** point readers at `shared/managed-agents-client-patterns.md` for reconnect and terminal-state patterns. **That file does not exist anywhere in the repo.** The patterns are correctly implemented in the code, so this is a dead pointer rather than a wrong one — but per the rule, fix the reference rather than route around it.

---

## 4. Recommendations

Ordered by value-per-hour. Each is independently shippable.

**R1 — Decide the GAN loop's fate (HIGH value, S effort to delete / M to wire).** This is a decision, not a task, and it has been deferred long enough that three Opus-pinned agents sit unreferenced. Two honest options: (a) write the driver — a `/gan` command or `scripts/gan/run.py` that creates `gan-harness/`, runs planner → generator ↔ evaluator until weighted ≥ 7.0, capped at N iterations — and use it on one real frontend surface; or (b) delete all three and record in `docs/AGENT_SYSTEM_PLAN.md` that `plan-review-fanout` + `compound-engineering` cover the adversarial-evaluation need. **Do not leave it as-is.** If you wire it, note the workshop's own finding that per-sprint evaluation became unnecessary on newer models — evaluate at end-of-generation, not every sprint.

**R2 — Model-ID sweep (HIGH value, S effort).** Move the 7 legacy agents in `config/managed_agents.yaml` to current IDs; pin `model:` on the 3 unpinned `.claude/agents/` files (`vertical-checker` especially — it should probably be Sonnet, not the inherited Opus); update the advisor defaults at `advisor_executor.py:61` and `managed_agents_registry.py:14`. Then reconcile the rules: rename `opus-4-7.md` to a model-agnostic `opus-current.md` or fold it into `model-routing.md`, so there is one canonical table instead of a rule file named after a superseded model. Take `effort` while you're there — the agent `model` field accepts `{"id": ..., "effort": "high"}`, which the YAML doesn't use at all. **Ship as one PR:** `user-rules.md` Rule 8 forbids a half-done migration, and with 98 call sites a partial sweep creates exactly the ambiguity that rule exists to prevent.

**R3 — Make the budget rule true (HIGH value, S effort).** Two parts. First, add a `budget` param to `ManagedAgentsClient.create_session` and set a hard cap on every non-interactive session (leave interactive widget chat uncapped, as the rule already says). Second, correct `.claude/rules/task-budgets.md`: mark the `task_budget` call-site table as **not yet implemented**, and add a section distinguishing hard session budgets from advisory task budgets. Right now a reader of that rule believes both exist; neither does.

**R4 — Field monitor → scheduled deployment (MEDIUM value, S effort).** Add `/v1/deployments` to the client and migrate `field-monitor-weekly.yml`. Cleanest pilot: low blast radius, obvious win, proves the deployment path before touching `kb-autopopulate` or `ai-auto-improve`. Watch the DST note — schedule outside 01:00–03:00 local, since wall-clock times that don't exist on spring-forward day never fire.

**R5 — Fix the control-plane drift in G6 (MEDIUM value, S effort).** The six broken skill stubs and the phantom commands are the urgent half — a skill that can't load is worse than one that doesn't exist, because the index claims it's there. Fix the counts in `CLAUDE.md`, `claude-execution-layers.md`, and `TEAM.md` in the same pass, and either add `config/managed_agents.yaml` entry for `appointment_booker` or remove its accessor and service. Consider a `scripts/check_agent_system.py` assertion on the counts so they can't drift again — the guardrail already exists, it just doesn't check this.

**R6 — Pilot the native advisor (MEDIUM value, M effort).** Add `multiagent` to `create_agent`, then try the advisor roster entry on **one** agent — `document_drafter` is the right candidate (real reasoning, not latency-critical). Compare quality and cost against `advisor_executor.py` on identical inputs before migrating anything else. Use `claude-opus-4-8` so advice is readable on the event stream. Keep `advisor_executor.py` until the pilot wins; don't migrate on faith.

**R7 — Fix the two stale claims in G7 (LOW value, XS effort).** Ten minutes, and it stops the next session re-deriving the same conclusion.

---

## 5. What NOT to do

- **Don't build a multi-agent orchestration layer because the primitive now exists.** The guidance is blunt: 3–10× tokens, and "teams invest months building elaborate multi-agent architectures only to discover that improved prompting on a single agent achieved equivalent results." Six of eight agents here are single-purpose and should stay that way. `multiagent` earns its cost for `document_drafter` (advisor) and possibly `deep_researcher` (parallel source fan-out). Nothing else has a case yet.
- **Don't add another orchestrator.** There are already five overlapping ones — `coordinator` (canonical), `compound-engineering`, `worktree-orchestrator`, `team-orchestration`, `plan-review-fanout` — plus four autonomous loops (`issue-to-pr-loop`, `build-loop`, `autopilot-loop` legacy, `subconscious`) and the unarmed `scripts/autonomy/` graph. Doctrine claim #5 says the move is to delete, not add.
- **Don't migrate `memory/` to memory stores yet.** `.claude/rules/memory-hygiene.md` already implements confidence scoring, freshness, and eviction — which memory stores do *not* give you. Memory stores add versioning, audit, and redaction. Different problems. Revisit only when cross-session memory needs to reach production tenant agents.
- **Don't attach a memory store `read_write` to any tenant-facing agent.** The docs carry an explicit warning: a prompt injection through untrusted input writes into the store, and later sessions read it back as trusted memory. `support_agent` and `lead_qualifier` both ingest untrusted user text. `read_only` or nothing.
- **Don't route tenant OAuth through vaults without re-reading the isolation model.** Vaults are **workspace-scoped** — anyone with an API key for the same workspace can reference them at session creation. For a multi-tenant SaaS whose first design principle is tenant isolation, that boundary needs deliberate design, not a drop-in.

---

## Appendix — unverified

Two things I could not confirm from this checkout, flagged so nobody treats them as settled:

- **`.env.managed_agents` does not exist here** and no `*_AGENT_ID` vars appear in `.env.example`. The file is provision-generated and gitignored, so this doesn't prove production is unprovisioned — but nothing in-repo confirms the hosted agents are live. Every call site raises `ManagedAgentNotConfigured` if they aren't.
- **The autonomous engineering loop is not armed.** `scripts/autonomy/ROUTINE.md:203-206` shows `autonomous-engineering-loop | _not yet armed_`; only `nightly-commit-review` has a live trigger. G3's budget recommendation should land *before* that loop is armed, not after.

---

## Sources

Primary (Anthropic):
- [Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) · [Define your agent](https://platform.claude.com/docs/en/managed-agents/agent-setup) · [Multiagent orchestration](https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration) · [Session budgets](https://platform.claude.com/docs/en/managed-agents/budgets) · [Scheduled deployments](https://platform.claude.com/docs/en/managed-agents/scheduled-deployments) · [Vaults](https://platform.claude.com/docs/en/managed-agents/vaults) · [Agent memory](https://platform.claude.com/docs/en/managed-agents/memory)
- [Scaling Managed Agents: decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)
- [Building multi-agent systems: when and how](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

Talks (transcript mirrors — YouTube unreachable from this environment):
- [Build Agents That Run for Hours](https://sozai.app/transcript/anthropic-workshop-build-long-running-agents/) — Prabaker & Wilson, 75 min
- [Ship your first Managed Agent](https://claude.com/code-with-claude/session/ldn-ext-ship-your-first-managed-agent) — Isabella He, 45 min
