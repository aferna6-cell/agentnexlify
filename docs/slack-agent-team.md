# Slack Agent Team

Mentionable AI teammates in the owner's Slack workspace, grok-bot style:
each agent on the cross-provider team (Fable 5, Codex, Kimi 3) is its own
Slack bot. Mention one in a channel — `@Fable5 what's the risk in this
plan?` — and it replies in-thread through the shared Anthropic runtime,
speaking in its `docs/TEAM_OPERATING_CONTRACT.md` role. DMs work too.

This is an **internal ops surface** (like admin routes), not a tenant
feature. No tenant data enters the prompts, and no `client_id` scoping
applies.

## How it works

```
Slack workspace
  @Fable5 / @Codex / @Kimi3  (one Slack app per agent)
        │  Events API (app_mention, message.im)
        ▼
POST /api/v1/slack/events       backend/routers/slack_agents.py
  1. verify v0 signature against raw body (5-min replay window)
  2. matching signing secret ⇒ which agent app this event belongs to
  3. BackgroundTasks: fetch thread → Claude reply → guard → postMessage
        │
        ▼
backend/services/slack_agent_team.py
  - personas mirror TEAM_OPERATING_CONTRACT §4 roles
  - replies pass os_outbound_guard.scan_text (secret/SSN/card patterns)
  - bot-authored events are never answered (no bot↔bot reply loops)
```

All agent apps point at the **same** events URL:

```
https://agentnexlify-production.up.railway.app/api/v1/slack/events
```

## Setup (per agent — repeat for each bot)

1. Create the Slack app at [api.slack.com/apps](https://api.slack.com/apps)
   → *Create New App* → *From a manifest* → paste the manifest below
   (change `name`/`display_name` per agent).
2. *Install to Workspace*, then collect:
   - **App ID** — *Basic Information* → App ID (`A0…`)
   - **Signing Secret** — *Basic Information* → App Credentials
   - **Bot Token** — *OAuth & Permissions* → `xoxb-…`
   - **Bot user id** (optional, improves mention stripping) — run
     `curl -H "Authorization: Bearer xoxb-…" https://slack.com/api/auth.test`
     and take `user_id` (`U0…`).
3. Add the entry to the `SLACK_AGENT_TEAM` env var on Railway (see below)
   and redeploy.
4. Back in the Slack app config, *Event Subscriptions* → enable and set the
   Request URL. Slack sends `url_verification`; the endpoint echoes the
   challenge once the deployed roster contains this app's signing secret —
   so set the env var **before** pasting the URL.
5. Invite the bot to a channel (`/invite @Fable5`) and mention it.

### App manifest

```yaml
display_information:
  name: Fable5            # Codex / Kimi3 for the other two
  description: AgentNexLiFy AI teammate — product & architecture steward
features:
  bot_user:
    display_name: Fable5  # the @name people will mention
    always_online: true
oauth_config:
  scopes:
    bot:
      - app_mentions:read   # receive @mentions
      - chat:write          # post replies
      - channels:history    # thread context in public channels
      - groups:history      # thread context in private channels
      - im:history          # DMs
      - im:read
      - im:write
settings:
  event_subscriptions:
    request_url: https://agentnexlify-production.up.railway.app/api/v1/slack/events
    bot_events:
      - app_mention
      - message.im
  org_deploy_enabled: false
  socket_mode_enabled: false
```

### Environment variables (Railway)

```bash
# JSON array — one object per agent app. Never commit values.
SLACK_AGENT_TEAM='[
  {"agent": "fable5", "app_id": "A0…", "signing_secret": "…", "bot_token": "xoxb-…", "bot_user_id": "U0…"},
  {"agent": "codex",  "app_id": "A0…", "signing_secret": "…", "bot_token": "xoxb-…", "bot_user_id": "U0…"},
  {"agent": "kimi3",  "app_id": "A0…", "signing_secret": "…", "bot_token": "xoxb-…", "bot_user_id": "U0…"}
]'

# Optional overrides (defaults shown)
SLACK_AGENT_MODEL=claude-sonnet-5
SLACK_AGENT_MAX_TOKENS=700
```

Per-entry optional keys: `persona` (replaces the built-in role prompt),
`model` (per-agent model override), `bot_user_id` (exact self-mention
stripping instead of the leading-token heuristic).

Agents with names other than `fable5`/`codex`/`kimi3` work too — they get
a generic persona unless the entry sets `persona`, so adding a fourth bot
is a roster edit, not a code change.

## Behavior notes

- **Threading** — a top-level mention starts a thread on that message; an
  in-thread mention replies in the same thread with the thread transcript
  (last 30 messages) as context, so follow-ups work.
- **Bot loop protection** — events carrying `bot_id` (or without a human
  `user`) are dropped. Agents answer humans only; they do not reply to
  each other. To get two agents' takes, mention both in one message —
  each replies independently in the same thread.
- **Retries** — Slack redelivers when the first response is slow; the
  endpoint acknowledges retries (`X-Slack-Retry-Num`) without reprocessing
  so a slow Claude call can't double-post.
- **Outbound guard** — every reply passes the deterministic
  `os_outbound_guard.scan_text` (API keys, tokens, SSN, card numbers,
  payment-redirect language). A flagged reply is replaced with a guard
  notice, never posted.
- **Failure shape** — model errors degrade to a canned "couldn't reach my
  model" reply; Slack API failures are logged and dropped. The webhook
  itself always answers inside Slack's 3-second deadline because the work
  runs in `BackgroundTasks`.

## Security

- Signature verification runs against the **raw body before any payload
  field is parsed** — nothing attacker-controllable selects the secret;
  the matching secret itself identifies the app.
- Timestamps older than 5 minutes are rejected (replay window).
- With `SLACK_AGENT_TEAM` unset the endpoint rejects everything (403).
- Bot tokens are used as bearer headers only; they never appear in URLs
  or logs.

Tests: `backend/tests/test_slack_agent_team.py`.
