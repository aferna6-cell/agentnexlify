# Run 103 Ideas — 2026-08-03

## Evidence Inputs This Run
- Git log: 227526a (nightly clean, 2026-08-03), a98ea21 (auto-log bug fix), 4ed5ad3 (connector_awareness.py client_id bug fixed by nightly)
- PR #619 (b67710c): capabilities phases 1-5 — 50+ files, 8000+ test lines (inbox monitoring, SMS agent, social publish+images, prospecting, in-chat connectors)
- PR #622 (c5a5a62, 2026-08-01): PWA installability + escalation push
- knowledge-base/log.md: last entry 2026-07-23 — 11 days stale as of 2026-08-03
- docs/dev-knowledge/bug-patterns.md: connector_awareness.py used `.eq("tenant_id", client_id)` on tenant_api_keys (should be client_id invariant) — fixed 4ed5ad3
- docs/skill-discovery/2026-07-20.md: 3 unimplemented skills proposed (notification-layer-add, digest-job-add, agent-os-extension)
- governance.json run_101_mandate: Step 9G absent, KB stale, Agent OS 2-3 tenants
- Step 9G ABSENT from .claude/skills/nightly-commit-review/SKILL.md (grep 'Step 9G' returns 0)

---

## Idea 1: Step 9G — KB Autopopulate Self-Healing Trigger (Carry-Forward, 2nd Cycle)
**Category:** operational
**Effort:** XS (~30 bash lines)
**Confidence:** HIGH
**Autonomous-executable:** true (SKILL.md bash block, same class as Steps 9B-9F)

**Evidence:**
- Step 9G ABSENT from SKILL.md — 2nd-cycle carry-forward fires (run 100 winner, run 101 mandate item 1)
- KB 11 days stale (last: 2026-07-23, threshold: 7 days)
- Step 9F fires correctly (nightly-2026-07-22: "Step 9F: KB STALE (9 days) — comment added to GH #403") but alerts only — no repair
- 63-day stale gap in early 2026 caused by empty secrets with `continue-on-error: true` — silent failure class
- Step 9G catches exactly this: `gh workflow run` + status check + targeted diagnostic if secrets fail
- Previous Steps 9B-9F all proven autonomous channel; same mechanism

**Implementation sketch:**
After Step 9F block in SKILL.md, add `## Step 9G` bash block:
1. Condition: `DAYS_STALE -gt 7` (reuses Step 9F variable)
2. `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
3. `sleep 30`
4. `gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url` → parse conclusion
5. success → log "Step 9G: kb-autopopulate triggered — SUCCESS"
6. failure/cancelled → comment on GH #403: "Step 9G: kb-autopopulate.yml triggered but FAILED. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets. Run URL: $RUN_URL"
7. empty/in-progress → log "Step 9G: kb-autopopulate running — status check pending"

---

## Idea 2: Create agent-os-extension Skill
**Category:** workflow
**Effort:** S (~90 lines SKILL.md)
**Confidence:** HIGH
**Autonomous-executable:** true (new SKILL.md file)

**Evidence:**
- skill-discovery/2026-07-20.md: 9 PRs in 7 days involving Agent OS pattern (PRs #446-#462)
- Frequency: 2-3x/week when building Agent OS features
- 5-layer structure identified: service + router + test + frontend + wire-in
- 15-25 min saved per occurrence (pre-validated pattern reduces error rate)
- PR #619 capabilities sprint (50+ files) would have benefited from this

**Implementation sketch:**
`.claude/skills/agent-os-extension/SKILL.md` covering:
- Standard 5-layer pattern (service → router → Pydantic model → test → frontend page)
- client_id invariant enforcement
- managed_agents_registry.py wire-in checklist
- test coverage gates (80%+ per module)

---

## Idea 3: Create notification-layer-add Skill
**Category:** workflow
**Effort:** S (~60 lines SKILL.md)
**Confidence:** HIGH
**Autonomous-executable:** true (new SKILL.md file)

**Evidence:**
- skill-discovery/2026-07-20.md: 6 occurrences in 3 days
- 4 invariants identified: dedup, demo-safe, best-effort, field-gated
- notify_common.py extracted in nightly-2026-07-17 (skeleton now consistent)
- 25-40 min saved per occurrence, 2-3x/month frequency

**Implementation sketch:**
`.claude/skills/notification-layer-add/SKILL.md` covering:
- notify_common.py hook points (safe_send_email, safe_send_sms, dispatch_owner_alert)
- IdempotencyGuard usage pattern
- demo/sandbox tenant exclusion pattern
- field-gated permission check pattern

---

## Idea 4: client_id Audit of New Capabilities Layer (PR #619)
**Category:** code_health
**Effort:** S (read-only audit + potential 1-2 file patches)
**Confidence:** MEDIUM-HIGH
**Autonomous-executable:** true (audit pass via grep + potential nightly patch)

**Evidence:**
- 4ed5ad3 (2026-08-02): connector_awareness.py used `.eq("tenant_id", client_id)` on tenant_api_keys — caught by nightly, fixed
- PR #619 (b67710c): 50+ new/modified files in capabilities layer — high surface area
- CLAUDE.md Critical Rule #1: `client_id` not `tenant_id` on leads/conversations "3+ production bugs from this"
- New capability files (inbox monitoring, SMS agent, prospecting) all query Supabase tables
- Bug class repeats: 4ed5ad3 proves capabilities layer is susceptible

**Implementation sketch:**
1. `grep -rn "tenant_id" backend/services/capabilities/` to find all candidate violations
2. Cross-reference against table schemas that use `client_id`
3. File nightly-patchable fixes or GH issues per violation

---

## Idea 5: Create digest-job-add Skill
**Category:** workflow
**Effort:** S (~80 lines SKILL.md)
**Confidence:** MEDIUM-HIGH
**Autonomous-executable:** true (new SKILL.md file)

**Evidence:**
- skill-discovery/2026-07-20.md: 1 occurrence + 2 immediate bug classes identified
- Bug classes: blind-state guard + permissions:issues:write
- 45-75 min saved per occurrence
- Scheduled jobs are a recurring pattern (conversation_enrichment_job.py, appointment_jobs.py, loop_health_scan.py)

**Implementation sketch:**
`.claude/skills/digest-job-add/SKILL.md` covering:
- Scheduled job pattern (APScheduler/cron, async-safe)
- blind-state guard (check if previous run still active)
- permissions:issues:write for GH issue filing from jobs
- Supabase service-role client pattern for cross-tenant queries
