# Improvement Backlog — 2026-05-28 (Run 37)

## Active

- **[Run 37 winner]** Add billing-constant-guard as pre-commit Check 11 (WARNING mode). Autonomously executable by nightly review. 10 lines bash. `HIGH` confidence. See winning-concept.md.
- **[Run 35 standing]** Invoke `/god-class-splitter email_sequences.py` — split 1255L into email_crud + email_enrollment + email_processor. Pre-condition: GH #181 fix first. Human session ~2h.
- **[Run 36 standing]** Create `post-split-test-repair SKILL.md` — 8-step checklist for repointing stale `@patch` decorators and imports after any refactor (god-class splits AND API cleanup migrations). Full content in `subconscious/runs/2026-05-27/winning-concept.md`. Under 1 minute to create. Nightly review didn't act autonomously — needs explicit session or direct human creation.

## Critical Standing Actions (Human Required — Not New Pending Items)

- **GH #181** — `billing.py` AMOUNT_TO_PLAN missing `15000→autopilot` + `25000→professional`. ~15 min, S-effort. Do before email_sequences split. `CRITICAL`
- **Moratorium Sprint Items A/B/D** — check_project_invariants pre-commit (~5 min), widget sync guard (~15 min), CI eval workflow (~20 min). Total ~40 min.

## Parking Lot (Survived Debate or Promoted)

- **post-split-test-repair SKILL.md** — WEAKENED in debate (loses to billing-constant-guard on all criteria, not because it's invalid). 3 occurrences confirmed (5f2cd2b, 4afb3cf, bca2082). Broader scope than god-class splits — fires after API cleanup migrations too. Create before email_sequences split. Full content in runs/2026-05-27/winning-concept.md.
- **Agent OS outbound delivery failure tracking** — KILLED in debate (wrong timing post-merge, moratorium conditions, no confirmed silent-swallow bug). Valid operational need. Revisit after moratorium exits and Agent OS has real usage data. Consider: structured `logger.error()` in `os_outbound_mirror.py` exception handlers (no migration needed).
- **Wire check_project_invariants.py into pre-commit as Check 10** — moratorium Item A, 3-line bash, 5 min. Sprint dependency.
- **Wire golden eval harness to CI (.github/workflows/lead-qualifier-eval.yml)** — moratorium Item D. Sprint dependency.
- **email_sequences N+1 fixes (GH #112/#113)** — Best done after god-class split. N+1 in `list_enrollments` and duplicate processor loop. Blocked on email_sequences split.
- **AI-to-Human Handoff v1 (Run 4, 42 days)** — Oldest pending customer-value item. Critical gap all industries. Infrastructure exists. Promote when moratorium exits.
- **Zapier plan_status enforcement (GH #107)** — ROI 2.5, security. Promote to first non-moratorium winner.
- **GH #93 billing fraud false-positive** — HIGH severity, 31 days. Promote to next post-moratorium window.
- **billing-constant-guard CI enforcement (pr-check.yml)** — Step 2 after Check 11 + GH #181 fix. Promotes WARNING to FAIL in CI.

## Rejected This Run

- **Agent OS delivery monitoring** — KILLED. No confirmed bug. Wrong timing (post-merge moratorium conditions). Adds migration to pending queue. Parking lot.

## Questions for Next Run

1. Was billing-constant-guard Check 11 implemented by nightly review? (Check `scripts/hooks/pre-commit` for Check 11 block.)
2. Was GH #181 fixed? (Check `billing.py:263` for `15000` and `25000` entries — Check 11 WARNING will be silent if fixed.)
3. Was post-split-test-repair SKILL.md created? (Check `.claude/skills/post-split-test-repair/SKILL.md`.)
4. Was email_sequences.py split executed? (Check `wc -l backend/routers/email_sequences.py` — should drop below 600L if split.)
5. Are moratorium Items A/B/D still MISSING? (`scripts/check-widget-sync.sh`, `check_project_invariants` in pre-commit, `.github/workflows/lead-qualifier-eval.yml`.)
6. Any new Agent OS bugs or delivery failures surfaced in nightly logs or Railway errors?
