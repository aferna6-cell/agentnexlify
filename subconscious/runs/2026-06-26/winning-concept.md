# Winning Concept — Run 68 (2026-06-26)

**Winner:** Run 68 Mandate — 30-Second Terminal Fix
**Category:** code_health
**Impact:** HIGH (unblocks ALL commits immediately)
**Effort:** S (~30 seconds of human execution)
**Autonomous-executable:** NO — HUMAN-REQUIRED
**Mandated by:** `subconscious/runs/2026-06-25-pm/winning-concept.md` lines 114-118

---

## Why This Won

check_project_invariants.py has exited 1 for 4 consecutive subconscious runs (65, 66, 67, 68). Pre-commit Check 13 (FAIL+BLOCK mode) prevents ALL commits until it exits 0. Root cause is a chicken-and-egg: the fix requires human action (cp + text replacement + existing SKILL.md edit), and nightly-commit-review scope covers none of those. Run 67 set the mandate: if check still exits 1 in run 68, provide exact copy-paste terminal commands for human. This is that mandate executing.

---

## Exact Fix — Run This Now (30 seconds)

Copy the entire block below and paste into your terminal from the repo root:

```bash
# Step 1: Fix widget drift (landing-page-v2 out of sync)
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js

# Step 2: Fix 10 em-dashes (U+2014 → hyphen-minus) across 3 files
python3 -c "
files = [
    'frontend/src/components/billing/ReferralCard.jsx',
    'frontend/src/pages/SignupPage.jsx',
    'frontend/src/pages/AdminFunnelPage.jsx',
]
for f in files:
    txt = open(f, encoding='utf-8').read()
    fixed = txt.replace('—', '-')
    open(f, 'w', encoding='utf-8').write(fixed)
    changed = txt.count('—')
    print(f'Fixed {f}: {changed} em-dash(es) replaced')
"

# Step 3: Add Step 9B to nightly-commit-review SKILL.md
# (see Step 9B block below — paste the Python after reviewing)

# Step 4: Verify — must print "0 invariant(s) failed."
python3 scripts/check_project_invariants.py

# Step 5: Commit everything
git add widget/ landing-page-v2/widget/ frontend/src/components/billing/ReferralCard.jsx frontend/src/pages/SignupPage.jsx frontend/src/pages/AdminFunnelPage.jsx .claude/skills/nightly-commit-review/SKILL.md
git commit -m "fix: widget drift + em-dash violations + nightly Step 9B (runs 65/66 delivery)"
```

---

## Step 9B — Add to nightly-commit-review SKILL.md

After Step 2, add the following entry to the LOW risk list in `.claude/skills/nightly-commit-review/SKILL.md` (insert after the last bullet in the LOW section, before `### MEDIUM`):

```
- **Widget drift + em-dash repair** when `check_project_invariants.py` exits non-zero due to:
  (a) `widget/agentnexlify-widget.js` != `landing-page-v2/widget/agentnexlify-widget.js` → run `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
  (b) em-dash (U+2014) violations in frontend JSX → run `python3 -c "import pathlib; [p.write_text(p.read_text(encoding='utf-8').replace('—', '-'), encoding='utf-8') for p in [pathlib.Path(f) for f in ['frontend/src/components/billing/ReferralCard.jsx','frontend/src/pages/SignupPage.jsx','frontend/src/pages/AdminFunnelPage.jsx']]]"`
  Pre-condition: `check_project_invariants.py` identifies only widget-drift or em-dash failures (no other fails). If any other check fails, classify MEDIUM and open GH issue instead.
  Commit: `fix(nightly): widget drift + em-dash repair [auto-nightly-YYYY-MM-DD]`
```

---

## Expected Outcome

After running Steps 1-5:
- `python3 scripts/check_project_invariants.py` → `0 invariant(s) failed.`
- Pre-commit Check 13 unblocked → all developers can commit again
- Runs 65 + 66 active_directions cleared from governance.json
- Moratorium moves 2 items closer to exit (true_pending ~6 → ~4)
- Run 69 candidate unlocked: Plan-name invariant guard Check 7 (AUTONOMOUS-EXECUTABLE)

---

## What Nightly Can Now Fix Autonomously (After Step 9B)

Once Step 9B is in place, nightly-commit-review can handle future widget drift + em-dash regressions without human intervention. This closes the chicken-and-egg loop permanently.

---

## Parking Lot Candidates (not this run)

1. **Plan-name guard Check 7** (run 69) — AUTONOMOUS-EXECUTABLE after check exits 0. Prevents next repricing from breaking paid features silently.
2. **KB autopopulate fix** — replace agent-browser CLI with curl in `scripts/daily/kb-autopopulate.sh`. KB stale 50+ days.
3. **email_sequences.py split** — 1143 lines, Rule 9 violation. Multi-hour refactor, needs plan approval.
4. **OPS #2 GH issue** — create tracking issue for 10DLC/A2P registration (code ready, business action needed).
