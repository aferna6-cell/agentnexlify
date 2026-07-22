# Morning Digest — 2026-07-22

Generated: 2026-07-22 UTC | 21 commits last 24h

---

## Commits (last 24h)

- `9c02bb6` docs(nightly): clarify auth_billing.py diff attribution in 2026-07-22 review
- `7f598ff` docs(nightly): review 2026-07-22 [auto-nightly]
- `9166b64` feat: web research sources + upgrade funnel + voice-workforce bridge + routing metrics + fast-path digest + architecture audit (#557)
- `b8066ad` docs(ops): backlog unblock runbook — owner action checklist [skip ci]
- `6dc3419` feat(zapier): Zapier CLI app — new_lead polling trigger + API-key auth (#61) [skip ci]
- `d50d1e8` docs(zapier): KB article + 3 CRM guides + runbook + marketing copy (#62) [skip ci]
- `af2d9d3` feat: one-click email approvals + stage-2 plan gate + suite chips + step timeline approvals + legacy token baselines + fast-path metrics (#553)
- `14ebe8e` docs(drive-kb): KB article + ADR + failures runbook (#54) [skip ci]
- `70e3c82` feat(ops-automation): pending_automations retry drainer + table (#118) [skip ci]
- `9d3cfa2` feat(drive-kb): disconnect confirm + read-only KB when Drive sync active (#52) [skip ci]
- `d6897df` feat(drive-kb): optional "Connect Google Drive" onboarding step (#53) [skip ci]
- `79e8398` feat(zapier): Settings → Integrations → Zapier page — key management + CRM cards (#60) [skip ci]
- `c8abe98` feat(photo-quote): pilot telemetry — feedback + error-rate + conversion (#44) [skip ci]
- `5202f82` feat(photo-quote): widget upload UI + quote render + 3-fork handoff (#41) [skip ci]
- `55352b3` feat: research card + 402 upsell + chat-originated projects + research-to-project + marketing gate fix (#545)
- `aa040fc` fix: planner response schema needs additionalProperties false (#544)
- `b41d460` feat: suite plan gate + chat BI fast path + research v1 + approval rollup + runner-planned projects (#543)
- `a20e8fe` feat: workforce weekly digest + ask-data v2 + starter recurring tasks (#542)
- `0deab50` fix: re-export purge_photo_quote_images_30d so automation loop can start (#541)
- `39b7f72` feat: OS Projects + memory write-back + MCP context tools + workforce dashboard + loop supervisor (#540)
- `24b1777` feat: autonomous-workforce batch — scheduled tasks, ask-data, MCP awareness, customer memory, auto-evals, projects spec (#539)

---

## Issues Opened / Updated (last 24h)

| # | Title | State | Note |
|---|-------|-------|------|
| #558 | fix: require_agent_os_access missing from 10 os_* routers (H1 architecture audit) | OPEN | NEW — ai-ready, backend, security |
| #413 | ACTION REQUIRED: Activate referral reward — REFERRAL_REWARD_ENABLED=1 | CLOSED | Closed today — verify if env-var was actually set in Railway |
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions secrets | OPEN | KB stale 9 days — Step 9F comment added by nightly |
| #399 | autopilot-issue-loop GitHub Actions failing — AUTOPILOT_GH_TOKEN expired | OPEN | Day 19+ — 30+ ai-ready issues stalled |
| #538 | Morning digest 2026-07-21 | OPEN | Yesterday's digest issue |

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #559 | subconscious: run 100 — Fix Agent OS plan gate coverage gap (H1) | <1 day | REVIEW — HIGH severity revenue fix |
| #537 | subconscious: Wire MCP client + Fix Step 9F execution gap | 1 day | Conflicts with #559 — reconcile before merge |
| #521 | feat(ops-automation): pending_automations retry worker (#118) | 1 day | Blocked by #517 — merge migration first |
| #517 | feat(ops-automation): migration 180 — pending_automations + activity_feed_events | 1 day | Review + apply migration via Supabase |
| #509 | docs: update current-tasks with subconscious run 99 status | 2 days | Merge or close |
| #490 | chore(deps): bump actions/setup-python 5→7 | 2 days | Merge if CI green |
| #489 | chore(deps): bump actions/cache 4→6 | 2 days | Merge if CI green |
| #488 | chore(deps): bump actions/setup-node 4→7 | 2 days | Merge if CI green |
| #487 | chore(deps): bump actions/github-script 7→9 | 2 days | Merge if CI green |
| #13 | chore(deps): bump peter-evans/create-pull-request 6→8 | ~100 days | Stale — merge or close |

---

## Nightly Review 2026-07-22 Summary

- 18 commits reviewed — all MEDIUM/LOW risk
- 0 autonomous fixes (LOC guardrail >50 LOC tripped)
- Widget byte-identical: PASS
- `from __future__ import annotations` in FastAPI: PASS
- `client_id` discipline on leads/conversations: PASS
- SSRF check on os_web_sources.py: PASS (is_safe_url, 1-hop cap, 1.5MB response cap)

---

## Subconscious Recommendation (Run 100 — 2026-07-22)

**Agent OS plan gate gap** — 10 `os_*` routers in `main.py` missing `require_agent_os_access` dependency. `chatbot`-plan tenants ($19.99/mo) get silent 200 responses on `agent_os`-only ($99.99/mo) endpoints. Revenue leak + tier integrity breach. PR #559 staged, issue #558 open.

Run 99 mandate check results:
- Step 9F in SKILL.md: PASS (written by run 99)
- KB stale: 9 days (FAIL — stale comment added to #403)
- #399 AUTOPILOT_GH_TOKEN: OPEN Day 19+
- #413 REFERRAL_REWARD: CLOSED today (verify activation in Railway)

---

## Multi-Day Blockers (human-action-required)

| Issue | Days Open | Impact | Fix Time |
|-------|-----------|--------|----------|
| #399 AUTOPILOT_GH_TOKEN expired | 19+ | 30+ ai-ready issues stalled, no autonomous PRs | ~5 min |
| #403 ANTHROPIC_API_KEY not in GH Actions | 13+ | KB stale 9 days, autopilot classifier dead | ~2 min |
| #558 10 os_* routers ungated | NEW | Revenue leak — chatbot-plan gets agent_os data free | Review #559 |

---

## Top 3 Priorities Today

### 1. Review + merge PR #559 — Agent OS plan gate (H1, revenue)
- 10 routers return 200 to chatbot-plan tenants who should get 402
- PR is ready — `require_agent_os_access` additions + 10 gating tests
- Merge sequence: review #559 → verify tests pass → merge → confirm 402 on chatbot client

### 2. Rotate AUTOPILOT_GH_TOKEN (#399) + set ANTHROPIC_API_KEY (#403)
- Both are 2-5 min Railway/GitHub tasks
- Unblocks: 30+ queued ai-ready issues, KB autopopulate, autopilot loop
- Do in one session: GH Settings → PAT rotation → Actions secrets update

### 3. Verify #413 closure — did REFERRAL_REWARD_ENABLED=1 actually get set?
- Issue closed today but env-var activation requires Railway dashboard action
- Check: Railway → backend service → Variables → confirm REFERRAL_REWARD_ENABLED=1
- If not set: 7 real leads are potential referrers getting no referral prompt

---

## KB Status

- Last successful run: **2026-07-13 (9 days — STALE)**
- Threshold: 7 days
- Root cause: ANTHROPIC_API_KEY missing in GH Actions (#403)
- Fix: set the secret → triggers next 6am/6pm cron automatically
