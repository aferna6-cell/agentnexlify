# Improvement Backlog — Run 86 (2026-07-10)

## Winner (AUTONOMOUS-EXECUTABLE)
- **Step 9E credential rotation tracking** — create `ops/credential-rotation-schedule.md` + add Step 9E block to nightly SKILL.md. Embedded content in winning-concept.md. 2nd-miss escalation.

---

## Parking Lot

### Bonus A — Lead Source Analytics Dashboard (run 87 primary if Step 9E confirmed)
- **Why deferred:** run_86_mandate condition unmet. Step 9E must be confirmed implemented before Lead Source Analytics promotes. Mandate condition: Steps 9E + credential-rotation-schedule.md both confirmed by nightly-2026-07-11.
- **When:** run 87, if mandate items confirmed
- **Action:** Create GH issue `feat(analytics): add lead source breakdown chart to analytics page` with `ai-ready` label. Full implementation body in `subconscious/runs/2026-07-09-pm/winning-concept.md`.
- **Effort:** L (issue creation XS; implementation L via issue-to-pr-loop)
- **Source:** run 85 winner, 83-run parking lot

### Bonus B — Warm Lead Recovery (run 87 secondary, conditional)
- **Why deferred:** run_86_mandate secondary condition: "revisit warm lead recovery if mandate items confirmed." Mandate items NOT confirmed this run.
- **When:** run 87 if both mandate items confirmed AND Lead Source Analytics already queued
- **Action:** Query leads table for Sunset Mobile Detailing + Niko's Consulting. Draft one-shot re-engagement email via Resend. Use existing `activation_nudges.py` batch pattern.
- **Effort:** S

### Bonus C — Landing-page-v2 Widget Policy (GH #408)
- **Why deferred:** GH #408 MEDIUM (widget policy ambiguity). Human decision required. Not autonomous-executable.
- **When:** interactive session when human available
- **Action:** Update CLAUDE.md to explicitly state whether `landing-page-v2/widget/` is in byte-identical sync scope (add to check_project_invariants.py) or permanently excluded (add pre-commit exception + close #408).
- **Effort:** XS

### Bonus D — Referral Reward Human Gate (GH #407)
- **Why deferred:** GH #407 HIGH — referral reward (`REFERRAL_REWARD_ENABLED=1`) needs 4-step human gate: migration 162 audit + staging test + production smoke + Stripe verification. Human-required.
- **When:** interactive session, human priority
- **Action:** Follow exact 4-step gate in GH #407 before setting `REFERRAL_REWARD_ENABLED=1` in Railway.
- **Effort:** S (human-only)

---

## Killed This Run

| Idea | Why killed |
|------|-----------|
| governance.json pending_autonomous scan (Idea 3) | Root cause is content format, not mechanism gap. Embedded content pattern is proven (9B/9C/9D). Meta-fix adds complexity vs zero benefit over proven fix. Anti-precedent: moratorium loop (runs 18-24). |

---

## Carry-Forward (Recurring Parking Lot)

- Plan-Name Guard Check 7 (XS, AUTONOMOUS-EXECUTABLE) — consistently deferred, no urgency
- email_sequences.py split (M-effort, no imminent edit trigger)
- Booking flow diagnosis on real tenants (booking_enabled status on MTOptions + 914 Exterior)
- INGESTION-LOG.md in Phase 2 evidence (Step 9C + 9D cover gap; diminishing returns)

---

## Governance State After Run 86

- `total_runs`: 86
- `moratorium_active`: false (pending_approval count = 1, max = 2)
- `pending_autonomous`: Step 9E (run 84 original → run 86 escalation, embedded content)
- `pending_approval`: Lead Source Analytics Dashboard (run 85 winner)
- `pending_human`: Brain connector credentials (run 79 winner, GH #394 still open)
