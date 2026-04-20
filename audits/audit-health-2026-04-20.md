# Codebase Health Audit — 2026-04-20

Autonomous scan after Opus 4.7 prompting migration sweep. Three commits landed today on main (local, not pushed — SSH sandbox-blocked):

- `42f4362` — advisor_executor style flip + KB article
- `4362424` — 4.7 prompting migration sweep (feature-build, ai-feature-pattern, parallel-approaches, compound-engineering, /ultraplan)
- `ee2cfe3` — initial 4.7 moves (grill-me batch, karpathy + opus-advisor + sonnet-executor flips)

User: run `git push origin main` when back at terminal (3 commits ahead).

---

## Findings

### 1. Silent failure patterns — MEDIUM
Scan: `except Exception:` across `backend/services/`.

Top hotspot: **`backend/services/noshow_recovery.py`** with **15+ bare `except Exception:` blocks** at lines 56, 71, 89, 122, 132, 150, 181, 191, 202, 240, 260, 298, 316, 342, 351.

Each needs human review to determine:
- Is the exception logged?
- Is a fallback value returned?
- Does the exception indicate a real failure that should halt the recovery sequence?

**Risk:** silent drop of no-show recoveries = missed revenue. Tenant-facing.

**Recommended action:** assign to a dedicated debugging session with `systematic-debugging` skill. 15 sites × ~3 min review each = ~45 min.

Other files with silent-failure patterns (lower volume):
- `backend/services/lead_qualification.py:368, 390`
- `backend/services/url_validation.py:45`
- `backend/services/webhook_dispatcher.py:89, 143`

### 2. God classes — HIGH priority, DEFERRED
Scan: files >600 lines (per CLAUDE.md user-rules.md Rule 9).

Top offenders:

| File | Lines | Notes |
|---|---|---|
| `frontend/src/pages/SettingsPage.jsx` | 2,262 | Tabs per plan / integration — split per tab |
| `widget/agentnexlify-widget.js` | 2,043 | **DO NOT SPLIT** — byte-identical rule (CLAUDE.md invariant #4) |
| `frontend/src/pages/ConversationsPage.jsx` | 2,039 | Inbox + drawer + filters — split |
| `frontend/src/pages/Dashboard/LeadDetailDrawer.jsx` | 1,688 | Drawer tabs — split |
| `frontend/src/pages/EmailSequencesPage.jsx` | 1,554 | Builder + list — split |
| `backend/routers/local_seo.py` | 1,552 | Multi-feature router — split by concern |
| `frontend/src/pages/LocalSEOPage.jsx` | 1,525 | Paired with router above |
| `backend/routers/auth.py` | 1,487 | **HIGH RISK to refactor** — needs plan + tests first |
| `frontend/src/pages/WidgetPage.jsx` | 1,398 | Widget admin — split |
| `backend/tests/test_managed_agents.py` | 1,333 | Test file — acceptable, but could split by feature |
| `frontend/src/pages/DocumentsPage.jsx` | 1,311 | Tabs — split |
| `frontend/src/pages/FormBuilderPage.jsx` | 1,306 | Builder — split |
| `frontend/src/pages/Home.jsx` | 1,254 | Dashboard widgets — split |
| `backend/routers/invoices.py` | 1,211 | Router — split per endpoint group |

**Recommended action:** run `improve-architecture` skill (Monday cadence per `daily-skills.md §5`) then compound-engineering in a separate session to refactor one at a time. User-rules.md Rule 8 forbids half-migrations.

### 3. Dependency rot — NOT SCANNED THIS PASS
Skipped `dependency-auditor` — read-only but needs network egress to npm/pypi CVE feeds. Can run next session.

### 4. TODO / FIXME debt — CLEAN
Zero TODO/FIXME/XXX/HACK markers in `backend/`, `frontend/src/`, `widget/`. Cleanest state in memory.

### 5. Opus 4.7 prompting migration — COMPLETE
Covered by today's 3 commits. New rule `.claude/rules/opus-4-7-prompting.md` documents the 5 moves; audit checklist in § Audit Checklist. KB article `knowledge-base/raw/opus-4-7-prompting-migration-2026-04-20.md` awaits next compile cron.

Remaining 4.7 audit targets NOT touched (low hit count, low ROI):
- `.claude/skills/obsidian-sync/SKILL.md` (4 negatives)
- `.claude/skills/dead-code-sweep/SKILL.md` (4)
- `.claude/skills/ubiquitous-language/SKILL.md` (3)
- `.claude/skills/improve-architecture/SKILL.md` (3)
- `.claude/skills/edit-article/SKILL.md` (3)
- `.claude/skills/build-loop/SKILL.md` (3)

---

## Ranked next-session action list

1. **Push 3 local commits** — trivial, 10s at terminal with SSH access.
2. **Triage `noshow_recovery.py` silent failures** — 45 min with `systematic-debugging` skill.
3. **Plan god-class split for `frontend/src/pages/SettingsPage.jsx`** — largest non-widget file (2262 lines). Use `improve-architecture` + `compound-engineering` on separate branch.
4. **Run `dependency-auditor`** — surface any outstanding CVEs.
5. **Tackle remaining low-hit 4.7 audit skills** — 10 min batch if desired, otherwise skip.

---

## Smoke-test status
- `backend.services.advisor_executor` imports clean after style flip — PASS
- `backend.services.llm_runtime` imports clean — PASS
- `backend.services.managed_agents_registry` imports clean — PASS
- Pre-commit hook green on all 3 commits — PASS
- Pytest blocked by pre-existing `widget/` path issue in `backend/main.py:817` when run from `backend/` cwd — NOT MY REGRESSION (file path was already brittle before today)

## Commits ahead of origin/main (push when available)
1. `ee2cfe3` — rules apply batch-mode + positive examples (5 files)
2. `4362424` — finish migration sweep (6 files)
3. `42f4362` — advisor_executor flip + KB article (2 files)

Total: 13 files changed, +250 / -76. Zero runtime behavior change — phrasing and references only.

Verified: `git log --oneline -5` matches expected — PASS.
