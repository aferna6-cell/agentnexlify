# Winning Concept — 2026-06-11-pm

## Recommendation
Fix the `from __future__ import annotations` false positive in `check_project_invariants.py` (1-line human edit) so that tonight's nightly run can fix the 10 JSX em-dash violations autonomously and Item A (Check 10) auto-wires via the SKILL.md directive.

## Why This, Why Now
`check_project_invariants.py:209` uses a full-file text search (`"from __future__ import annotations" in text`), which catches the warning reminder comment in `channels_instagram.py:19` — a false positive. This means even after the nightly fixes all 10 JSX em-dash violations tonight, the `__future__` check will still fail and Check 10 cannot wire. The false positive is new — introduced by PR #232 adding a docstring reminder. The fix is 1 line and requires human execution (~2 min). With both failures cleared, the existing SKILL.md Item A directive fires at 2:37 AM and the self-healing loop is finally active after 50+ days of blockage.

## Implementation Sketch

**Step 1 (Human, ~2 min): Fix the false positive**
Edit `scripts/check_project_invariants.py` line 209:

Replace:
```python
if "from __future__ import annotations" in text:
```
With:
```python
if any(line.strip().startswith("from __future__ import annotations")
       for line in text.splitlines()):
```
This checks for an actual import statement at the start of a line, not any string occurrence in the file.

**Step 2 (Autonomous, tonight): Fix 10 JSX em-dash violations**
Mark the following files for nightly autonomous substitution (same pattern as run 49 winner 8db33df):
- `frontend/src/main.jsx:152`
- `frontend/src/components/CookieConsent.jsx:5, :31`
- `frontend/src/components/MarketingUpsell.jsx:3`
- `frontend/src/components/App.jsx:328`
- `frontend/src/components/Sidebar.test.jsx:27, :49`
- `frontend/src/components/billing/ReferralCard.jsx:24, :45`
- `frontend/src/components/os/ComposerAttachments.jsx:1`
AUTONOMOUS-EXECUTABLE. Substitute em-dash (`—`) with hyphen (`-`) in all UI string literals.

**Step 3 (Automatic, tonight): Check 10 auto-wires**
After Step 1 + Step 2 complete, `check_project_invariants.py` exits 0. The SKILL.md Item A directive (`pending_autonomous: true, autonomous_executable: true`) fires in the same nightly cycle, adding the 3-line pre-commit Check 10 block. Item A closes after 50+ days.

**Bonus Action A:** Review and merge PR #183 (billing fix, 18-day draft). ~10 min human.
**Bonus Action B:** Create `scripts/check-widget-sync.sh` (~10 min human, run 50 autonomous directive has not fired in 6 days — widget is in sync but unguarded).

## What This Replaces
Run 54 winner was "Fix 3 JSX em-dash violations in Agent OS UI (MemoryPanel.jsx, AgentOS.jsx)" — AUTONOMOUS-EXECUTABLE. Those 3 violations were targeted at run 54's specific files. Run 55's winner addresses the same class (em-dash violations) with a 2-part attack: fix the NEW blocker (false positive) + fix the 10 new violations from PRs #228/232. The false positive is what prevents the em-dash autonomous fix from being sufficient on its own.

## Confidence
**HIGH** — False positive confirmed by direct script inspection (`check_project_invariants.py:209`) + direct grep of `channels_instagram.py:19`. Em-dash violations confirmed by `check_project_invariants.py` output (10 violations, 7 files). Nightly em-dash fix pattern proven by run 49 (8db33df, 5 violations). Check 10 SKILL.md directive confirmed present (`autonomous_executable: true` in governance.json). Only human dependency: 1-line Python edit (~2 min).
