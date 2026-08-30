# Slack Agent Team Spec

Status: **canonical**
Updated: 2026-08-30

## Outcome

Aidan can talk to a Slack team of agents the same way he already talks to the Grok/`@cursor` bot: type in a channel (or use a short prefix in `#agent-nexlify`) and a specialist Cloud Agent replies in-thread, then does bounded repo work when asked.

## Non-goals

- Replacing GitHub Issues as the durable task hub
- Creating a second competing team besides Codex / Fable 5 / Kimi 3
- Custom Slack apps or extra bot tokens
- Spending GitHub Actions minutes
- Letting Slack bots merge, deploy, rotate secrets, or make product decisions

## Already true in the live workspace

| Surface | ID | Role |
|---|---|---|
| Slack team | `T0AU024EH38` | Agent Nexlify workspace |
| `#agent-nexlify` | `C0BTKCYP8TG` | Shared engineering HQ |
| `#all-agent-nexlify` | `C0AU5MEJ5QC` | Broadcast only |
| `@cursor` | `U0BTH748Z3P` | Grok-class implementer |
| ChatGPT | `U0BTQPR3KFE` | Engineering manager (standing auth) |
| Claude | `U0BTM9DHUV8` | Principal reviewer (legacy Slack bot until Claude Tag) |
| GitHub | `U0BTKCEKLK0` | Repo notifications |
| Aidan | `U0AU23Y8PSN` | Owner |

ChatGPT `@cursor` mentions already launch Cloud Agents. Unmentioned channel posts do not. That is why specialist Cursor Automations exist.

## Required specialist channels

Public channels, Cursor invited, one automation each:

| Channel | Agent | Wake method |
|---|---|---|
| `#agent-grok` | Grok Front Desk | any top-level message |
| `#agent-product` | Fable 5 | any top-level message |
| `#agent-code` | Codex | any top-level message |
| `#agent-review` | Kimi 3 | any top-level message |

HQ prefixes in `#agent-nexlify` are also required so the existing room keeps working:

| Prefix | Agent |
|---|---|
| `grok:` / `ask:` | Grok Front Desk |
| `fable:` / `product:` | Fable 5 |
| `codex:` / `impl:` | Codex |
| `kimi:` / `review:` | Kimi 3 |

## Automation contract

Each specialist automation MUST:

1. Use repository `aferna6-cell/agentnexlify`
2. Trigger from **Anyone in the channel**
3. Enable Send to Slack + Read Slack channels
4. Paste the prompt from `ops/slack-agent-team/prompts/`
5. Reply in the triggering thread
6. Keep `#agent-nexlify` top-level replies to 1–4 bullets
7. Refuse `Agent-Nexlify-OS` as the working repo
8. For repo edits: `teamctl` preflight + claim, `[skip ci]`, no Actions dispatch
9. Open draft PRs only; never merge or push `main`

## Acceptance

- `python3 scripts/check_slack_agent_team.py` exits 0
- Config, spec, ops doc, and four specialist prompts stay in sync
- Owner can create the four public channels and four automations from the ops doc without inventing prompts
- A message in `#agent-grok` or `grok:` in HQ produces a Slack thread reply
- Slack-started implementation still records a GitHub issue event before editing
