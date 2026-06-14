# Ideas — Run 48 (2026-06-03)

## Evidence Digest

- **Item D implemented** (nightly 42992fa): `.github/workflows/lead-qualifier-eval.yml` created — run 14 winner (48-day pending) now closed. Governance correction applied.
- **Item A still blocked**: `check_project_invariants.py` exits 1 on 5 JSX em-dash violations (`IntegrationsPage:1018`, `SettingsInboundChannels:220/221`, `MessagingSettingsCards:263/276`). Nightly cannot auto-wire Check 10 until script exits 0. Pre-commit bash additions scope extended (4226ef4) — channel is ready, em-dash is the only gate.
- **Zero production code commits** for 4+ days. Moratorium day 33. 15 pending (Item D drops to 14 after governance correction).
- **email_sequences.py**: 1255L (run 35/41 winner, day 4+ unimplemented). god-class-splitter + post-split-test-repair both ready.
- **GH #181**: `AMOUNT_TO_PLAN` at `backend/routers/billing.py:263` confirmed missing `15000:'autopilot'` and `25000:'professional'`. Path now known. In `rejected_paths` — cannot be winner without new evidence.
- **Widget sync guard**: `scripts/check-widget-sync.sh` MISSING (Item B, run 7/15, 40+ days).
- **AI-to-Human Handoff** (run 4): 48 days, Critical gap, all 7 industries.

---

### Idea 1: Fix 5 JSX em-dash violations — unblock Item A autonomous chain reaction

**Evidence:** nightly-commit-review-2026-06-03.md §Item A confirms exact 5 files blocking `check_project_invariants.py` exit 0. CLAUDE.md personality rule bans em-dashes site-wide. 4-run autonomous infrastructure chain (runs 42→43→44→47) built the execution path — pre-commit bash additions in nightly scope since 4226ef4. Only the em-dash exit 1 prevents auto-wiring Check 10 tonight.

**Action:** Edit 5 JSX files to replace em-dashes (`—`) with hyphens (`-`) or reword the copy:
- `frontend/src/pages/IntegrationsPage.jsx:1018`
- `frontend/src/pages/SettingsInboundChannels.jsx:220-221`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:263, 276`
Then `check_project_invariants.py` exits 0 → nightly fires autonomous Check 10 wiring at 2:37 AM.

**Impact:** Closes Item A (29+ days pending); pre-commit Check 10 active; moratorium pending drops 1; chain reaction costs ~10 min human effort.

**Category:** code_health / workflow

---

### Idea 2: Create scripts/check-widget-sync.sh (Item B) + wire to pre-push

**Evidence:** `scripts/check-widget-sync.sh` confirmed MISSING by every nightly review since run 7 (2026-04-24, 40+ days). Widget copies confirmed in sync (nightly PASS) but no guard exists. 3 copies: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. CLAUDE.md Invariant #4 incorrectly says "2 copies" — update needed.

**Action:** Create `scripts/check-widget-sync.sh` (diff all 3 widget copies, FAIL on diverge). Wire into `scripts/hooks/pre-push`. Fix CLAUDE.md Invariant #4 "2 copies" → "3 copies".

**Impact:** Closes Item B (run 7/15, 40+ days); pre-push guard active; one more moratorium item cleared; ~15 min.

**Category:** code_health

---

### Idea 3: Fix 5 JSX em-dashes + create widget sync guard as single 20-min moratorium sprint commit

**Evidence:** Combining Idea 1 (em-dash, ~10 min) and Idea 2 (widget sync, ~15 min) into a single commit drops moratorium pending by 2 in one session. Both are additive non-breaking changes. After these 2: Items A and B closed → moratorium pending 14→12 (or lower after governance correction). This is the single highest-moratorium-impact action available under 30 min.

**Action:** Same as Ideas 1+2, committed together. Update CLAUDE.md Invariant #4 while touching it.

**Impact:** 2 closures (Items A+B) in single 20-25 min commit. Moratorium pending drops 2. Pre-commit Check 10 + pre-push widget guard both active.

**Category:** workflow / code_health

---

### Idea 4: Invoke /god-class-splitter on email_sequences.py (run 41 active_direction)

**Evidence:** email_sequences.py confirmed 1255L (runs 35/41 winner, now day 4+ unimplemented). god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). 3 clean concerns: CRUD (lines 1-400), enrollment (401-800), processor (801-1255). GH #112 N+1 + GH #113 duplication both become isolated post-split. GH #181 billing path now known (backend/routers/billing.py) — critical_standing_action to do first (~15 min) then split.

**Action:** Human invokes `/god-class-splitter` on `email_sequences.py`. Fix GH #181 billing entries as the prerequisite bonus first.

**Impact:** 1255L → 3 modules <600L; N+1 (GH #112) and duplication (GH #113) isolated; code_health win; enables future AI-to-Human Handoff work in cleaner codebase.

**Category:** code_health

---

### Idea 5: Fix GH #181 billing entries — add 15000→autopilot + 25000→professional

**Evidence:** `AMOUNT_TO_PLAN` at `backend/routers/billing.py:263` confirmed missing `15000:'autopilot'` and `25000:'professional'` (direct inspection this run). Prior fix attempts (c72b535, 1eaaeec, PR #183) ALL targeted the wrong path (`backend/services/billing.py`). **New evidence:** billing.py path was first confirmed in run 47. This is genuinely new — wrong-path failures explain 2+ failed attempts. Check 11 Warning fires every commit flagging this gap. In `rejected_paths` but new-evidence exception applies.

**Action:** Add `15000: "autopilot"` and `25000: "professional"` to `AMOUNT_TO_PLAN` dict in `backend/routers/billing.py:263`. Update `test_billing_amount_to_plan.py` — remove backwards assertions, add current-price assertions.

**Impact:** Closes GH #181 (26+ days, Check 11 Warning silenced); billing webhook correctly maps $150/$250 plans; PR #183 can merge; ~15 min S-effort.

**Category:** code_health
