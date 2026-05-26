# Improvement Backlog — 2026-05-26-pm (Run 35)

## Active

- Invoke `/god-class-splitter` on `email_sequences.py` (1255L → 3 modules: email_crud, email_enrollment, email_processor). First production use of new skill. ~2 hours. Human action.

## Critical Standing Action (not a winner — requires human implement/reject decision)

- **GH #181** — Fix `billing.py` AMOUNT_TO_PLAN (add 15000→autopilot + 25000→professional), remove backwards test assertions in `test_billing_amount_to_plan.py`. S-effort ~15 min. Has been recommended 5 consecutive runs. Do this BEFORE the email_sequences split. Full sketch: `subconscious/runs/2026-05-26/winning-concept.md`.

## Parking Lot — Promoted (execute soon)

- **Wire billing-constant-guard as pre-commit Check 11** (ROI 2.1, autonomously executable by nightly review, LOW-risk 10-line bash addition). After GH #181 is applied, Check 11 guards the fixed state. Survived debate round 2 strongly.
- **Batch merge 5 stale Dependabot PRs** (#11-15, 42 days, GitHub Actions bumps — actions/cache, actions/setup-python, actions/setup-node, peter-evans/create-pull-request, actions/upload-artifact). ~5 min. Moratorium-safe.
- **Review + recommend merge of PR #182** (invoices.py god-class split, 3 days, Draft). Morning digest flags it. Verify against god-class-splitter 12-step checklist.

## Parking Lot — Standard

- Fix email_sequences N+1 queries — GH #112 (list_enrollments 1001 queries per 1000 enrollments) + GH #113 (process_sequences duplication). Best addressed AFTER email_sequences.py split (targeted fix in isolated enrollment module).
- Wire check_project_invariants.py into pre-commit as Check 10 (Sprint Item A, 5 min, 3 lines) — moratorium sprint standing action.
- Create scripts/check-widget-sync.sh + wire into pre-push hook (Sprint Item B, 15 min) — moratorium sprint standing action.
- Create .github/workflows/lead-qualifier-eval.yml (Sprint Item D, 20 min) — moratorium sprint standing action.
- Create billing-constant-guard skill (.claude/skills/billing-constant-guard/SKILL.md) — 10-step checklist including CLAUDE.md plan price cross-reference. Promote after GH #181 is fixed and Check 11 is in place.
- Zapier API key plan_status enforcement (GH #107, ROI 2.5, security) — promote to first non-moratorium winner after moratorium exits.
- AI-to-Human Handoff v1 (run 4, 40+ days pending, Critical gap all 7 industries) — customer value, medium effort. Create GH issue first.
- Create post-split-test-repair skill (.claude/skills/post-split-test-repair/SKILL.md) — after god-class-splitter gets one production use.

## Rejected This Run

- **PR #182 review as winner** — KILLED round 3. Operational PR management, not a systemic improvement. Morning digest already surfaces it. Standing action, not subconscious winner material.

## Questions for Next Run

- Was GH #181 billing fix implemented? (critical standing action)
- Was the email_sequences.py split executed? If yes: did GH #112/#113 N+1 fix follow?
- Was PR #182 merged? Any gaps found vs god-class-splitter 12-step checklist?
- Was billing-constant-guard Check 11 added by nightly review tonight?
- Were the 5 stale Dependabot PRs merged?
- Is moratorium still active? Pending count?
