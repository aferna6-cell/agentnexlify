# Improvement Backlog — 2026-07-21 (Run 100)

## Active

- **File GH issue: Migration 176 INTEGRATIONS_ENC_KEY provisioning blocker** — irreversible schema drop blocked until Railway env var set; GCal just shipped; 0 integrations rows = safe window now

## Parking Lot (survived debate but not chosen)

- **Migrations 181+182 peer apply** — conversation memory + KB provenance silently failing; correct mechanism is peer (Codex/Kimi3) applying Fable5-authored migrations via team contract; file team-channel request or GH tag to trigger
- **Photo-quote billing audit** — `photo_quote_usage.py` is solid (idempotency key, client_id, fail-open all correct); park unless metered billing expands or a billing anomaly surfaces
- **Step 9F nightly execution verification** — Step 9F IS in SKILL.md (grep=6) but "Step 9F:" line absent from nightly-2026-07-21.md; KB 8 days stale should have triggered GH #403 comment; verify in run 101

## Rejected This Run

- **Platform_settings integer kill-switch audit** — KILLED: 0 prod rows at risk, no evidence of imminent risk, pre-existing parking lot item with no status change

## Questions for Run 101

1. Was Migration 176 GH issue created (by this run's recommendation or subsequent human action)?
2. Is INTEGRATIONS_ENC_KEY now in Railway, and was migration 176 applied before first GCal OAuth connect?
3. Does nightly-2026-07-22.md contain a "Step 9F:" line, or does GH #403 have a Step 9F comment from 2026-07-21/22?
4. Have GH #399 (expired AUTOPILOT_GH_TOKEN) and GH #413 (REFERRAL_REWARD_ENABLED) moved after now being open 18+ and 10+ days?
5. Did a peer agent (Codex or Kimi3) apply migrations 181+182?
