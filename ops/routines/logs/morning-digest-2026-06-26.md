# Morning Digest — 2026-06-26

Generated: 2026-06-26 UTC | Caveman mode.

---

## CRITICAL: Invariants STILL broken (3rd day)

`check_project_invariants.py` exits 1. Pre-commit Check 13 BLOCKING ALL COMMITS.

- FAIL: widget drift — `widget/agentnexlify-widget.js` != `landing-page-v2/widget/agentnexlify-widget.js`
- FAIL: em-dashes in 4 JSX files — 10 locations:
  - `frontend/src/components/billing/ReferralCard.jsx:6`
  - `frontend/src/pages/SignupPage.jsx:40, 151`
  - `frontend/src/pages/AdminFunnelPage.jsx:15, 49, 87, 122, 267, 315, 440`

Subconscious ran 3 autonomous attempts (runs 65/66/67). All blocked by nightly scope limits.
Run 67 mandate: **go direct, human executes in interactive session now.**

Fix is < 5 minutes:
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
# then replace em-dashes with hyphens in 4 files above
python3 scripts/check_project_invariants.py
git add -A && git commit -m "fix: widget drift + em-dash violations (run 65/66/67 delivery)"
```

---

## Commits — Last 24h (12)

All council-driven (SMB onboarding/integration strategy):

- `bcdafc2` Fix #3 (council): no-website onboarding KB fallback
- `6a66c12` Fix #2 + #9 (council): ops runbooks for text-back 10DLC + onboarding
- `dcd6532` Fix #7 (council): propose-only + recoverable record changes
- `5b9ead8` Fix #8 (council): sell outcomes, stop counting agents
- `13416b9` Fix #6 (council): surface lapsed integrations to the owner
- `baf7a30` Fix #4 (council): lead score → glanceable temperature badge
- `ce4df1e` docs(brain): mark register #5 DONE (label fix)
- `f6674da` Fix #5 (council): per-recipient text-back frequency cap
- `9ddfd0e` Fix #1 (council): SMS opt-out suppression on every outbound path (TCPA)
- `c39abce` docs(brain): council fixes issue register
- `5f3cc47` docs(brain): LLM Council — SMB onboarding/integration strategy
- `0c63061` subconscious: run 2026-06-25-pm (67) — mandate fires, escalate to interactive human execution

Signal: active LLM Council session shipped 9 product fixes across TCPA compliance, lead scoring, text-back frequency, integration surfaces, and onboarding fallbacks. Strong output day.

---

## Open PRs Needing Action (10)

| # | Title | Age | Action |
|---|-------|-----|--------|
| #372 | Referral reward: $20 credit on first paid invoice | 3d | Apply migration 160 → merge |
| #341 | KB drift sweep 2026-06-22 | 4d | Ready to merge |
| #328 | Billing: save-offer before cancel | 8d | Needs review |
| #327 | AI Workforce: upgrade prompt on 402 | 8d | 16 tests pass — merge? |
| #325 | Checkout: kill Stripe Link + fix redirect | 9d | 30 tests pass — merge? |
| #286 | Agent OS alerts + support form email | 11d | Set Railway env vars first |
| #284 | python-jose ≥3.5.0 (CVE fix) | 11d | Auto-merge candidate |
| #283 | uvicorn bump 0.34.0→0.49.0 | 11d | Auto-merge candidate |
| #282 | stripe req update | 11d | Auto-merge candidate |
| #281 | vitest bump 4.1.8→4.1.9 | 11d | Auto-merge candidate |

---

## Issues

- **#373** BUG: Duplicate migration 158 — step-0 funnel events + demo_referral actions may be unapplied to prod. Apply via Supabase MCP.

---

## Subconscious

- **Run 67** (2026-06-25-pm): Execute Run 65 Steps + Step 9B in Interactive Session — REQUIRES HUMAN (mandate fires; 3rd escalation)
- **Run 66** (2026-06-25): Add Step 9B to nightly-commit-review SKILL.md — pending_approval (auto=true but nightly scope blocked)
- **Run 65** (2026-06-24-pm): Fix Widget Drift + Em-Dash — pending_approval (auto=true, 3rd cycle undelivered)

All three converge on the same fix. One human interactive session clears all three.

---

## Top 3 Priorities

1. **FIX INVARIANTS** — 5-min fix above; unblocks all commits + clears 3 subconscious backlog items
2. **Apply migration 158 to prod** (#373) — funnel events silently broken until applied
3. **Clear dep PR queue** — merge #281/282/283/284 (all auto-merge candidates, no conflicts expected)
