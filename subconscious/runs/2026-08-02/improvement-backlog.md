# Improvement Backlog — 2026-08-02 (Run 101)

## Active
- **Step 9G: KB Autopopulate Self-Heal** — Add bash block to nightly SKILL.md: when KB stale >7 days, trigger kb-autopopulate.yml, check result, comment diagnostic on GH #403 if failed. Proven channel, 1st carry-forward. [AUTONOMOUS-EXECUTABLE, XS, HIGH confidence]

## Parking Lot (survived debate but not chosen)
- **Step 9H: Paying Tenant Conversation Heartbeat** — Per bug-patterns.md (2026-07-23): paying tenant widget down 5 weeks unnoticed. Step 9H would check for paying tenants with 0 conversations/7d and alert. BLOCKED: Supabase unavailable in headless nightly sessions. Correct path: file GH issue with implementation spec for human to add monitoring in Railway/Supabase dashboard. File as bonus action next run if Step 9G wins.
- **capabilities Phase 1-5 integration test audit** — PR #619 (62 files, 13,916 insertions). New external integrations (Gmail OAuth, social APIs, Twilio SMS agent, prospecting). Tests shipped with PR (2400+ lines). Consider selective smoke test audit if any integration surfaces fail in production.
- **GH #399 AUTOPILOT_GH_TOKEN** — 29 days open, loop stalled. Multiple escalation comments already posted. Condition unchanged. Recommend posting day-count update if >35 days without action.
- **Lead Source Analytics Dashboard (run 85 winner)** — GH issue filed with ai-ready label. Pending issue-to-pr-loop once GH #399 resolved.
- **conversation_enrichment_job.py scheduling** — Pending GH #399 resolution.
- **kb_hybrid_retrieval enable** — Needs settings UI or GH #399 first.

## Rejected This Run
- **GH #536 INTEGRATIONS_ENC_KEY as winner** — Demoted to bonus action (1 targeted comment linking PR #619 Gmail dependency to migration 176 block). Not strategic enough for winner slot.
- **GH #399 escalation as winner** — Multiple prior comments already posted; day-count update has diminishing returns without new information.

## Questions for Next Run (Run 102)
1. Did Step 9G get implemented by nightly-2026-08-03? (grep 'Step 9G' SKILL.md — should return >0)
2. If Step 9G present: did it fire? Check nightly log for "Step 9G:" line.
3. Did the `gh workflow run` succeed? Was kb-autopopulate.yml triggered successfully?
4. GH #536: did the targeted PR #619 comment prompt human to provision INTEGRATIONS_ENC_KEY?
5. Any Gmail OAuth failures surfacing for tenants (500 errors on `/auth/gmail/callback`)?
6. GH #399 resolved? (30+ days open — AUTOPILOT_GH_TOKEN rotation).
7. PR #619 capabilities: any production errors on new surfaces (escalations, prospecting, SMS agent)?

## Bonus Action This Run
- Comment on GH #536 linking PR #619 Gmail connector dependency to migration 176 block, with exact Railway variable name and `secrets.token_hex(32)` generation command.
