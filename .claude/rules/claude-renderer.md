# Claude Code Renderer — CLAUDE_CODE_NO_FLICKER=1

## Rule
Opt-in to new virtual-DOM-style terminal renderer for long sessions.

## How to enable
```bash
# Preferred — npm script (cross-platform via cross-env)
npm run claude:noflicker

# Or per-shell export
# bash/zsh:
CLAUDE_CODE_NO_FLICKER=1 claude

# PowerShell:
$env:CLAUDE_CODE_NO_FLICKER=1; claude

# cmd.exe:
set CLAUDE_CODE_NO_FLICKER=1 && claude
```

## What it changes
- Zero screen flicker (virtual screen diff, like React DOM)
- Input field pinned to bottom (chat-app UX)
- Mouse click + drag select + wheel scroll work
- Memory stays constant regardless of conversation length
- Diff rendering updates only changed chars

## Tradeoffs
- **Cmd+F / Ctrl+F dead** — use `Ctrl+O` then `/` to search instead
- Experimental — edge cases possible
- Unverified on v2.1.98 (our pinned version) — flag may silent-ignore on older builds

## When to disable
- Rendering artifacts on specific terminal (iTerm/Windows Terminal/Alacritty edge cases)
- Need native terminal search (Cmd+F) and won't adapt to Ctrl+O workflow
- Tmux/screen panes misbehaving (virtual screen conflicts with multiplexer redraws)
- Copy-paste breaking across OS clipboard boundaries

## Compat with version pin
`.claude/rules/claude-version-pin.md` pins v2.1.98 for phantom-token avoidance. If `CLAUDE_CODE_NO_FLICKER=1` produces no visible effect on 2.1.98:
- Flag likely gated to newer build (2.1.100+)
- Decide: stay on 2.1.98 (accept flicker) OR unpin temporarily for renderer
- Re-evaluate version pin sunset criteria

## Why this matters for 10+ hour sessions
- Constant memory — no fan spin-up on long chats
- No reflow lag — even with 200k context
- Mouse support — faster navigation than keyboard-only

## Cross-refs
- `.claude/rules/claude-version-pin.md` — 2.1.98 pin
- `package.json` scripts: `claude:2.1.98`, `claude:noflicker`
- Source: community post, Claude Code experimental renderer (2026-04)
