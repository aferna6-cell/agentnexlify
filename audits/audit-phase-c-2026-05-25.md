# Phase C Pre-Merge Audit — 2026-05-25

**Branch:** `claude/agent-os-grill-resume-cHznV`
**Source plan:** `plans/agent-os-p0_plan.md` §"Phase C — Pre-Merge Cleanup & Refactoring"
**Status:** AUDIT ONLY. **No deletions in this commit.**

Per plan operating rule (`plans/agent-os-p0_plan.md:131-132`):
> Audit produces a report; deletion is a separate step. No file is removed
> until its candidate row is confirmed.

This file IS the report. Deletions land in 4 separate commits (one per category)
in a separate session, per plan operating rule (`plans/agent-os-p0_plan.md:127`):
> Separate session from the build. Per `improve-architecture.md`: do not audit
> and fix in the same session.

---

## C1 — Skills audit (`.claude/skills/`, 83 skills present)

**Method:** `grep -rl "skills/<name>\|\"<name>\"" .claude/commands .claude/hooks .claude/agents CLAUDE.md`
for each candidate. Zero hits = orphan candidate.

### Confirmed orphans (zero refs)

| Skill | Refs | Verdict | Rationale |
|---|---|---|---|
| `kevin-mode` | 0 | REMOVE | Joke persona. Not workflow. |
| `nodejs-backend-patterns` | 0 | REMOVE | Off-stack (FastAPI/Python, not Node). |
| `nodejs-best-practices` | 0 | REMOVE | Off-stack. |
| `obsidian-sync` | 0 | REMOVE | Not Claude workflow. |
| `buddy` | 0 | REMOVE | Purpose unclear, zero refs. |
| `kairos` | 0 | REMOVE | Purpose unclear, zero refs. |
| `subconscious` | 0 | REMOVE | Purpose unclear, zero refs. |
| `last30days` | 0 | REMOVE | Purpose unclear, zero refs. |
| `coordinator` | 0 | UNCERTAIN | Possible alt to compound-engineering. Confirm intent before removing. |
| `team-orchestration` | 0 | UNCERTAIN | Possible alt to compound-engineering. |
| `plan-review-fanout` | 0 | UNCERTAIN | Possible alt to parallel-approaches. |
| `ddup` | 0 | UNCERTAIN | Unknown acronym. |
| `skillify` | 0 | UNCERTAIN | Possible alt to skill-creator. |
| `wiki` | 0 | UNCERTAIN | Possible alt to kb-* skills. |
| `source-validation` | 0 | UNCERTAIN | Possibly used by kb-compile flow. |
| `strategic-compact` | 0 | UNCERTAIN | Possibly relevant to context budget. |
| `challenge-assumptions` | 0 | UNCERTAIN | Possible alt to grill-me. |
| `premortem` | 0 | UNCERTAIN | Possible decision-support skill. |

### Refs ≠ 0 — keep

| Skill | Refs | Verdict | Rationale |
|---|---|---|---|
| `go` | 1 (`.claude/commands/go.md:25`) | KEEP | Live command points at it. |
| `autopilot-loop` | 1 (`CLAUDE.md` "kept for reference") | KEEP-FOR-NOW | CLAUDE.md explicitly retains as reference; remove later if `issue-to-pr-loop` proven stable. |

### C1 deliverable for deletion session
- 8 confirmed REMOVE → one `git rm -rf .claude/skills/<name>` commit
- 10 UNCERTAIN → require human verdict before action
- Update `CLAUDE.md` skill count from "57 agents… + 83 skills" → new count post-removal

---

## C2 — Stale `.md` files

### Root candidates

| File | Verdict | Rationale |
|---|---|---|
| `GEMINI.md` | REMOVE | Gemini config; not Claude workflow. |
| `AUDIT_RESULTS.md` | REMOVE | One-time dated report; superseded by `audits/audit-architecture-*`. |
| `CLEANUP_REPORT.md` | REMOVE | One-time dated report. |
| `CODEBASE-AUDIT-2026-03-25.md` | REMOVE | Dated audit; superseded by `audits/audit-architecture-2026-04-29.md` + later. |
| `DEBUGGING_SESSION_REPORT.md` | REMOVE | Session log; superseded by `docs/dev-knowledge/bug-patterns.md`. |
| `FULL_AUDIT.md` | REMOVE | One-time dated; superseded by `audits/`. |
| `PRE_LAUNCH_AUDIT.md` | REMOVE | One-time dated; pre-launch milestone passed. |
| `CLAUDE.md` | KEEP | Source of truth. |
| `AGENTS.md` | KEEP | Source of truth. |
| `README.md` | KEEP | Repo root. |
| `STRUCTURE.md` | KEEP | Directory map. |
| `CHANGELOG.md` | KEEP | Active. |
| `PROMPTLIBRARY.md` | KEEP | Active. |
| `KARPATHY.md` | KEEP | Reference. |
| `design.md` | KEEP | Reference. |

### `docs/` candidates (dated/one-time)

| File | Verdict | Rationale |
|---|---|---|
| `docs/ai-auto-improve-report.md` | UNCERTAIN | Confirm whether ai-auto-improve flow still runs. |
| `docs/IMPLEMENTATION_SUMMARY_2026-04-05.md` | REMOVE | Dated one-time summary. |
| `docs/env-vars-2026-04-26.md` | UNCERTAIN | If live env-var doc → KEEP; if snapshot → REMOVE. |
| `docs/claude-code-audit.md` | UNCERTAIN | Verify against active claude-code config. |
| `docs/CODEBURN.md` | UNCERTAIN | If active cost-tracking doc → KEEP. |
| `docs/CLAUDE_CODE_IMPROVEMENT_PLAN.md` | UNCERTAIN | Plan vs runbook; verify status. |
| `docs/CLAUDE_SKILLS_RESEARCH.md` | UNCERTAIN | Research doc → consider move to `knowledge-base/raw/`. |
| All `docs/dev-knowledge/*` | KEEP | Live runbooks (bug-patterns, schema-log, architecture-decisions). |
| `docs/AGENT_ROUTING.md` | KEEP | Live runbook. |
| `docs/LLM_RUNTIME_OPERATIONS.md` | KEEP | Live runbook. |
| `docs/production-runbook.md` | KEEP | Live runbook. |
| `docs/incident-response-playbook.md` | KEEP | Live runbook. |
| `docs/managed-agents.md` | KEEP | Live reference. |
| `docs/migration-apply-guide.md` | KEEP | Live reference. |
| `docs/scheduled-routines.md` | KEEP | Live reference. |

### `audits/` candidates

22 audit files present. Latest is `audit-architecture-2026-05-02.md`. Earlier
`audit-architecture-2026-04-*.md` series (6 files) superseded by 2026-05-02.

| File | Verdict |
|---|---|
| `audits/audit-architecture-2026-04-16.md` | REMOVE (superseded) |
| `audits/audit-architecture-2026-04-18.md` | REMOVE (superseded) |
| `audits/audit-architecture-2026-04-19.md` | REMOVE (superseded) |
| `audits/audit-architecture-2026-04-25.md` | REMOVE (superseded) |
| `audits/audit-architecture-2026-04-27.md` | REMOVE (superseded) |
| `audits/audit-architecture-2026-04-29.md` | REMOVE (superseded by 2026-05-02) |
| `audits/audit-architecture-2026-05-02.md` | KEEP (latest) |
| `audits/audit-phase-c-2026-05-25.md` | KEEP (this file) |
| All `audit-mtoptions-*` (3 files) | UNCERTAIN — confirm mtoptions feature shipped/dropped |
| All `audit-lead-*` (2 files) | UNCERTAIN — lead-parser-replacement plan removed below |
| `audit-ops-automations-2026-05-01.md` | KEEP (current ops) |
| `audit-onboarding-2026-04-21.md` | UNCERTAIN — onboarding-v2 plan removed below |
| `audit-opus47-prompting-2026-04-27.md` | KEEP (live rule basis) |
| `audit-environment-blockers-2026-04-15.md` | UNCERTAIN |
| `audit-codebase-debug-2026-04-15.md` | UNCERTAIN |
| `audit-health-2026-04-20.md` | REMOVE (one-time health snapshot) |
| `existing-infra-reference-2026-04-21.md` | KEEP (reference) |

---

## C3 — Stale plans (`plans/`)

**Method:** `grep -rln "<plan-name>"` across CLAUDE.md + plans/README.md for live refs.
All 5 candidates returned 0 live refs.

| Plan | Live refs | Verdict | Rationale |
|---|---|---|---|
| `plans/lead-parser-replacement_plan.md` | 0 | REMOVE | Feature shipped; verify via `backend/services/lead_parser*` grep before deletion. |
| `plans/marketing-addon-activation_plan.md` | 0 | REMOVE | Marketing addon shipped; verify via `backend/routers/marketing*`. |
| `plans/onboarding-v2_plan.md` | 0 | REMOVE | Onboarding shipped; verify via `frontend/src/pages/Onboarding*`. |
| `plans/onboarding-v2_issues.md` | 0 | REMOVE | Issues file paired with the plan; closed. |
| `plans/ops-automation-surfacing_plan.md` | 0 | REMOVE | Ops automation shipped. |
| `plans/post-audit-remediation_plan.md` | 0 | REMOVE | Remediation complete or superseded by Phase C itself. |
| `plans/handoff-2026-04-16-post-analytics-split.md` | 0 | REMOVE | Handoff doc, context fully consumed. |
| `plans/handoff-2026-05-22-agent-os-resume.md` | 0 | UNCERTAIN | Recent handoff; may still inform live work. |
| `plans/agent-os-p0_plan.md` | n/a | KEEP | Active (this plan). |
| `plans/agent-os-connectors-inbound_plan.md` | n/a | KEEP | Active (Group A spec). |
| `plans/agent-os-next-steps_plan.md` | n/a | KEEP | Active (post-OS roadmap). |
| `plans/README.md` | n/a | KEEP | Directory README. |

### C3 verification gate before deletion
For each REMOVE row: `grep -rln "<shipped-surface>" backend/ frontend/` to confirm
the plan's deliverable exists. If exists → safe REMOVE. If missing → flip to
UNCERTAIN.

---

## C4 — Dead code from the rehaul

Plan §C4 (`plans/agent-os-p0_plan.md:208-209`):
> This step is **scoped only after P1–P4 land** — the dead set depends on which
> old surfaces the workflow agents replace.

**P1-P4 ARE landed** (`backend/services/os_workers/{customer_question,booking,lead_nurture,campaign}.py`).

### Scoping result

P1-P4 workers run inside the orchestrator as ADDITIVE routing targets. They do
NOT replace any existing dashboard surface. Verified:

```
frontend/src/pages/ConversationsPage.jsx       — still primary (no AgentOS handoff)
frontend/src/pages/LeadsPage.jsx               — still primary
frontend/src/pages/ChatFlowBuilderPage.jsx     — still primary
frontend/src/pages/AutoShopChatbot.jsx         — still primary
frontend/src/pages/DentalChatbot.jsx           — still primary
frontend/src/pages/MedicalOfficeChatbot.jsx    — still primary
frontend/src/pages/RestaurantChatbot.jsx       — still primary
frontend/src/pages/SalonChatbot.jsx            — still primary
frontend/src/pages/LiveChatAlternative.jsx     — still primary
```

**No frontend surface is superseded by Agent OS yet.** `AgentOS.jsx` is an
ADDITIONAL surface (owner chat shell), not a replacement.

**No backend handler is superseded by Agent OS yet.** Existing chat / lead /
appointment routers remain canonical; Agent OS layers on top via `os_*` tables.

### C4 candidates: NONE in this audit cycle

Re-evaluate C4 after a product decision flips an existing surface to "Agent OS
canonical" (e.g. retiring `ConversationsPage` once `AgentOS.jsx` reaches feature
parity). Until then, removing any existing page/router would be a regression,
not cleanup.

### Tooling owed before next C4 run

- Run `dead-code-sweep` skill against `backend/` + `frontend/` for unrelated
  rot (independent of rehaul)
- Run `knip` + `ts-prune` + `depcheck` against `frontend/`
- Run `vulture` against `backend/`
- Cross-check candidates with `gitnexus_impact` for zero live callers

These produce a separate dead-code report — not blocking Phase C closeout.

---

## Phase C done-criteria status (per `plans/agent-os-p0_plan.md:222-229`)

| Criterion | Status |
|---|---|
| C1–C4 candidate tables produced and confirmed | ✅ Tables produced. UNCERTAIN rows need user verdict before deletion commits. |
| Four removal commits (one per category) | ⬜ DEFERRED to separate session per operating rule. |
| No dangling references (`grep` + `check_plan_drift.py` clean) | ⬜ Verified after deletion commits. |
| CLAUDE.md updated: skill count, any removed-file references | ⬜ Updated alongside deletion commits. |
| Branch ready to merge to `main` with no obsolete code | ⬜ After deletion commits + final `npm run build` + `check:quick`. |

## Next session entry brief

To execute deletions:
1. Read this audit.
2. For each UNCERTAIN row in C1/C2/C3 — confirm verdict via `AskUserQuestion`.
3. Execute 4 separate commits (C1 skills / C2 docs / C3 plans / C4 if applicable).
4. Run `grep -rln` after each commit for dangling refs; fix or revert.
5. Run `check:quick` + `npm run build` after each commit.
6. Update `CLAUDE.md` skill/file counts.
7. Update `plans/agent-os-p0_plan.md` to mark Phase C as DONE.
8. PR #177 ready for merge to `main`.

---

## ADDENDUM — Audit invalidation (2026-05-25, post-audit)

When the deletion executor attempted to action C1/C2/C3 confirmed-REMOVE rows, a pre-deletion `grep -rln` sweep found that **every confirmed-REMOVE row has live references** in active code, specs, CI workflows, or other plans. The audit's "0 refs" column is **wrong on a methodological level**.

### Evidence (sampled rows)

| Candidate | Audit said | Actual ref count | Sample ref |
|---|---|---|---|
| `kevin-mode` skill | 0 | 2 (live invocation paths) | `.claude/rules/personality.md:110` + `.claude/rules/caveman-mode.md:33` ("kevin mode" toggle) |
| `last30days` skill | 0 | 5+ | `memory-tiered-retrieval.md:65` + full spec in `specs/claudeopedia_spec.md` + `planning/specs/claudeopedia_spec.md` |
| `obsidian-sync` skill | 0 | 3+ | `claudeopedia_spec.md:702-735` (full active spec) |
| `kairos` skill | 0 | 2+ | `docs/kairos/` directory of live state |
| `subconscious` skill | 0 | 6+ | `subconscious/` directory of live state + governance.json |
| `nodejs-backend-patterns` skill | 0 | mirror at `.agents/skills/nodejs-backend-patterns/` | actual duplicate |
| `GEMINI.md` | confirmed-REMOVE | 6 refs | `.ai/README.md:25` (registry), `.github/workflows/agent-config-security.yml:15,35` (CI watch), `docs/AGENT_SYSTEM_PLAN.md:63` |
| `audit-architecture-2026-04-16.md` | confirmed-REMOVE | 5 refs | cited from later audits + plans |
| `audit-architecture-2026-04-18.md` | confirmed-REMOVE | 7 refs | cited from later audits + plans |
| `audit-health-2026-04-20.md` | confirmed-REMOVE | audited 0 — but plan + other audits self-cite | check before action |
| `lead-parser-replacement_plan.md` | confirmed-REMOVE | 7 refs | `migrations/103_*.sql:4`, `backend/routers/widget_chat.py:1230`, `backend/tests/test_lead_enrichment.py:11` (production code citing the plan in comments) |
| `onboarding-v2_plan.md` | confirmed-REMOVE | 10 refs | morning-digest logs + subconscious governance state + sibling `onboarding-v2_issues.md` |
| `post-audit-remediation_plan.md` | confirmed-REMOVE | 3 refs | active citations from elsewhere |

### Methodology gap

The audit's "0 refs" column appears to have been generated either without `grep -rln` verification or with a too-narrow search scope (excluding subconscious/, docs/, migration comments, CI workflows, registry files).

### Operating-rule conclusion

Per `plans/agent-os-p0_plan.md:131-132`: **"No file is removed until its candidate row is confirmed."**
Per `.claude/rules/fill-instructions-before-guessing.md`: when an instruction (audit) contradicts code reality, **STOP. Fix the instruction first.**

The 30 "confirmed-REMOVE" rows are NOT confirmed. They are UNCERTAIN pending re-audit with corrected `grep -rln` methodology + per-ref triage:

- **Comment-only refs in code** (e.g. `lead-parser-replacement_plan.md` cited from migration comment) → can delete plan after rewriting the comment to cite the spec only.
- **Registry refs** (`.ai/README.md`, `skills-lock.json`) → registry must be updated before/with deletion.
- **CI workflow refs** (`.github/workflows/agent-config-security.yml`) → workflow path-watch list must be updated before deletion.
- **Active spec refs** (`claudeopedia_spec.md` referencing `obsidian-sync` + `last30days`) → must decide spec fate first; deleting skill orphans the spec.
- **Active state-dir refs** (`subconscious/`, `docs/kairos/`) → those skills are not orphans; they're part of live workflows.
- **Toggle-doc refs** (`personality.md`, `caveman-mode.md` referencing `kevin-mode`) → rules must be updated before deletion.

### Updated Phase C done-criteria status

| Criterion | Status |
|---|---|
| C1–C4 candidate tables produced and confirmed | ❌ Confirmation invalidated — audit methodology broken. Re-audit needed. |
| Four removal commits (one per category) | ⬜ BLOCKED on re-audit + per-ref triage + user verdict on UNCERTAIN |
| No dangling references | ✅ Currently zero dangling refs (because nothing deleted yet) |
| CLAUDE.md updated | ⬜ |
| Branch ready to merge to `main` with no obsolete code | ⬜ |

### Re-audit work needed (separate session)

1. For each candidate, run `grep -rln --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=_archive --exclude="audit-phase-c-2026-05-25.md" -e "<basename>" .` and inspect every ref.
2. Classify each ref:
   - **Stale comment in code** → editable, deletion can proceed after rewrite
   - **Registry entry** → registry must be patched in same commit
   - **CI workflow watch path** → workflow patched in same commit
   - **Active spec or state dir** → blocking — candidate is NOT removable
   - **Cycle ref** (another removed file referencing this one) → both go together
3. Reclassify candidate as CONFIRMED-REMOVE only when all refs fall in the "editable" bucket.
4. Issue user-facing verdict via `AskUserQuestion` for all candidates remaining UNCERTAIN.
5. Then execute the 4-commit deletion sequence with reference-patching included in each commit.

### Status — 2026-05-25

Phase C deletions: **BLOCKED on re-audit**. PR #177 Phase C box stays unchecked. The Agent OS P0–P4 build + Group A inbound + tests + e2e loop work IS shipped; Phase C is the only remaining plan section, and it correctly stays as "report produced, deletion deferred to a future re-audited session" per the plan's own operating rule.

---

## RE-AUDIT FINDINGS — 2026-05-25 (in-session, post-invalidation)

Re-audit performed with `grep -rln` per candidate + ref-by-ref triage using 6-bucket classification: stale-comment / registry / CI-workflow / active-spec-or-state-dir / cycle-ref / frozen-historical-log.

### CONFIRMED-REMOVE (only cycle refs + frozen historical refs)

| Candidate | Refs | Required patch |
|---|---|---|
| `AUDIT_RESULTS.md` | plan + audit (cycle) | none |
| `CLEANUP_REPORT.md` | plan + audit (cycle) | none |
| `CODEBASE-AUDIT-2026-03-25.md` | plan + audit (cycle) + `docs/daily-logs/2026-03-25.md` (frozen historical) | none |
| `DEBUGGING_SESSION_REPORT.md` | plan + audit (cycle) | none |
| `FULL_AUDIT.md` | plan + audit (cycle) | none |
| `PRE_LAUNCH_AUDIT.md` | plan + audit (cycle) | none |
| `marketing-addon-activation_plan.md` | plan + audit (cycle) | none |
| `ops-automation-surfacing_plan.md` | plan + audit (cycle) | none |
| `post-audit-remediation_plan.md` | cycle + frozen-historical-log + frozen audit | none |
| `handoff-2026-04-16-post-analytics-split.md` | self-ref + cycle | none |
| `audit-architecture-2026-04-25.md` | cycle ref only | none |
| `audit-architecture-2026-04-19.md` | cycle ref only | none |
| `audit-architecture-2026-04-27.md` | 0 refs (TRUE zero) | none |
| `audit-architecture-2026-04-29.md` | 0 refs (TRUE zero) | none |
| `audit-health-2026-04-20.md` | 0 refs (TRUE zero) | none |
| `audit-architecture-2026-04-16.md` | cycle + frozen historical logs | none |
| `audit-architecture-2026-04-18.md` | cycle + frozen historical brainstorm runs | none |
| `buddy` skill | `.ai/manifest.json` (registry) + frozen historical | patch `.ai/manifest.json` to drop entry |

### BLOCKED (active refs in code, specs, rules, scripts, state dirs)

| Candidate | Blocking ref | Decision |
|---|---|---|
| `kevin-mode` skill | `.claude/rules/personality.md:110` + `.claude/rules/caveman-mode.md:33` actively reference it as a toggle persona | KEEP — toggle is active |
| `nodejs-backend-patterns` skill | `.agents/skills/nodejs-backend-patterns/SKILL.md` is a parallel skill copy | KEEP — mirror is live |
| `nodejs-best-practices` skill | `.agents/skills/nodejs-best-practices/SKILL.md` mirror | KEEP — mirror is live |
| `obsidian-sync` skill | `specs/claudeopedia_spec.md:702-735` documents it as the sync mechanism | KEEP — active spec |
| `kairos` skill | `scripts/kairos/{autodream.py,monitor.py,daemon.sh}` active runtime | KEEP — active scripts |
| `subconscious` skill | `subconscious/runs/*` daily run dirs + state + governance.json | KEEP — active system |
| `last30days` skill | `specs/claudeopedia_spec.md:228-245` full skill section + `memory-tiered-retrieval.md:65` | KEEP — active spec + rule |
| `lead-parser-replacement_plan.md` | `.claude/rules/fill-instructions-before-guessing.md:42` cites it as the teaching example for the rule | KEEP — rule teaching ref |
| `onboarding-v2_plan.md` | `subconscious/state/governance.json:392` active governance log entry | KEEP — active state |
| `onboarding-v2_issues.md` | `scripts/post_onboarding_v2_phase1_issues.sh` active shell script | KEEP — active script |

### UNCERTAIN (need user verdict)

| Candidate | Refs | Question |
|---|---|---|
| `GEMINI.md` | `.ai/README.md:25` (registry row) + `.github/workflows/agent-config-security.yml:15,35` (CI watch path) + `docs/AGENT_SYSTEM_PLAN.md:63` (historical doc listing tool mirrors) | Does AgentNexLiFy still want Gemini CLI compatibility, or remove the file + drop registry/CI watch row + rewrite historical doc? |
| `docs/IMPLEMENTATION_SUMMARY_2026-04-05.md` | cycle + frozen `.openclaw-migration/memory/2026-04-05.md` | REMOVABLE (resolved 2026-05-25) — move to CONFIRMED-REMOVE |

### Plan vs reality — old "confirmed-REMOVE" reduced 30 → 18 truly-removable + 10 BLOCKED + 2 UNCERTAIN

Truly-removable rows = 6 root .md + 2 plans + 1 plan-variant + 7 audits + 1 skill (buddy) = 17 unambiguously-removable files via one patch to `.ai/manifest.json` (for buddy) and one straight `git rm` commit per category.

The 10 BLOCKED rows are NOT half-migration risks because the plan rule §C explicitly says "audit produces a report; deletion is a separate step." Leaving BLOCKED candidates in place is honoring rule §C, not violating it.
