# Morning Digest — 2026-06-05

> Generated: 2026-06-05 | Run 50 subconscious active

---

## Commits (last 24h)

- `da25e94` subconscious: run 2026-06-05 — Extend nightly scope + Item B AUTONOMOUS-EXECUTABLE (widget sync guard)
- `349bed9` docs: auto-log bug fix from 8db33df
- `8db33df` fix: replace em dashes with hyphens in UI copy (personality.md rule) ← **Item A unblocked**
- `829d741` ops: morning-digest 2026-06-04

**4 commits. Run 49 winner executed by nightly. Moratorium chain advancing.**

---

## Project Invariants

```
PASS  FastAPI router files avoid future annotations
PASS  active backend code avoids retired live-schema fields
PASS  retired plan names do not appear in plan-related code
PASS  widget assets are byte-identical across mirrors
PASS  website source avoids em dashes            ← NEW (was FAIL yesterday)
PASS  direct Anthropic SDK message creation stays behind runtime wrapper
```

**All 6 PASS. check_project_invariants.py exits 0.** Tonight at 2:37 AM nightly auto-wires Check 10 to pre-commit.

---

## Issues Updated (last 24h)

| # | Title | Status |
|---|-------|--------|
| #201 | Morning digest 2026-06-04 | open (stale — close when done) |

No new issues filed in last 24h.

---

## Open PRs Needing Action

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| #200 | subconscious run 49 — Extend nightly SKILL.md + 5 JSX em-dashes | 2d | yes | **review + merge** (nightly needs scope) |
| #198 | bump @typescript-eslint/parser 8.58→8.60 | 3d | no | merge or close |
| #197 | bump eslint 9.39→10.4 | 3d | no | merge or close |
| #190 | fix(os-workers): inject business profile into worker prompts | 8d | yes | review |
| #183 | subconscious run 33 — GH #181 billing fix | 12d | yes | **merge — confirmed path** |
| #182 | Split invoices.py god class into 4 service modules | 13d | yes | decide: merge or abandon |
| #12–15 | Dependabot GH Actions bumps | 52d | no | **batch close — stale** |

---

## Subconscious Recommendation (Run 50)

**AUTONOMOUS-EXECUTABLE: Item B widget sync guard fires tonight.**

Run 49 winner landed (8db33df). Invariants all PASS. Nightly at 2:37 AM:
1. Wires Check 10 to `scripts/hooks/pre-commit` (Item A closes).
2. Creates `scripts/check-widget-sync.sh`, wires into pre-push, updates CLAUDE.md Invariant #4 (Item B closes).

Both in same cycle. Zero human action required beyond merging PR #200 (nightly reads SKILL.md scope from main).

Bonus actions identified:
- **GH #181** — billing.py AMOUNT_TO_PLAN missing `autopilot` ($150) + `professional` ($250). PR #183 ready.
- **Zapier API key** — `zapier_auth.py` missing `plan_status IN ('active','trialing')` filter. Create `ai-ready` issue → issue-to-pr-loop handles it.

---

## Top 3 Priorities Today

### 1. Merge PR #200 — 5 min
SKILL.md scope extension required for nightly to execute Item B autonomously tonight. PR is draft but correct.
```
gh pr ready 200 && gh pr merge 200 --squash
```

### 2. Merge PR #183 (GH #181 billing fix) — 10 min
`backend/routers/billing.py:263` missing `autopilot` + `professional` prices. PR 12 days old. Confirmed path.
```
gh pr review 183 --approve && gh pr merge 183 --squash
```

### 3. Batch close Dependabot PRs #12–15 — 5 min
52 days stale. GH Actions bumps. Close as superseded.
```
for pr in 12 13 14 15; do gh pr close $pr -c "superseded by current dep audit"; done
```

---

## Blockers Carrying Forward

- **CI broken** — #185 pyo3/cryptography failures blocking pytest. Not blocking local dev.
- **Moratorium** — #193 ongoing. Items A + B close TONIGHT autonomously if PR #200 is merged.
- **PR #182** — invoices.py god class split, 13d draft. Needs a merge-or-abandon call.

---

*Nightly review: 2:37 AM. KB autopop: 6 AM / 6 PM.*
