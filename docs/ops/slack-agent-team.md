# Slack Agent Team — Grok-like setup

Slack is already connected. `#agent-nexlify` already launches the Grok/`@cursor` bot. This pack turns that into a specialist team you can talk to the same way.

GitHub Issues stay the durable hub. Slack starts the work.

Canonical config: [`.ai/slack-agent-team.json`](../../.ai/slack-agent-team.json)

## What you already have

| App | Slack ID | How it behaves today |
|---|---|---|
| Cursor / Grok | `U0BTH748Z3P` | `@cursor` in `#agent-nexlify` starts a Cloud Agent |
| ChatGPT | `U0BTQPR3KFE` | Engineering manager; `@cursor` mentions from ChatGPT already launch agents |
| Claude | `U0BTM9DHUV8` | Legacy Slack bot until Claude Tag is enabled |
| GitHub | `U0BTKCEKLK0` | Repo notifications |
| Aidan | `U0AU23Y8PSN` | Owner |

Cursor does **not** wake on unmentioned channel posts. That is why the Grok bot feels like one named assistant, and why specialist channels + Cursor Automations are required for a team.

## Owner steps (about 10 minutes)

These cannot be done from a Cloud Agent. Do them in Slack and the Cursor dashboard.

### 1. Create four public channels

In the Agent Nexlify Slack workspace:

1. `#agent-grok` — type anything; Grok answers
2. `#agent-product` — Fable 5
3. `#agent-code` — Codex
4. `#agent-review` — Kimi 3

Keep them **public**. Cursor Slack automations only see public channels.

Invite `@cursor` to each channel (`/invite @cursor`).

### 2. Confirm the Cursor Slack install

1. Open [Cursor integrations](https://cursor.com/dashboard/integrations)
2. Slack should already show Connected (it is — `#agent-nexlify` is live)
3. Default repository: `aferna6-cell/agentnexlify`

In `#agent-nexlify` run:

```text
@Cursor settings
```

Set the channel default repo to `aferna6-cell/agentnexlify`.

### 3. Create four Cursor Automations

Open [cursor.com/automations](https://cursor.com/automations). For each row:

| Automation name | Channel | Also match in `#agent-nexlify` | Prompt to paste |
|---|---|---|---|
| Grok Front Desk | `#agent-grok` | `^(grok\|ask):` | [`ops/slack-agent-team/prompts/grok-front-desk.md`](../../ops/slack-agent-team/prompts/grok-front-desk.md) |
| Fable 5 Product | `#agent-product` | `^(fable\|product):` | [`ops/slack-agent-team/prompts/fable5-product.md`](../../ops/slack-agent-team/prompts/fable5-product.md) |
| Codex Implement | `#agent-code` | `^(codex\|impl):` | [`ops/slack-agent-team/prompts/codex-implement.md`](../../ops/slack-agent-team/prompts/codex-implement.md) |
| Kimi 3 Review | `#agent-review` | `^(kimi\|review):` | [`ops/slack-agent-team/prompts/kimi3-review.md`](../../ops/slack-agent-team/prompts/kimi3-review.md) |

For every automation:

- Trigger: **New message in channel** + optional regex filter for HQ prefixes
- From: **Anyone in the channel**
- Repository: `aferna6-cell/agentnexlify`
- Tools: Send to Slack, Read Slack channels, Pull request creation
- Model: the recommended model in the prompt file

Do not add a fifth “do everything” automation on `#agent-nexlify` with no filter. It will fire on every ChatGPT/Claude/GitHub post.

### 4. Optional: Claude Tag

Claude’s current Slack app is the legacy fallback and cannot reliably `@mention` Cursor. Enable Claude Tag in the Claude workspace if you want Claude to launch Cursor the same way ChatGPT already can.

## How to use it (Grok-like)

**Always-on specialist (closest to Grok):**

```text
#agent-grok
Why did widget greeting stop matching the dashboard?
```

**HQ prefixes** (stay in `#agent-nexlify`):

```text
grok: summarize open loops that block paid launch
product: shrink onboarding to three owner decisions
impl: add the missing client_id filter on that leads query
review: adversarial-check the draft PR
```

**Ad-hoc Cloud Agent** (what you already do):

```text
@Cursor in agentnexlify, inspect PR 693 and reply in this thread
```

Main channel: 1–4 bullets. Threads for the real work.

## What Slack cannot replace

- `python3 scripts/teamctl.py preflight --issue <n> --agent <codex|fable5|kimi3>`
- Lane claims, reviews, and proof on the GitHub issue
- `[skip ci]` on team commits
- Owner authority for merges, deploys, secrets, purchases, and product decisions

## Verify the repo pack

```bash
npm run slack-team:check
```

This check validates the config, spec, and prompt files. It cannot prove the Cursor dashboard automations exist.
