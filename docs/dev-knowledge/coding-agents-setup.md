# Claude Code Setup

Claude Code is the coding agent for AgentNexLiFy development.

## Starting Claude Code

Already configured. Use for multi-file features, debugging, architecture, git operations.
```bash
claude   # starts Claude Code in current directory
```

## Claude Code "35 Techniques" — AgentNexLiFy Adaptation

These are the techniques from Khairallah's list that map directly to our current workflow, with AgentNexLiFy-specific commands.

### High-value defaults (use every day)

1. **Plan mode before implementation**
   - Use plan mode for any task touching 2+ files.
   - Match with repo rule: "UltraPlan + UltraThink always."

2. **Context hygiene**
   - `/compact` after long sessions (30+ minutes).
   - `/clear` between unrelated tasks.

3. **Checkpoint commits before risky edits**
   - `git add . && git commit -m "checkpoint before <change>"`
   - Fast rollback when an experiment goes sideways.

4. **Incremental build + verify loop**
   - Ship in thin slices (schema -> API -> UI -> validation).
   - Run the smallest matching guardrail command after each slice:
     - `npm run check`
     - `npm run check:quick`
     - `npm run check:full` when cross-surface.

5. **Diff review after edits**
   - Ask for per-file rationale after changes.
   - Prevents accidental "helpful" side edits outside scope.

### Strongly useful in this repo

6. **Reference-file technique**
   - Point to an existing route/component and explicitly request pattern matching.
   - Works especially well with our strict schema + router conventions.

7. **Error-paste discipline**
   - Always paste full traceback and failing command output.
   - Ask for root-cause-first diagnosis before code changes.

8. **Architecture and security audits before major work**
   - Use architecture alternatives for multi-surface features.
   - Run focused security scans for auth, billing, tenant isolation, and MCP boundaries.

9. **Migration ripple planning**
   - Before schema edits, list all impacted layers first: migration, backend queries, types, routes, and tests.
   - Then implement.

10. **Recovery mode when stuck**
   - If a fix loop stalls, reset to known-good code and restart with a simpler approach.

### Already covered by existing AgentNexLiFy conventions

- `/init` is already done and maintained in `CLAUDE.md`.
- Multi-model routing (Opus for planning, Sonnet for execution) is already policy.
- Pre-commit/CI automation patterns already exist in hooks + GitHub Actions.

### Suggested "starter sequence" for new features in this repo

1. Plan mode -> validate scope and file list.
2. Implement the smallest vertical slice.
3. Run `npm run check` (or `npm run check:quick`).
4. Review diff and explain each touched file.
5. Commit checkpoint.
6. Continue next slice.
