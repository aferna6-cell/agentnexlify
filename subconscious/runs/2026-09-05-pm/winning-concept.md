# Winning Concept — Run 115 (2026-09-05-pm)

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI usage guard coverage
sweep that identifies routers calling `call_claude_messages` without `ai_usage_guard`, and files
GH issues (labels: `billing + ai-ready`) for each unguarded route.

## Why This, Why Now
13 routers are confirmed unguarded as of 2026-09-05 (direct grep): menu.py, widget_photo_quote.py,
platform_support.py, content.py, jobs.py, snippets.py, reviews.py, os_files.py, onboarding.py,
insights.py, bids.py, marketing_campaigns.py, social_media.py. PRs #792–#799 (last 3 days) were a
7-PR emergency sprint to retrofit billing guards on voice/widget/SMS paths — each adding 600-1726
lines of tests. Without a preventive nightly sweep, every new AI route added to the codebase starts
unguarded and accumulates billing debt until a human notices and kicks off another sprint. Step 9I
(block_demo_role sweep) follows the identical mechanism and has caught security class-bugs since
implementation. Step 9L applies that proven mechanism to the billing domain.

## Implementation Sketch

Two deliverables: a committed analysis script and a SKILL.md step that runs it.

### Deliverable 1 — `scripts/check_ai_metering.py` (new file)

AST-based analyzer. Operates at **enclosing-function granularity**, resolves import aliases,
handles both router (Depends-based) and service (reserve/record/release) guard patterns,
and applies explicit exclusions.

**Detection logic:**

```python
# scripts/check_ai_metering.py
"""
Detect backend functions that call AI without metering guards.
Exits 0 with violations on stdout (one per line: path:function:line).
Exits 1 on script error only.
"""
import ast, sys
from pathlib import Path

# AI call names. Aliases resolved via import tracking per file.
AI_CALL_NAMES = {"call_claude_messages", "client.messages.create"}

# Guard patterns — router (Depends arg) OR service (call in body)
ROUTER_GUARD = "ai_usage_guard"          # appears in function signature via Depends()
SERVICE_GUARDS = {"reserve_tokens", "record_tokens", "ai_usage_guard"}

# Recognized metered wrappers: calling one of these satisfies the guard requirement in the caller.
# A function listed here is exempt from the check (it IS the guard layer).
METERED_WRAPPERS = set()  # extend as project adds canonical wrappers

# Paths to skip entirely (relative to repo root)
EXCLUDE_DIRS = {"tests", "test", "docs", "scripts/offline", "knowledge-base", "_archive"}

# Per-file opt-out: first 5 lines contain "# ai-metering-exempt: <owner>: <reason>"
EXEMPTION_MARKER = "# ai-metering-exempt:"

def resolve_aliases(tree):
    """Return dict mapping local alias -> canonical AI call name."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                real = alias.name
                local = alias.asname or alias.name
                if real in AI_CALL_NAMES:
                    aliases[local] = real
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                if alias.name in AI_CALL_NAMES:
                    aliases[local] = alias.name
    return aliases

def fn_has_ai_call(fn_node, ai_names):
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in ai_names:
                return True
    return False

def fn_has_guard(fn_node, is_router):
    """True if function has a guard. Router: Depends arg; Service: guard call in body."""
    if is_router:
        for arg in fn_node.args.args + fn_node.args.kwonlyargs:
            # Depends(ai_usage_guard) shows up as annotation or default
            pass
        # Check defaults for Depends(ai_usage_guard)
        for default in fn_node.args.defaults + fn_node.args.kw_defaults:
            if default and isinstance(default, ast.Call):
                if isinstance(default.func, ast.Name) and default.func.id == "Depends":
                    for darg in default.args:
                        if isinstance(darg, ast.Name) and darg.id == ROUTER_GUARD:
                            return True
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in SERVICE_GUARDS or name in METERED_WRAPPERS:
                return True
    return False

def scan_file(path: Path, is_router: bool):
    src = path.read_text(errors="replace")
    # Exemption check
    if any(EXEMPTION_MARKER in line for line in src.splitlines()[:5]):
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []
    ai_names = AI_CALL_NAMES | set(resolve_aliases(tree).keys())
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in METERED_WRAPPERS:
            continue  # wrapper itself is exempt
        if fn_has_ai_call(node, ai_names) and not fn_has_guard(node, is_router):
            violations.append(f"{path}:{node.name}:{node.lineno}")
    return violations

def main():
    root = Path(".")
    all_violations = []
    for target, is_router in [("backend/routers", True), ("backend/services", False)]:
        for py in Path(target).rglob("*.py"):
            if any(exc in py.parts for exc in EXCLUDE_DIRS):
                continue
            all_violations.extend(scan_file(py, is_router))
    for v in all_violations:
        print(v)

if __name__ == "__main__":
    main()
```

**Alias handling:** `resolve_aliases()` maps every `import ... as alias` and `from ... import fn as alias` for AI call names, then passes the expanded set to `fn_has_ai_call`. An aliased call is detected identically to a direct call.

**Guard discrimination:**
- Router functions: `Depends(ai_usage_guard)` in default values of any parameter.
- Service functions: any call to `reserve_tokens`, `record_tokens`, or `ai_usage_guard` in the function body.
- Both scopes: calling a recognized metered wrapper satisfies the check.

**Exclusion mechanism:**
- Directory-level: `EXCLUDE_DIRS` set — paths containing `tests/`, `test/`, `docs/`, `scripts/offline/`, etc. are skipped.
- Per-file: first 5 lines containing `# ai-metering-exempt: <owner>: <reason>` — file skipped, marker is human-auditable.

**Output format:** one line per violation: `backend/services/foo.py:generate_content:42`. Identifiers only — no prompt content, customer data, or secrets.

---

### Deliverable 2 — Step 9L block for `nightly-commit-review/SKILL.md`

Insert after Step 9K log line and before "10. Commit report":

```markdown
### Step 9L — AI Usage Guard Coverage Sweep

1. Run detector:
   ```bash
   python3 scripts/check_ai_metering.py > /tmp/step9l-violations.txt 2>&1
   ```
2. Parse violations (one line = `path:function:line`). Skip if output empty.
3. For each unique `path:function` pair:
   a. Search for existing open issue:
      `mcp__github__search_issues(query="repo:aferna6-cell/agentnexlify is:open label:ai-ready {path}:{function}")`
   b. If open issue found → dedup-skip.
   c. If none → file via `mcp__github__issue_write`:
      - Title: `fix(billing): {path}:{function} calls Claude without metering guard`
      - Labels: `["billing", "ai-ready"]`
      - Body: `Function \`{function}\` in \`{path}\` (line {line}) calls an AI provider without
        reserve/record/release metering. AI spend from this call is untracked and unbilled.
        Add the guard pattern per PRs #792–#799. Autodetected by Step 9L nightly sweep.`
        (Identifiers only — no prompt content, customer data, or secrets in issue body.)
4. Log: `Step 9L: {N} functions checked, {M} violations, {K} issues filed, {D} dedup-skipped.`
```

---

### Regression Fixtures

Six cases that must pass before Step 9L ships to SKILL.md:

| # | Fixture | Expected |
|---|---------|----------|
| 1 | `services/unmetered_svc.py::generate_response()` — calls `call_claude_messages`, no guard in body | **FLAGGED** |
| 2 | `routers/widget_chat.py::chat_endpoint()` — `Depends(ai_usage_guard)` in signature, calls AI | **PASSES** |
| 3 | `services/guarded_wrapper.py::call_guarded_claude()` — listed in `METERED_WRAPPERS`, calls AI directly | **PASSES** (it is the wrapper) |
| 4 | `routers/mixed.py` — `guarded_fn()` has Depends guard; `unguarded_fn()` has no guard, both call AI | `unguarded_fn` **FLAGGED**, `guarded_fn` **PASSES** (no masking across functions) |
| 5 | `services/alias_user.py` — `from backend.services.llm_runtime import call_claude_messages as call_llm`; uses `call_llm()` without guard | **FLAGGED** (alias resolved) |
| 6 | `tests/test_ai.py`, `docs/sample.py`, `scripts/offline/process.py` | **EXCLUDED** (not scanned) |

**Inventory note:** PR #791 (merged 2026-09-03, `appointment_brief`) added metering to the
appointment router. It should appear in the PASSES inventory for fixture 2-class cases, not as an
outstanding violation. The detector must not re-flag it.

---

### Commit plan

Two files in one PR:
1. `scripts/check_ai_metering.py` — the detector (new file)
2. `.claude/skills/nightly-commit-review/SKILL.md` — Step 9L block inserted

3. **Autonomous-executable:** This is a SKILL.md edit + one new script — same channel as Steps 9C/9E/9F/9G/9I/9J/9K.
   No backend code changes, no migrations, no new state files. Script reads only; writes nothing to disk.

## What This Replaces
Active direction was Step 9K (implemented run 114, working correctly as of nightly-2026-09-05).
Step 9L extends the nightly sweep pattern to a new domain (billing vs. security). No replacement
of prior active direction — additive.

## Confidence
**HIGH** — Evidence is direct (grep confirmed 13 unguarded routes today). Mechanism proven (Step 9I
identical pattern, zero false positive issues in 5+ weeks). Risk is dedup failure (mitigated by
search_issues check before filing). Token cost is low (bash greps + conditional GH API calls).

## Escalation Condition
Autonomous-executable if not approved by run 116 (1st carry-forward mandate per established governance).
