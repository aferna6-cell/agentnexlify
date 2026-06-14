# Nightly Commit Review — 2026-06-02

**Run time:** 2026-06-02 UTC  
**Commits reviewed:** 7 (last 24h)  
**Issues opened:** 0  
**Autonomous fixes applied:** 0  
**Status:** No issues found

---

## Commits Reviewed

| SHA | Message | Risk | Finding |
|-----|---------|------|---------|
| `e7e0a3b` | fix(nightly): em-dash in comments [auto-nightly-2026-06-01] | LOW | Comment-only changes in `App.jsx` + `os-inbound.js`. No logic change. Clean. |
| `4226ef4` | docs(skill): extend nightly autonomous scope for pre-commit bash additions | LOW | SKILL.md docs update only. Extends autonomous scope definition (with pre-condition guard). Clean. |
| `d1f8acc` | ops: nightly-commit-review 2026-06-01 | LOW | Ops log. Clean. |
| `f992c3e` | subconscious: run 2026-06-01 (run 44) | LOW | Subconscious system run — governance state + debate log. No production code. Clean. |
| `c5746bd` | ops: morning-digest 2026-06-01 | LOW | Ops log. Clean. |
| `4d9263b` | ops: kb-drift sweep 2026-06-01 — no drift detected | LOW | Ops log. Clean. |
| `82f4627` | subconscious: run 2026-06-01-pm (run 45) | LOW | Subconscious PM run — governance correction + debate log. No production code. Clean. |

---

## Invariants Check

`python3 scripts/check_project_invariants.py` → **EXIT 1**

```
PASS FastAPI router files avoid future annotations
PASS active backend code avoids retired live-schema fields
PASS retired plan names do not appear in plan-related code
PASS widget assets are byte-identical across mirrors
FAIL website source avoids em dashes
  - frontend/src/pages/IntegrationsPage.jsx:1018
  - frontend/src/pages/SettingsInboundChannels.jsx:220
  - frontend/src/pages/SettingsInboundChannels.jsx:221
  - frontend/src/pages/settings/MessagingSettingsCards.jsx:263
  - frontend/src/pages/settings/MessagingSettingsCards.jsx:276
PASS direct Anthropic SDK message creation stays behind the runtime wrapper
1 invariant(s) failed.
```

These are intentional UI display em-dashes (dropdown placeholders, separator characters) — not backend naming violations. Tracked in GH #194. The fix is to scope `check_project_invariants.py` to skip `.jsx`/`.tsx` in the em-dash walk + wire Check 10 to `scripts/hooks/pre-commit`. This is **Item A** (run 45 winner).

---

## Item A Status

- **Run 45 winner:** Scope em-dash check to skip `.jsx`/`.tsx` + wire Check 10 to pre-commit (~10 min)
- **Autonomous execution:** NOT authorized — run 45 explicitly marks this HUMAN-EXECUTE
- **Governance:** `active_directions` entry has no `autonomous_executable: true`; pre-condition (script exits 0) also fails
- **Blocked by:** JSX em-dash violations in UI copy (GH #194)
- **Action:** No autonomous action. Human execution required per run 45 winning-concept.md

---

## Summary

No bugs found in today's commits. All 7 commits are documentation/ops/subconscious artifacts with no production logic changes. The em-dash invariant failure is a known, tracked issue (GH #194) — not a regression from today's commits. Pre-commit hook does not yet have Check 10.

**Next:** Human should execute Item A per `subconscious/runs/2026-06-01-pm/winning-concept.md` (~10 min, closes GH #194, wires Check 10).
