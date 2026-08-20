# Nightly Commit Review — 2026-08-20

**Run time:** 2026-08-20 (automated)
**Commits reviewed:** 3 (last 24h)

---

## Commits Triaged

| SHA | Message | Risk | Action |
|-----|---------|------|--------|
| `2e4dc26` | ops: morning-digest 2026-08-19 | LOW | No action — log file only |
| `dccd591` | subconscious: run 2026-08-19 — Step 9I nightly demo-role security sweep | LOW | No action — skill file + subconscious artifacts, no prod code |
| `d247e81` | ops: nightly-commit-review 2026-08-19 | LOW | No action — log file only |

**No bugs found in commits. No fixes committed.**

---

## Step 9I: Demo-Role Security Sweep

First automated execution of Step 9I (added by subconscious run 107 on 2026-08-19).

**Scan result:**
- Files scanned with mutating routes (POST/PUT/DELETE/PATCH): **112**
- Excluded (skip list — auth, external webhooks, public widget): **15**
- Remaining checked: **97**
- Missing `block_demo_role`: **97 of 97**

**Dedup against existing open issues:**
- `appointment_briefs.py` → already tracked GH #643 — skip
- `scoring_config.py` → already tracked GH #660 / #661 — skip

**New issues filed: 1**
- GH #669: `[security] Class-wide: 95 routers missing Depends(block_demo_role) on mutating endpoints`
  - Labels: security, nightly-review, backend
  - Lists all 95 untracked files; recommends middleware-level batch fix over per-file patching

---

## Status of Ongoing Blockers (from subconscious governance)

- **KB staleness:** Still stale (last entry 2026-07-23 = 28 days). GH #403 (ANTHROPIC_API_KEY in GH Actions) still open. Run 107 posted targeted comment with setup path. Human action required.
- **GH #399 (AUTOPILOT_GH_TOKEN):** Still blocking issue-to-pr-loop. Day 40+. Human action required.
- **SUPABASE_ACCESS_TOKEN last_rotated:** Not filled in by human. See ops/credential-rotation-schedule.md.
- **Dependabot PRs (#629/#630/#631/#649/#665/#666):** Still aging. Step 9J (auto-merge) flagged as run 108 candidate.
- **PR #653:** Still draft.

---

## Summary

No code bugs found in last 24h commits. All three commits were operational/automation artifacts.

Step 9I sweep executed for first time — confirmed class-wide gap: **97 of 97 checked routers** missing `Depends(block_demo_role)` on mutating endpoints. Filed GH #669 as consolidated tracking issue. Recommendation: middleware-level guard rather than 95 individual patches.

Human attention needed: ANTHROPIC_API_KEY (GH #403), AUTOPILOT_GH_TOKEN (GH #399), SUPABASE_ACCESS_TOKEN rotation date.
