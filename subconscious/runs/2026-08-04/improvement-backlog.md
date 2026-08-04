# Improvement Backlog — Run 101 (2026-08-04)

## Active Winner (in queue)

| Idea | Category | Effort | Status | Carry-Forward |
|------|----------|--------|--------|---------------|
| Step 9G: KB autopopulate self-healing trigger | operational | XS | Waiting for nightly SKILL.md-edit channel | 1st cycle |

---

## Parking Lot — Ranked by Impact

### 1. Security Audit Request — Capabilities Phases 1-5
**Category:** security / code_health  
**Effort:** XS (file GH issue)  
**Labels:** `security`, `human-action-required`, `audit`  
**Why parked:** No concrete bug found; attack surfaces are structural properties. Belongs in human-action-required queue, not ai-ready.  
**Specific risks:**
- SSRF via `connector_registry.py` (tenant-supplied OAuth URLs — no allowlist confirmed)
- Gmail OAuth scope creep (does it request read-all vs least-privilege?)
- TCPA compliance in `prospecting.py` (opt-out handling for externally-emailed contacts)
- Social media token lifetime and rotation (no expiry mechanism confirmed)
- `INTEGRATIONS_ENC_KEY` gap (GH #536, HIGH, 14 days open) — capabilities phases 1-5 store OAuth tokens in DB without this key
**Promote condition:** Run this as bonus action in run 102 if no higher-priority winner.

### 2. INTEGRATIONS_ENC_KEY (GH #536) — Security Gap Escalation
**Category:** security / operational  
**Effort:** XS (GH comment reframe)  
**Why parked:** Confidence on specific claim ("tokens stored unencrypted") is 65-70%, below 80% threshold. Comment-posting pattern hasn't moved the needle on similar issues. Security concern captured in item 1 above.  
**Promote condition:** Read `connector_registry.py` to confirm fallback behavior — if unencrypted storage confirmed, escalate to direct comment on GH #536.

### 3. GH #399 Economic Escalation (AUTOPILOT_GH_TOKEN)
**Category:** operational  
**Effort:** XS (GH comment)  
**Why parked:** Day 26+ open, 30 ai-ready issues stalled. Comment fatigue documented. New framing: capabilities phases 1-5 will generate additional ai-ready issues, compounding the backlog further.  
**Promote condition:** Post economic escalation comment (26d × 30 issues × 2h/issue = 60 engineering-hours queued; 5-min Railway fix) as bonus action at any run.

### 4. Capabilities Phases 1-5 Test Coverage Report
**Category:** code_health  
**Effort:** XS (grep + count + conditional GH issue)  
**Why parked:** 156 tests passing aggregate but coverage distribution unknown for 5 new high-risk routers.  
**Investigation path:** `python3 -m pytest backend/tests/ --co -q 2>/dev/null | grep -E "gmail|escalat|prospect|social|connector" | wc -l`  
**Promote condition:** If count < 10 per new router, file GH issue with ai-ready label.

---

## Long-Tail Parking Lot (retained from prior runs)

| Item | Source Run | Status | Promote Condition |
|------|-----------|--------|-------------------|
| Referral Reward activation (GH #413, REFERRAL_REWARD_ENABLED=1) | Run 89-93 | pending_human_action | Human sets env var in Railway |
| Keys Koffee business hours (GH #415) | Run 92 | pending_human_action | Human contacts tenant |
| Lead Source Analytics (GH issue filed, ai-ready) | Run 85 | pending_autonomous | GH #399 resolved → issue-to-pr-loop picks it up |
| email_sequences.py god-class split | Run 35 | parked | GH #399 resolved → ai-ready |
| LoopHealthPage.jsx | Run 100 | parked | Agent OS >5 active tenants (currently ~3) |
| MCP quickstart doc | Run 100 | parked | Second MCP tenant activated (currently 1) |
| conversation_enrichment_job.py scheduling | Run 98 | parked | GH #399 resolved |
| kb_hybrid enable | Run 98 | parked | Settings UI or GH #399 |

---

## Rejected Paths (do not propose)

| Idea | Kill Reason | Run |
|------|-------------|-----|
| ai_human_handoff (frozen) | Frozen by governance — do not propose | Runs 4-38 |
| MCP Step 9H monitoring | 1 tenant only, premature observability | Run 100 |
| os_opportunities referral_activation | Mechanism mismatch (env-var check in DB-query service) | Run 96 |

---

## Carry-Forward Protocol Reminder
- 1st carry-forward: recommend again (run 101 — THIS RUN)
- 2nd carry-forward: recommend again with stronger framing (run 102)
- 3rd carry-forward: direct implementation by subconscious (run 103 if still absent)
