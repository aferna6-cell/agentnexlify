### Idea 4: Create scripts/check-widget-sync.sh — Item B After 50+ Days MISSING

**Evidence:** check-widget-sync.sh MISSING confirmed in 5 consecutive runs (50/51/52/53/54). Run 7 winner (2026-04-24, day 50+ of calendar gap). Run 50 extended nightly scope to include check-widget-sync.sh creation as AUTONOMOUS-EXECUTABLE. governance.json run 7 active_directions entry: `pending_autonomous, autonomous_executable: true`. Widget byte-identity is Critical Invariant #4. Three widget copies confirmed: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. Current nightly SKILL.md has the full script inline and pre-push wire.

**Action:** Create `scripts/check-widget-sync.sh` (diff all 3 widget copies, exit 1 on divergence). Wire into `scripts/hooks/pre-push`. Fix CLAUDE.md Invariant #4 ("2 copies" → "3 copies").

**Impact:** Widget sync guard finally exists after 50 days. Pre-push catches drift before it reaches prod. AUTONOMOUS-EXECUTABLE via nightly — run 50 SKILL.md scope extension already covers this.

**Category:** code_health
