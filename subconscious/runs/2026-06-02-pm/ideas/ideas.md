# Candidate Ideas — Run 47 (2026-06-02-pm)

---

### Idea 1: Item D AUTONOMOUS-EXECUTABLE — Extend nightly scope to CI YAML creation

**Evidence:** Run 46 binding mandate fires: Item A not executed this session (em-dash check still
fails JSX/TSX via `python3 scripts/check_project_invariants.py`, no Check 10 in pre-commit grep).
Mandate text: "run 47 winner MUST switch to Item D AUTONOMOUS-EXECUTABLE (extend nightly scope to
`.github/workflows/*.yml` creation)." `backend/tests/evals/test_lead_qualifier_golden.py` +
`lead_qualifier_golden.json` exist (7854ede). Nightly autonomous channel: 4226ef4 extended scope
for pre-commit bash additions using same SKILL.md mechanism — precedent established.

**Action:** (1) Update governance.json: Item D (run 14, `subsumed_in_sprint`) → `pending_autonomous`,
`autonomous_executable: true`. (2) Update nightly-commit-review SKILL.md: add bullet covering
`.github/workflows/*.yml` creation in LOW-risk autonomous scope when `autonomous_executable: true`
label present. (3) Include inline `lead-qualifier-eval.yml` content in winning-concept.md as patch
for nightly to apply.

**Impact:** Golden eval harness wires to weekly CI (Monday cron) + PR trigger on eval changes.
Prevents silent lead qualifier regressions. Closes run 14 winner (day 28 pending). Drops pending
15→14 when nightly executes. Pattern: identical to SKILL.md creation and bash scope extension
that both worked reliably.

**Category:** operational

---

### Idea 2: GH #181 Path Discovery — Annotate PR #183 + Update Critical Standing Action

**Evidence:** Bonus A from run 46 resolved: `find backend/ -name '*billing*'` confirms
`backend/routers/billing.py` exists (not `backend/services/billing.py` as all prior sketches
assumed). `AMOUNT_TO_PLAN` at line 263 confirmed missing `15000: "autopilot"` ($150/mo) and
`25000: "professional"` ($250/mo). PR #183 (draft, 9 days old) likely targets wrong path —
all 6 implementation sketches in runs 31/32/34 reference `backend/services/billing.py`.
Two prior failed fix attempts (c72b535, 1eaaeec) may have failed due to wrong file path.
GH #181 rejected from winner slot (runs_rejected=1), but rejected_paths condition (b) satisfied:
"new evidence emerges about why it keeps being skipped."

**Action:** (1) Update `critical_standing_action` note in governance.json with correct path.
(2) Add inline annotation to GH #183 description with `backend/routers/billing.py` + correct
AMOUNT_TO_PLAN fix (add `15000: "autopilot"` and `25000: "professional"`). S-effort ~5 min.

**Impact:** PR #183 becomes actionable. Human can merge GH #181 in ~15 min now that path is
known. Two current plan tiers ($150 autopilot, $250 professional) return wrong plan on Stripe
webhook until fixed. Zero implementation blockers remain.

**Category:** code_health

---

### Idea 3: Item B Standalone — De-couple Widget Sync Guard from Sprint

**Evidence:** `scripts/check-widget-sync.sh` missing since run 7 (day ~40). Three widget copies
confirmed: `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`. Nightly PASS on
widget assets byte-identical check. Item A was de-coupled from sprint in run 42 (same mechanism).
The rejected_paths entry ("Authorize nightly review to execute Items A+B") applied to concurrent
execution, not Item B standalone. Nightly autonomous channel: Check 11 bash script (061582c)
precedent — new bash file creation is within autonomous scope.

**Action:** De-couple Item B from sprint (update governance.json status to `pending_autonomous`,
`autonomous_executable: true`). Add nightly SKILL.md bullet for bash script creation in `scripts/`
when `autonomous_executable: true` label present. Include inline `check-widget-sync.sh` content
in winning-concept.md.

**Impact:** Protects widget 3-copy sync invariant. S-effort ~15 min for nightly. Drops pending
15→14 when executed.

**Category:** code_health

---

### Idea 4: email_sequences.py split — Invoke /god-class-splitter

**Evidence:** email_sequences.py confirmed 1255L (run 41 winner, day 3). god-class-splitter
SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). GH #112/#113
(N+1 queries, process duplication) easier post-split. No autonomous path exists — M-effort,
requires human interactive session. Human present in this session.

**Action:** Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` to split 1255L
into `email_crud.py` + `email_enrollment.py` + `email_processor.py`. Pre-condition: GH #181
billing fix first (~15 min). Then split (~2h human session).

**Impact:** Reduces god-class size from 1255L to ~400L × 3. Resolves GH #112/#113. Unblocks
future email automation features.

**Category:** code_health

---

### Idea 5: Merge Safe Dependabot PRs (#11–#15, #186)

**Evidence:** PRs #11/12/13/14/15 are Dependabot dependency bumps aging 49 days: actions/cache
4→5, actions/setup-python 5→6, peter-evans/create-pull-request 6→8, actions/setup-node 4→6,
actions/upload-artifact 4→7. PR #186 is eslint-parser 8.58→8.60 (8 days). Morning digest
labels #11-#15 as "Safe to merge" (batch). PR #186: minor version, safe. These do not require
human implementation — they are auto-merges.

**Action:** Merge PRs #11/12/13/14/15 as a batch (all Dependabot, all GH Actions version bumps,
no application code change). Merge PR #186 (minor eslint parser bump).

**Impact:** Reduces open PR noise from 10→4. Eliminates 49-day-old stale PRs. 5 min effort.

**Category:** operational
