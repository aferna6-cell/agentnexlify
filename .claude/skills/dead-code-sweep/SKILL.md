---
name: dead-code-sweep
description: "Scan the codebase for dead code — unused files, unreachable functions, orphan imports, dead config. Verify each item is truly dead, then remove."
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools: []
triggers: ["/dead-code-sweep", "dead code", "unused code", "remove dead", "orphan imports", "cleanup unused"]
effort: medium
---

# Dead Code Sweep

Systematic dead code detection and removal with false-positive verification.

## When to Use
- During refactoring cycles to clean up unused code
- Before major releases to reduce maintenance burden
- After renaming or restructuring to find orphaned files and functions
- When the codebase feels bloated with forgotten code

## When NOT to Use
- On a freshly initialized project with no history
- During active development where code may be used soon
- Without understanding external consumers (APIs, webhooks, third-party integrations)
- As a substitute for writing clean code in the first place

## Usage

- `/dead-code-sweep` — full codebase
- `/dead-code-sweep backend/services/` — scan specific directory

## Scan Steps

### 1. Dead Files
Find Python files never imported anywhere:
```bash
for f in backend/services/*.py; do
    base=$(basename "$f" .py)
    if [ "$base" != "__init__" ] && ! grep -rq "from backend.services.$base\|import.*$base" backend/ tests/; then
        echo "DEAD FILE: $f"
    fi
done
```

### 2. Dead Frontend Pages
Cross-reference pages against routes:
```bash
# List all page files
ls frontend/src/pages/*.jsx
# Check which are imported in App.jsx or routing
grep -l "import.*from.*pages/" frontend/src/components/App.jsx frontend/src/main.jsx
```
Any page file not in any route = dead.

### 3. Dead Functions
For each Python file, find functions defined but never called:
```bash
grep -n "^def \|^async def " <file> | while read line; do
    fname=$(echo "$line" | grep -oP "def \K\w+")
    if ! grep -rq "$fname" backend/ tests/ --include="*.py" | grep -v "^def "; then
        echo "DEAD: $fname in $file"
    fi
done
```

### 4. Unused Imports
```bash
# Quick scan with pyflakes if available
python3 -m pyflakes backend/routers/*.py 2>&1 | grep "imported but unused"
```
Fallback: manually check each import.

### 5. Dead Config
Check `backend/config.py` settings against usage:
```bash
grep -oP "\w+:" backend/config.py | while read key; do
    k=${key%:}
    if ! grep -rq "settings\.$k\|$k" backend/ --include="*.py" | grep -v "config.py"; then
        echo "DEAD CONFIG: $k"
    fi
done
```

### 6. Legacy Files
Check `public/`, `_archive/`, any `.bak` or `.old` files.

## False-Positive Verification

Before removing ANYTHING, verify it's truly dead:

1. **Dynamic imports** — Check for `importlib`, `__import__`, or string-based imports
2. **Public APIs** — Functions may be called by external consumers (webhooks, cron)
3. **Test-only usage** — Some functions only used in tests (still alive)
4. **Template references** — Jinja/string templates may reference functions by name
5. **Frontend lazy loading** — React.lazy() imports won't show in static grep

Log verified false-positives in the commit body so future sweeps skip them.

## Removal Order

1. Dead files (biggest impact, easiest to verify)
2. Dead functions within live files
3. Unused imports
4. Dead config
5. Legacy/archive files (confirm with user first)

## Commit

```
refactor: remove dead code — N dead files, N dead functions, N unused imports, N dead config

Removed:
- [list each item]

Verified alive (false positives):
- [list items checked but kept, with reason]
```

Run `python3 -m pytest tests/ -x --tb=short` before committing.
