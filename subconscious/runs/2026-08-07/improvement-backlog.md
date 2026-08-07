# Improvement Backlog — Run 102 (2026-08-07)

## Parking lot from this run

### Idea 2 — Fix kb-autopopulate.yml to exit 1 when KB log not updated
- **Status:** parking_lot (S effort, human-reviewable, not autonomous channel)
- **Action:** File GH issue (human-action-required, medium-risk) requesting review of `.github/workflows/kb-autopopulate.yml` continue-on-error pattern + add exit-1 verification step
- **Priority:** HIGH — root-cause fix for the silent-green pattern

### Idea 3 — feature-docs-trio skill
- **Status:** parking_lot — 3 occurrences in 7-day window, evidence validated
- **Evidence:** `docs/skill-discovery/2026-07-27.md`; e0e9be6 (22-file insights feature) shipped 2026-08-06 with zero docs
- **Action:** Create `.claude/skills/feature-docs-trio/SKILL.md`
- **Priority:** MEDIUM — compound benefit but not a mandate item

### Idea 4 — Grandfathered plan gate audit
- **Status:** parking_lot — grep-only audit, zero risk
- **Evidence:** `2869124` fixed one gate missing grandfathered plans; no comprehensive audit since
- **Action:** Grep `backend/routers/` for plan gates omitting growth/autopilot/professional/enterprise; file GH issue with list
- **Priority:** MEDIUM — revenue protection, low effort

### Idea 5 — Typed KB notes discovery banner
- **Status:** parking_lot — M effort, frontend change
- **Evidence:** PR #632 shipped typed notes with no UX surface
- **Priority:** LOW — discoverability improvement, not urgent

## Carried from run 101 parking lot

- **Nexlify Score token-burn guard** — response_score.py shipped in e0e9be6; verify no unbounded AI calls per-request. WEAKENED (speculative without reading the file). Deferred.
- **Step 9H redesign** — redesigned idempotent alerting for PR pile-up. Deferred pending PR merge activity.
