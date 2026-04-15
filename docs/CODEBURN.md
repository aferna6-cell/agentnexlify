# codeburn — token spend dashboard

Terminal tool that classifies every Claude Code session turn into 13 activity categories (coding, debugging, exploration, conversation, etc.) so you can see where tokens actually go. Reads local session transcripts — no LLM calls, no upload.

Upstream: https://github.com/AgentSeal/codeburn

## Install on this machine

System npm is broken (missing `walk-up-path`), so the canonical `npx codeburn` fails. Workaround: fresh npm + local install, no system changes.

```bash
# one-time
curl -sL https://registry.npmjs.org/npm/-/npm-11.12.1.tgz -o /tmp/npm.tgz
mkdir -p "C:/Users/aidan/tools/fresh-npm" && tar -xzf /tmp/npm.tgz -C "C:/Users/aidan/tools/fresh-npm" --strip-components=1
mkdir -p "C:/Users/aidan/tools/codeburn-install" && cd "C:/Users/aidan/tools/codeburn-install"
node "C:/Users/aidan/tools/fresh-npm/bin/npm-cli.js" init -y
node "C:/Users/aidan/tools/fresh-npm/bin/npm-cli.js" install codeburn --no-audit --no-fund
```

## Use

```bash
CB='node C:/Users/aidan/tools/codeburn-install/node_modules/codeburn/dist/cli.js'
$CB status                       # one-liner: today + month
$CB export -f json -o burn.json  # 1d + 7d + 30d breakdown
$CB today                        # interactive TUI
```

## Snapshot — 30 days to 2026-04-15

- Total: $316.13 / 4082 calls / 69 sessions
- AgentNexLiFy project: $16.79 / 168 calls / 3 sessions (5.3% of spend)
- By activity: **Exploration $166.70 (53%)**, Coding $52.93 (17%), Debugging $35.43, Conversation $19.56, Brainstorming $10.33
- By model: Opus 4.6 $312.42 (99%), Haiku 4.5 $3.70

## Leverage

Exploration eating half the budget → watch for agents doing redundant repo walks. Coding is only 17% — actual edits are cheap, research is where money goes. Haiku handles almost nothing at $3.70 — more mechanical work could route there per model-routing rule.
