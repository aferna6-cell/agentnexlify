# Ideas — Run 110 (2026-08-25)

## Evidence Digest
- Step 9J first execution: 0 PRs merged (correct — minor/patch candidates all `mergeable_state: unknown`; major-version bumps correctly blocked). Working as designed.
- 4 open subconscious draft PRs: #575 (32d stale), #626 (22d stale), #653 (12d — block_demo_role middleware), #674 (1d — Step 9J). Run 110 mandate threshold ≥3 met.
- Step 9I sweep: 10 routers still missing block_demo_role, all tracked under GH #669.
- GH Actions dark (fix(ci) 4c45e67 unscheduled 11 workflows) → Step 9G skipped; KB 33d stale; brain connector 33d stale → GH #684 filed by nightly.
- Managed-agents audit (08e9178) shipped 7 fixes. Appointment ghost-confirmation fix (decc1e9) shipped.
- memory.jsonl: run 109 appended two identical entries (dedup bug).
- PR #653 (block_demo_role middleware proposal) 12d draft, no merge.

---

### Idea 1: Step 9K — Stale Subconscious PR Closer in nightly-commit-review SKILL.md
**Evidence:** Run 110 mandate explicitly names Step 9K as candidate. 4 open draft PRs (>= 3 threshold). #575 (32d) and #626 (22d) are superseded by direct SKILL.md implementations. PR noise obscures the current actionable item (#674). Same autonomous-executable SKILL.md channel as Steps 9F/9G/9I/9J.
**Action:** Add Step 9K block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9J's log line. Logic: list open PRs with head branch `subconscious/*` or title prefix `subconscious:`; for each: (a) if concept implemented in governance.json active_directions AND older than 7 days → close with "Superseded by direct implementation — closing stale draft"; (b) if older than 21 days and no newer superseding PR → post escalation comment; log Step 9K count.
**Impact:** Permanent PR queue hygiene. Reduces reviewer noise to 1 actionable PR at a time. Auto-closes superseded drafts within 24h of implementation. Compounds indefinitely.
**Category:** workflow

---

### Idea 2: memory.jsonl Dedup Guard in Subconscious SKILL.md Phase 6
**Evidence:** Run 109 appended two identical entries to memory.jsonl (both `{"run": 109, "winner": "Step 9J..."}`). Governance.json `run_109_mandate_executed` was also written twice. Over 110 runs this could accumulate noise making memory.jsonl unreliable as a 5-entry historical reference.
**Action:** Add dedup check in Phase 6 of `.claude/skills/subconscious/SKILL.md`: before appending to memory.jsonl, read last entry; if `run` matches current run number, skip append. One-line guard.
**Impact:** Prevents false-double entries in memory history. Small structural fix. XS effort.
**Category:** workflow

---

### Idea 3: Step 9J Fallback — Comment on Stale Minor Dependabot PRs When GH Actions Dark
**Evidence:** Step 9J found 19 Dependabot PRs but merged 0 because `mergeable_state: unknown` (GH Actions dark). PRs #665/#666 are 7d old, #630 is 21d old. With GH Actions dark, `mergeable_state` may never reach "clean" automatically. Current Step 9J has no fallback path for this case.
**Action:** Update Step 9K block (or Step 9J) to add fallback: if `mergeable_state: unknown` AND PR has no merge conflicts AND is minor/patch bump → post a comment listing the PR as "safe to merge manually" and label it `ready-for-human`. This surfaces the gap to the owner.
**Impact:** Recovers value from Step 9J when GH Actions dark (current situation). Non-blocking to Step 9K which is more valuable.
**Category:** workflow

---

### Idea 4: Block_demo_role Middleware in main.py (Closes GH #669 Class-Wide)
**Evidence:** 97 routers missing block_demo_role per GH #669 (filed 2026-08-20). PR #653 has the middleware draft (12d). Step 9I sweeps nightly but only reports — doesn't fix. One middleware in `main.py` (or a FastAPI dependency on the APIRouter) would apply block_demo_role to all non-GET non-admin non-healthz routes without touching 97 files.
**Action:** Add `app.middleware("http")` or `router.dependencies=[Depends(block_demo_role)]` in `backend/main.py`. Exclude: GET routes, `/api/v1/healthz`, `/api/v1/webhook/*`, `/api/v1/widget/*` (widget chat must stay open), `/api/v1/public/*`. File as PR targeting GH #669.
**Impact:** Closes 97-router security gap in one commit. HIGH security value. But requires code review — not autonomous-executable.
**Category:** code_health

---

### Idea 5: Add "Step 9J GH-Actions-Dark Awareness" — Skip with Diagnostic Instead of Silent Unknown
**Evidence:** nightly-2026-08-25 Step 9J ran and found 19 PRs but all minor/patch showed `mergeable_state: unknown`. Root cause: GH Actions dark (fix(ci) 4c45e67). Step 9J currently has no awareness of this state — it will repeat the same 0-merge result every nightly until GH Actions light back up. This wastes time and produces misleading logs.
**Action:** Update Step 9J block in SKILL.md: before listing Dependabot PRs, check if GH Actions are running by checking recent workflow runs; if dark (0 runs in 24h on main CI workflows), log "Step 9J: GH Actions dark — mergeable_state unknown for all PRs. Manual merge needed. See GH #500." and skip the merge loop.
**Impact:** Honest logging. Avoids misleading "0 merged" when root cause is infrastructure. S effort. But lower leverage than Step 9K.
**Category:** operational
