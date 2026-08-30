# Slack agent team

A Grok-bot-style agent team living in the founder's Slack workspace. Mention the
bot in a channel or DM it, and one of six specialist agents answers in-thread
under its own name and icon.

This is an **operator surface, not a tenant feature**. It carries no tenant JWT,
touches no tenant data, and is not part of any plan. It exists so the founder can
ask the platform's own specialists a question in the place work already happens.

## What it looks like in Slack

```
Founder    @Nexus the railway deploy failed with a 502
Ops        Check the deployment log first: Railway -> agentnexlify -> latest
           deploy. A 502 right after a deploy is almost always the container
           failing its healthcheck ...

Founder    @Nexus schema: does leads have tenant_id?
Schema     No. `leads` and `conversations` are scoped by `client_id` ...
Guardian

Founder    @Nexus team: should I raise the chatbot price to $29?
Growth     ...
Chief of   ...
Staff
Support    ...
Chief of   *Decision:* hold at $19.99 until ... (synthesis)
Staff
```

All six agents are one Slack app. Each reply is posted with `username` and
`icon_emoji` overrides, which is what makes them read as separate teammates —
that is the entire reason the `chat:write.customize` scope is required.

## The roster

| Key | Agent | Lane |
| --- | --- | --- |
| `chief` | Chief of Staff | Priorities, trade-offs, sequencing. Default when nothing else matches, and the synthesizer for `team:` questions. |
| `engineer` | Engineer | FastAPI routers/services, React dashboard, widget JS. |
| `schema` | Schema Guardian | Tables, columns, migrations, RLS, tenant scoping. |
| `growth` | Growth | Pricing, positioning, competitors, SEO, churn. |
| `support` | Support | Tenant-reported breakage, billing confusion, escalations. |
| `ops` | Ops | Railway/Vercel deploys, env vars, uptime, incidents. |

Aliases work too: `db:` and `migration:` reach `schema`, `infra:` and `devops:`
reach `ops`, and so on. The full list is
[`backend/services/slack_agent_roster.py`](../backend/services/slack_agent_roster.py).

Adding a teammate is one `SlackAgent` entry in that file. No router, service, or
Slack-app change.

## How to talk to it

| You type | What happens |
| --- | --- |
| `@Nexus <question>` | Routed by keyword to the best-matched agent. |
| `@Nexus schema: <question>` | That agent answers, routing bypassed. |
| `@Nexus team: <question>` | Three agents answer in parallel, then the chief posts the decision. |
| `@Nexus help` | Prints the roster. No model call. |
| Reply in a thread | Keeps the agent already in that thread, so `and the second one?` does not get re-routed. |
| DM the bot | Same grammar, no mention needed. |

An unrecognized prefix is prose, not an error: `@Nexus Note: the deploy failed`
is routed normally rather than rejected for having no agent called `note`.

## Setup

Four steps. Only step 3 is on Railway; the rest is in the Slack app config.

### 1. Create the app from the manifest

Go to <https://api.slack.com/apps> -> **Create New App** -> **From a manifest**,
pick the workspace, and paste
[`ops/slack/agent-team-manifest.json`](../ops/slack/agent-team-manifest.json).
Replace `REPLACE_WITH_BACKEND_DOMAIN` with the backend's public host (the same
host serving `/api/health`).

The manifest already declares the required scopes and the two bot events
(`app_mention`, `message.im`).

### 2. Install it and collect three values

- **Signing secret** — Basic Information -> App Credentials.
- **Bot token** (`xoxb-...`) — OAuth & Permissions, after clicking *Install to
  Workspace*.
- **Team ID** (`T...`) — Slack -> workspace menu -> *About this workspace*, or
  read it off any `event_callback` payload.

### 3. Set them on the backend (Railway -> Variables)

```
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_TEAM_ID=T...
```

All three are required. With any of them missing the endpoint returns `503` and
the agents stay off — a partial configuration is treated as off, never as open,
because every accepted event spends Anthropic credits.

Optional:

```
SLACK_ALLOWED_USER_IDS=U0FOUNDER,U0COFOUNDER   # empty => whole workspace
SLACK_AGENTS_MODEL=claude-sonnet-5
SLACK_AGENTS_MAX_TOKENS=700
SLACK_AGENTS_HISTORY_MESSAGES=12
```

`SLACK_AGENTS_MODEL` / `SLACK_AGENTS_MAX_TOKENS` /
`SLACK_AGENTS_HISTORY_MESSAGES` also read from `platform_settings` (migration
175), so they can be changed without a redeploy.

### 4. Point Slack at the endpoint and invite the bot

Redeploy the backend, then in **Event Subscriptions** save the request URL:

```
https://<backend-domain>/api/v1/slack/events
```

Slack posts a signed `url_verification` challenge; the endpoint echoes it. A
green *Verified* is proof the signing secret matches.

Finally `/invite @Nexus` in each channel it should work in. Thread context comes
from `conversations.replies`, which only works in channels the bot is a member
of.

## Security model

There is no user auth on this endpoint — Slack is the caller — so three things
stand in for it:

1. **Signature verification** over the raw request body
   (`backend/services/slack_verify.py`), checked before any payload field is
   read, with a 5-minute replay window.
2. **`SLACK_TEAM_ID` allow-list.** Events from any other workspace get `403`.
   This is the cost control: without it, anyone who found the URL and secret
   could bill the Anthropic account.
3. **Optional `SLACK_ALLOWED_USER_IDS`** for workspaces with guests.

Loop safety: any event carrying `bot_id`, `bot_profile`, or `app_id` is dropped,
so the bot never answers itself. Plain `message` events are only honored in DMs
(`channel_type == "im"`), so the bot never reads channel traffic it was not
addressed in.

Slack retries any event it does not see acked within 3 seconds, so model work
runs in `BackgroundTasks` and `event_id` is recorded in the shared idempotency
store (`provider = "slack"`) — a retry is a no-op instead of a second answer.

## Cost

One `@mention` is one Sonnet call capped at `SLACK_AGENTS_MAX_TOKENS` (700 by
default) with up to `SLACK_AGENTS_HISTORY_MESSAGES` messages of thread context.
A `team:` question is four calls: three agents plus the synthesis. The system
prompt is prompt-cached per agent, so repeated questions to the same agent read
the persona at 0.1x input cost.

`help` costs nothing — the roster is rendered deterministically.

## What the agents cannot do

By design, v1 agents have no tools. They cannot query Supabase, read the repo,
call the API, or change anything, and their system prompts tell them to say so
and name the file/table/dashboard to check instead of guessing. Treat answers as
a well-briefed colleague's opinion, not as a report from production.

Consequences worth knowing:

- Business facts (plans, prices, schema invariants, competitors) are baked into
  `_PLATFORM_CONTEXT` in `slack_agent_roster.py`, because `backend/Dockerfile`
  only copies `backend/`, `widget/`, and `VERSION` — the repo's markdown is not
  on disk in production. **Keep it in sync with `CLAUDE.md`** when plans, stack,
  or invariants change.
- No usage metering or per-day budget. The workspace and user allow-lists are
  the only spend limits.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Slack shows the request URL as unverified | `SLACK_SIGNING_SECRET` mismatch, or the backend has not redeployed with it set. |
| Slack event log shows `503` | One of the three required vars is unset. |
| Slack event log shows `403` | `SLACK_TEAM_ID` does not match the workspace sending events. |
| Bot stays silent, event log shows `200` | Event was skipped on purpose. The response body says why (`skipped: not_a_dm`, `bot_message`, `user_not_allowed`, `duplicate`). |
| Replies post as the generic app name | `chat:write.customize` scope missing — reinstall the app. |
| Replies land but ignore the thread | Bot is not in the channel, so `conversations.replies` returns `channel_not_found` and context degrades to empty. |
| `I couldn't reach the model just now` | Anthropic call failed after one retry. Check backend logs for `llm.call.error`. |

## Files

- `backend/routers/slack_agents.py` — the webhook, and every gate on it.
- `backend/services/slack_verify.py` — signature + replay window.
- `backend/services/slack_agent_roster.py` — roster, routing, command grammar.
- `backend/services/slack_agent_team.py` — Slack API calls, prompts, dispatch.
- `backend/tests/test_slack_agent_team.py` — 75 tests across all four.
- `ops/slack/agent-team-manifest.json` — the Slack app manifest.
