# Improvement Backlog — 2026-08-03 (Run 103)

## Winner (Implemented This Run)
- **Step 9G: KB autopopulate self-healing trigger** (run 100→101→102→103 winner, 4th-cycle carry-forward — IMPLEMENTED DIRECTLY)
  - Status: implemented (subconscious run 103, direct implementation per run_103_mandate escalation)
  - Effort: XS (~28 bash lines in SKILL.md)
  - Channel: nightly-commit-review SKILL.md-edit (proven autonomous)

---

## Parking Lot

### High Priority (promote run 102-103)
- **agent-os-extension skill** — 9 PRs in 7 days, 2-3x/week frequency, 15-25 min saved/occurrence
  - Blocked by: nothing. PR #619 capabilities sprint (50+ files) proves need. Promote when sprint settles.
  - Skill file: `.claude/skills/agent-os-extension/SKILL.md`
  - Pattern: service → router → Pydantic → test → frontend → wire-in to managed_agents_registry.py

### Medium Priority (promote run 103-105)
- **notification-layer-add skill** — 6 occurrences/3 days, 2-3x/month, 25-40 min saved
  - notify_common.py skeleton now stable (nightly-2026-07-17). Safe to codify.
  - Skill file: `.claude/skills/notification-layer-add/SKILL.md`

- **digest-job-add skill** — 1 occurrence + 2 bug classes (blind-state guard + permissions:issues:write)
  - Lower urgency than agent-os-extension but same category
  - Skill file: `.claude/skills/digest-job-add/SKILL.md`

### Watching (conditional promotion)
- **LoopHealthPage.jsx** — promote when Agent OS >5 active tenants (currently 2-3)
- **MCP quickstart doc** — promote on second MCP tenant activation (currently 1)
- **client_id audit, capabilities layer** — nightly already catches violations; resurface if PR #619 surfaces another miss
- **kb_hybrid enable** — needs settings UI or GH #399 resolution first

---

## Killed / Rejected This Run
- **client_id audit** (one-time scan; nightly catches individual violations; lower compounding value than Step 9G)
- **digest-job-add skill** (lower urgency this cycle; parking lot)

---

## Pending Human Actions (unchanged from prior runs)
- GH #413: REFERRAL_REWARD_ENABLED=1 in Railway Variables (2-minute flip; referral program fully built)
- GH #415: Keys Koffee business hours (email/call owner; first booking unblocked)
- GH #399: AUTOPILOT_GH_TOKEN rotation (30+ ai-ready issues blocked)

---

## Frozen Ideas (never re-propose)
- ai_human_handoff (frozen, rejected 3+ times)
- MCP Step 9H monitoring (killed run 100 — 1 tenant only, premature)
