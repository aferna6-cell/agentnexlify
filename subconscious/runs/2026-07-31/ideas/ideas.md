# Ideas — 2026-07-31 (Run 101)

## Evidence Digest

- **KB 8 days stale** (last compile 2026-07-23). Step 9G (run 100 winner) absent from SKILL.md on main. PR #577 open 8 days without merge. Step 9F firing correctly but alert-only.
- **GH Actions CI down Day 11** (#500 — spending limit). Every PR unvalidatable. KB autopopulate can't run. Nightly loops can't fire from Actions. Blocks CI-dependent mechanisms (GH Actions cron for tenant monitoring).
- **Autonomy graph runtime live** since 2026-07-28 (#599). Sweeper shipped (#608, 251 tests). But sweeper is CLI-only — no scheduled invocation. A crash mid-cycle between Routine fires would leave stranded runs until manual sweep.
- **GH #536 open Day 10** — INTEGRATIONS_ENC_KEY not provisioned in Railway. Migration 176 blocked. Listed as HIGH risk in every nightly review cycle but no automated escalation pressure applied.
- **Paying tenant silence** — bug-patterns.md (2026-07-23) names new defect class: Keys Koffee widget missing 5+ weeks undetected. GH #610 filed (2026-07-29), awaiting human Supabase action with no escalation cadence.
- **Quiet code period** — 4 days of ops-log-only commits (2026-07-28 sweeper was last real code). Code quieter than usual; autonomous pipeline is the active surface.
- **Run 101 mandate check**: Step 9G ABSENT, KB stale >7d, Agent OS <5 tenants, MCP at 1 tenant. Items 1-2 FAIL.

---

### Idea 1: Step 9G — KB Autopopulate Self-Healing Trigger (carry-forward, direct implementation)

**Evidence:** Step 9G absent from SKILL.md (grep=0). KB 8 days stale as of 2026-07-31. PR #577 open 8 days without merge. Step 9F fires correct alert to GH #403 but cannot trigger repair. Morning-digest 2026-07-29/30 screamed "merge ASAP" — human hasn't acted. 3 paying tenants depend on KB freshness for AI chat. Steps 9B-9F all implemented in 1 SKILL.md-edit cycle each. `kb-autopopulate.yml` supports `workflow_dispatch`. Run 99's pattern: 3rd-carry-forward → direct implementation. This is the 1st carry-forward from main's perspective (PR #577 opened but never merged).

**Action:** Add Step 9G bash block directly to `.claude/skills/nightly-commit-review/SKILL.md`. Block triggers `gh workflow run kb-autopopulate.yml`, waits 30s, checks run status via `gh run list`, posts targeted diagnostic comment on GH #403 if run fails (signals secrets-empty condition). ~30 bash lines.

**Impact:** KB repair fires on next nightly cycle (tonight). 3 paying tenants get fresh AI answers without human action. Closes 8-day repair gap. Demonstrates full observe→alert→self-heal arc working autonomously.

**Category:** operational  
**Effort:** XS (~30 bash lines, same template as Step 9F)  
**Autonomous-executable:** YES — same channel as Steps 9B-9F, all proven in 1 cycle

---

### Idea 2: Nightly Autonomy Sweeper Invocation (Step 9I candidate)

**Evidence:** `scripts/autonomy/sweeper.py` shipped 2026-07-28 (#608). `run_loop sweep` and `run_loop list` CLIs available. The autonomy Routine fires the graph loop on a schedule, but no automated sweep runs between Routine firings. A crash mid-verify (the exact bug that caused #605) can strand a run in `running` until a human runs `run_loop sweep` manually. Bug-patterns.md doesn't yet have this class because #608 closed it before it compounded — but the root condition (unattended loop) persists.

**Action:** Add a new Step 9I bash block to nightly-commit-review SKILL.md: run `python3 -m scripts.autonomy.run_loop sweep --dry-run` and log the result. If any stranded runs found: run `python3 -m scripts.autonomy.run_loop sweep` (live) and report how many were resolved. ~15 bash lines.

**Impact:** Stranded autonomy runs detected and resolved daily. Prevents the "permanent corpse run" failure mode from accumulating between Routine firings. Graph state stays clean.

**Category:** operational  
**Effort:** XS (~15 bash lines in SKILL.md)  
**Autonomous-executable:** YES — nightly has python3 + scripts.autonomy in scope

---

### Idea 3: INTEGRATIONS_ENC_KEY Escalation Nightly Check (Step 9I candidate)

**Evidence:** GH #536 "provision INTEGRATIONS_ENC_KEY in Railway before applying migration 176" — HIGH risk, open Day 10 (2026-07-21). Listed in every nightly review's open-issues table but no escalation comment is ever posted. Nightly already posts escalation comments on stale issues (Steps 9D/9E/9F patterns). Migration 176 ships an encryption key for a new feature; without it, the migration cannot be safely applied and the feature stays undeployable.

**Action:** Add bash block to nightly SKILL.md: if GH #536 is OPEN and age >7 days → post escalation comment on #536 framing the blocker: "Day N: migration 176 cannot be applied until INTEGRATIONS_ENC_KEY is provisioned in Railway Variables → Deploy. Feature stays locked until this credential is added." One comment per week (check for existing escalation comment before posting).

**Impact:** Daily pressure on #536 instead of passive listing in nightly table. Human is reminded with increasing urgency. Migration 176 unblocks in days instead of weeks.

**Category:** operational  
**Effort:** XS (~20 bash lines in SKILL.md)  
**Autonomous-executable:** YES — gh CLI is available in nightly

---

### Idea 4: GH #610 Staleness Escalation — Nightly Paying Tenant Silence Follow-up

**Evidence:** Bug-patterns.md (2026-07-23): paying tenant silence is a named new defect class. GH #610 "Monitoring: paying tenant silence detection [HUMAN ACTION REQUIRED, revenue]" filed 2026-07-29/30. Morning-digest 2026-07-30 lists it as Top 3 Priority #3. Required action: paste SQL into Supabase Dashboard scheduled jobs (5 min). 0 human comments on #610 as of latest nightly. Daily escalation comments have successfully driven human action on GH #413 referral checklist.

**Action:** Add bash block to nightly SKILL.md: check age of GH #610 and count of human comments. If age >7 days and human comment count = 0 → post escalation comment: "Day N: #610 tenant-silence SQL still not wired. Each day of delay risks another paying tenant going silent undetected. Fix is 5 minutes: Supabase Dashboard → Database → Scheduled jobs → paste SQL from issue body → daily at 9am."

**Impact:** Same escalation pressure that drove 10-item referral checklist to 10/10 completion (runs 89-93). Human action within days of daily pressure.

**Category:** customer_value  
**Effort:** XS (~15 bash lines in SKILL.md)  
**Autonomous-executable:** YES — gh CLI available in nightly

---

### Idea 5: Autonomy ROUTINE.md Post-Cycle Sweep Instruction

**Evidence:** `scripts/autonomy/ROUTINE.md` contains the Routine prompt that fires the graph loop. Prompt ends with "commit what you did" steps but has no self-cleanup instruction. Sweeper (#608) needs to be invoked after each cycle to handle crashes. Without it in the Routine prompt, stranded runs only get resolved if the operator remembers to run `run_loop sweep` manually, or if Idea 2 (nightly SKILL.md step) fires.

**Action:** Edit `scripts/autonomy/ROUTINE.md` — append to the Routine prompt body a post-cycle cleanup step: "After the graph cycle completes (success or failure), run `python3 -m scripts.autonomy.run_loop sweep` to resolve any runs stranded by crashes this cycle. Log the result."

**Impact:** Each Routine firing self-cleans. Stranded runs from the CURRENT cycle are swept before the next cycle starts. Complements Idea 2 (which sweeps from the nightly).

**Category:** operational  
**Effort:** XS (3-5 lines added to ROUTINE.md)  
**Autonomous-executable:** YES — ROUTINE.md edit is a plain text change
