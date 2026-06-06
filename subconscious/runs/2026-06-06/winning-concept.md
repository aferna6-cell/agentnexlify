# Winning Concept — 2026-06-06 (Run 52)

## Recommendation

Apply run 50's implementation sketch in full: add 3 scope bullets to nightly-commit-review SKILL.md (additive SKILL.md modification + bash script creation + pre-push additions) and the Item B inline content block — converts check-widget-sync.sh from "blocked 44 days" to "auto-executes at 2:37 AM 2026-06-07."

## Why This, Why Now

Run 50's winning concept was labeled AUTONOMOUS-EXECUTABLE but blocked: nightly scope line 65 covers SKILL.md *creation* only, not *modification*. Item B (check-widget-sync.sh) requires modifying the existing nightly SKILL.md to add scope bullets + inline content. Three prior scope-extension runs (40→43→47) each delivered in the next nightly cycle. The pattern is proven. The gap is one missing scope bullet. Human applies ~15-min SKILL.md edit today; nightly executes check-widget-sync.sh creation + pre-push wiring at 2:37 AM 2026-06-07 automatically.

## Implementation Sketch

**Human action required (~15 min). NOT autonomous (cannot self-extend scope to SKILL.md modification).**

### Step 1 — Add 3 scope bullets to nightly-commit-review SKILL.md

Open `.claude/skills/nightly-commit-review/SKILL.md`. Find the LOW-risk autonomous scope section (after the `.github/workflows/*.yml` bullet, around line 68). Insert the following 3 bullets BEFORE the `### Current pending item (Item A)` block:

```
- **Additive text additions to existing `.claude/skills/*/SKILL.md`** when the most recent winning-concept.md contains `AUTONOMOUS-EXECUTABLE` and provides the verbatim content to append, the change is purely additive (no deletions), and the target skill is NOT `nightly-commit-review` itself (no self-modification). Commit as `docs(skills): extend <skill-name> [auto-nightly-YYYY-MM-DD]`. After commit: update matching `governance.json` entry status → `implemented`.
- **New bash scripts in `scripts/` directory** when the winning concept provides the full script content verbatim in an `## Inline Scripts` section. Create at the named path, `chmod +x`, commit as `ci(scripts): add <name> [auto-nightly-YYYY-MM-DD]`.
- **Additive changes to `scripts/hooks/pre-push`** when `governance.json` has a matching `active_directions[]` entry with `"autonomous_executable": true` and the winning concept provides the exact lines to insert. Insert before the final `exit 0` line. Pre-condition: run any referenced script first — if exits non-zero, log blocker + open MEDIUM issue instead of wiring. Commit as `ci(pre-push): add <description> [auto-nightly-YYYY-MM-DD]`.
```

### Step 2 — Add Item B inline content block to nightly SKILL.md

After the existing `### Current pending item (Item A)` block (lines 69-79), insert:

```
### Current pending item (Item B): Widget 3-Copy Sync Guard
Status: `pending_autonomous`. Governance: run 7 `autonomous_executable: true`. 44-day gap.
3 widget JS copies: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. All currently byte-identical.

**Apply in order, single commit:**

**1. Create `scripts/check-widget-sync.sh`:**
```bash
#!/usr/bin/env bash
# check-widget-sync.sh — verify all 3 widget JS copies are byte-identical
set -euo pipefail

COPY1="widget/agentnexlify-widget.js"
COPY2="frontend/public/widget/agentnexlify-widget.js"
COPY3="landing-page-v2/widget/agentnexlify-widget.js"

FAIL=0
for src in "$COPY1" "$COPY2" "$COPY3"; do
  if [ ! -f "$src" ]; then
    echo "❌ Widget sync: $src missing"; FAIL=1
  fi
done
[ $FAIL -eq 1 ] && exit 1

if ! diff -q "$COPY1" "$COPY2" > /dev/null 2>&1; then
  echo "❌ Widget sync: $COPY1 and $COPY2 differ"; FAIL=1
fi
if ! diff -q "$COPY1" "$COPY3" > /dev/null 2>&1; then
  echo "❌ Widget sync: $COPY1 and $COPY3 differ"; FAIL=1
fi
[ $FAIL -eq 1 ] && exit 1
echo "✅ Widget sync: all 3 copies byte-identical"
```

**2. Wire into `scripts/hooks/pre-push`** — add before `exit 0`:
```bash
echo -n "Check 12: Widget 3-copy sync... "
bash scripts/check-widget-sync.sh || { echo "FAIL"; exit 1; }
echo "PASS"
```

**3. Fix CLAUDE.md Invariant #4** — change "2 copies" to "3 copies":
Find line: `**Widget JS byte-identical** in \`widget/\` AND \`frontend/public/widget/\``
Replace: `**Widget JS byte-identical** in \`widget/\`, \`frontend/public/widget/\`, AND \`landing-page-v2/widget/\``

Commit: `ci(pre-push): add widget 3-copy sync check (Item B) [auto-nightly-YYYY-MM-DD]`
After commit: update `governance.json` run 7 status → `implemented`.
```

### Step 3 — Commit SKILL.md changes

```bash
git add .claude/skills/nightly-commit-review/SKILL.md
git commit -m "docs(skills): extend nightly autonomous scope — SKILL.md modification + bash scripts + pre-push"
```

### Step 4 — Bonus Action: Merge PR #183

While SKILL.md changes are applied, also:
```bash
gh pr view 183 --json state,checksState
# If CI green: gh pr ready 183 && gh pr merge 183 --squash
```
Verify: `grep -n "15000\|25000" backend/routers/billing.py`

### Step 5 — Verify nightly 2026-06-07 fires

After 2:37 AM on 2026-06-07, check:
```bash
ls scripts/check-widget-sync.sh          # should exist
grep "check-widget-sync" scripts/hooks/pre-push  # should be wired
cat subconscious/state/governance.json | python3 -c "import sys,json; d=json.load(sys.stdin); [print(x['title'], x['status']) for x in d['active_directions'] if 'run 7' in x.get('note','') or '2026-04-24' == x.get('date','')]"
```

## What This Replaces

Active direction from run 50 (pending_autonomous) — converted from "queued for nightly" to "actionable today with nightly execution tomorrow."

## Confidence

HIGH — scope gap confirmed by direct SKILL.md grep (line 65: "creation" only). Prior 3/3 scope extensions delivered in next nightly. Item B content is pre-written in run 50 winning-concept.md. Zero code changes required (SKILL.md edit + bash script only).
