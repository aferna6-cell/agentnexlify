# Nightly Review — 2026-04-24

Run at: 2026-04-24 (UTC)
Commits window: last 24 hours (since 2026-04-23)
Total commits reviewed: 14

---

## Commits reviewed

| SHA | Message | Risk |
|-----|---------|------|
| 821f660 | Update Stripe pricing and Growth trial | HIGH (FORBIDDEN) |
| ab0b6e1 | chore(backend): bump dotenv and multipart security pins | LOW — clean |
| 92c9424 | docs: auto-log bug fix from fd37906 | LOW — docs only |
| fd37906 | fix(noshow_recovery): CAN-SPAM default-deny + escalate log | LOW — good fix |
| f2e22fb | chore(ai): noshow_recovery.py + tests | MEDIUM — reviewed, clean |
| df1e87c | chore(ai): .claude/settings.local.json | LOW — dev config |
| 9a7d40a | chore(ai): docs/content updates | LOW — docs only |
| dfcafcc | chore(ai): settings.local.json + email doc | LOW — docs only |
| 736b5d9 | chore(ai): large multi-file auto-commit | MEDIUM — reviewed below |
| 448ff18 | chore(ai): .claude/settings.local.json | LOW — dev config |
| 51e49bd | feat(positioning): home hero + meta tags | LOW — clean |
| 55c4992 | feat(audits): competitive + positioning audit | LOW — docs only |
| 65cca61 | chore(ai): new scheduled_jobs/ subpackage | MEDIUM — issue filed |
| 370725c | chore(ai): frontend-patterns.md rule | LOW — docs only |

---

## Findings

### Issues opened (2)

- **[HIGH] #81** — `billing.py` AMOUNT_TO_PLAN wrong plan mappings (821f660)
  - `$150 → "professional"` should be `"autopilot"`
  - `$250 → "enterprise"` should be `"professional"`
  - `$899 enterprise` entry completely removed
  - Inconsistent with `admin_analytics.py` PLAN_PRICES and CLAUDE.md
  - Primary webhook resolution (via `metadata.plan`) still works; this affects fallback path
  - **FORBIDDEN path** — not auto-fixed; human review required

- **[MEDIUM] #82** — `scheduled_jobs/` directory is dead code (65cca61)
  - New 7-file subpackage lacks `__init__.py`
  - Python resolves `scheduled_jobs` to the `.py` shim — new directory unreachable
  - Internal imports (`scheduled_jobs._common`) would `ModuleNotFoundError` if activated
  - Duplicate of logic already in `scheduled/` directory
  - No current runtime impact; latent breakage risk

### Fixed autonomously (0)

No LOW-risk bugs auto-fixed this run.

Notes:
- `frontend/index.html` meta description pricing appeared stale in commit 51e49bd ("Flat $249/mo") but was already corrected by a subsequent commit to "from $99/mo" — no action needed.
- `noshow_recovery.py` CAN-SPAM fix (fd37906 / f2e22fb) was a correct, already-landed improvement. Reviewed and confirmed clean.
- `admin_analytics.py` PLAN_PRICES update (736b5d9) correctly maps current prices. Clean.
- Dependency bumps (ab0b6e1): `python-dotenv` 1.0.1→1.2.2, `python-multipart` 0.0.22→0.0.26 — security patches, clean.
- `FREE_TRIAL_DAYS` 14→7 in `branding_service.py` (736b5d9) — intentional, consistent with Stripe `trial_period_days: 7` in auth.py.

### Skipped (FORBIDDEN paths touched)

- `backend/routers/auth.py` — touched by 821f660 (removed `free_trial_started_at` from provisioning, added trial null guard). Intentional; consistent with new Stripe-managed trial.
- `backend/routers/billing.py` — touched by 821f660 (HIGH issue filed above) and 736b5d9 (pricing update).
- `widget_chat.py` — free trial expiry check removed (821f660). Intentional; all plans now have unlimited conversations.

---

## Guardrail check

- Files changed this run: 0 (no auto-fixes applied)
- LOC changed: 0
- agent-system:check: skipped (no push)
- Pre-push hook: skipped (no push)

---

## Next action

**2 issues need human review:**
- #81 HIGH: Verify billing.py AMOUNT_TO_PLAN plan names against Stripe dashboard before correcting
- #82 MEDIUM: Decide whether to keep new `scheduled_jobs/` package or remove it (either add `__init__.py` + retire `scheduled_jobs.py`, or delete the new directory)
