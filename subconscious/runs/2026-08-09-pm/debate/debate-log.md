# Debate Log — Run 102 (2026-08-09-pm)

Top 3 ideas debated (ranked by impact + governance mandate priority):
1. Step 9H — Idempotent PR Pile Alerter
2. GH #500 Diagnostic Comment
3. Extend client_id sentinel to tenant_api_keys

---

## Idea 1: Step 9H — Idempotent PR Pile Alerter

### Challenge

**Is the evidence strong enough?**
4 open subconscious draft PRs (#606, #611, #613, #626), oldest 12 days. But PRs have always stacked up — why is this different from any prior run?

**Is this the highest-leverage thing right now?**
Human already SEES the PRs in GitHub. They know the pile exists. Adding a comment to GH doesn't fix the underlying cause (human hasn't merged them). A comment on the oldest PR is noise if they're not watching GH issue comments for subconscious PRs.

**What could go wrong?**
"Idempotent" design requires storing last-alert date in nightly log. If nightly log parsing is fragile, the sentinel might not read correctly, and fire every run. Or worse, if alert date check breaks, Step 9H fires daily. The very problem it was designed to solve (firing every nightly) reappears.

**Has something similar been tried and rejected?**
YES. Step 9H was killed in run 100 for a DIFFERENT concept (MCP tenant monitoring). That idea was killed, not this one. The PR pile alerter version was PARKED, not rejected. The parked note said: "current design would fire every nightly indefinitely." That's the idempotency gap being fixed now.

**Is this too similar to the current active direction?**
Current active direction: Steps 9F and 9G (KB staleness, KB self-healing). Step 9H is an orthogonal addition to the same SKILL.md step sequence. Fits the proven channel.

**Challenge verdict summary:** Medium strength objection — human probably SEES the PRs already. The value is systematizing the signal (once-weekly), not creating a net-new signal. Objection on "noise" is partially valid.

### Defend

The governance mandate for run 102 is explicit: "If not merged or closed, re-raise Step 9H with redesigned idempotent alerting." The mandate didn't ask for impact analysis — it asked for the design fix. The pile has grown to 4 PRs across 12 days without merge or close action; the human likely does NOT have a systematic monitoring cadence for PR age (no other alert exists).

Idempotency concern: the design stores last-alert date as a single line in the nightly log. The nightly SKILL.md already writes structured log entries (see Step 9G log format). Reading the last 7 nightly logs for "9H alert" is a grep, not a parse. If the grep fails, the step can default to alerting (safe failure mode = false positive, not daily spam).

"Noise" concern: once-weekly vs never is the choice. Human currently has 0 signal from subconscious about PR age. One comment on the oldest open PR per week is low noise.

Proven channel: 9A–9G all implemented as SKILL.md bash blocks. Same class, same risk surface, same execution path. Confidence on delivery: HIGH.

### Verdict: SURVIVES

Step 9H survives with a design note: idempotency relies on log grep, not parsed state. Failure mode defaults to alert (safe). Governance mandate is explicit. Proven SKILL.md channel makes XS implementation straightforward. Addresses a real gap (0 automated PR-age signal).

---

## Idea 2: GH #500 Diagnostic Comment

### Challenge

**Is the evidence strong enough?**
GH #500 filed 2026-07-27, last updated same day, 0 activity in 13 days. KB stale 17 days. Step 9G queued kb-autopopulate.yml (204 success) on 2026-08-07 but KB is still stale. The causal chain is inferred: GH #500 (billing limit) → hosted-runner failure → workflow silently fails → KB stays stale. This is NOT confirmed. Workflow might have been queued but also silently failed for a different reason (#403 ANTHROPIC_API_KEY).

**Is this the highest-leverage thing right now?**
This is a one-time comment on a single GH issue. Once posted, the diagnostic is there. Human reads it once. Does not create a system or prevent future recurrences. Lower leverage than Step 9H (system) or Idea 3 (sentinel catching future bugs).

**What could go wrong?**
The causal chain is wrong. If GH #500 was already resolved (billing recharged) and the real cause is GH #403, the comment misdirects the human. Could cause them to fix the wrong thing first. Inaccuracy risk is non-trivial since GH #500's actual status is unknown.

**Has something similar been tried and rejected?**
No prior runs proposed GH #500 comments. It's novel. Not rejected.

**Is this too similar to the current active direction?**
GH #403 is the active monitoring target for Step 9G. GH #500 is different (billing limit). This broadens scope slightly but complements existing direction.

### Defend

The evidence chain is strong enough to justify connecting #500 → Step 9G → KB staleness even if causation is unconfirmed. The comment explicitly states "if the billing limit is still active." It's diagnostic, not prescriptive. Human reads it and decides which issue to fix.

However: the comment on #500 is a one-shot action that doesn't prevent recurrence. GH #500 is 13 days stale — there's a real chance the human already knows this connection and hasn't fixed it due to friction (billing settings, not awareness). Adding another comment to a stale issue may have no effect.

### Verdict: WEAKENED

Causal chain is inferred, not confirmed. GH #500's current status is unknown. The comment is a one-shot action with uncertain leverage — high chance the human already knows the connection. Survives debate but ranked below Step 9H (systemic) and Idea 3 (prevents 5th bug recurrence). Parking lot candidate. Could be included as a bonus action in winning concept's implementation sketch.

---

## Idea 3: Extend client_id Sentinel to tenant_api_keys

### Challenge

**Is the evidence strong enough?**
bug-patterns.md explicitly documents the 2026-08-01 connector_awareness.py bug: `.eq("tenant_id", client_id)` on `tenant_api_keys` — 4th occurrence of the bug class. Step 3 in SKILL.md currently only checks `leads` and `conversations`. The uncovered table directly caused the production bug. Evidence: HIGH.

**Is this the highest-leverage thing right now?**
client_id/tenant_id mixup is the most frequent bug class in the codebase (4 occurrences, no other pattern comes close). The next occurrence will almost certainly be on a table NOT yet covered by the sentinel. Extending the sentinel is direct prevention.

**What could go wrong?**
Adding grep targets expands the sentinel's scope. If the grep pattern is wrong (overly broad), it could generate false positives — flagging legitimate `.eq("tenant_id"` calls on tables WHERE tenant_id IS the correct column name. But the `leads` and `conversations` tables use `client_id` by invariant (CLAUDE.md Rule 1). `tenant_api_keys` uses `tenant_id` as its primary foreign key? Need to verify — if `tenant_api_keys.tenant_id` is correct, then `tenant_api_keys.tenant_id` is NOT a bug.

**Wait — is the bug actually about the column name, or the VALUE passed to it?**
Re-reading bug evidence: connector_awareness.py used `.eq("tenant_id", client_id)` on `tenant_api_keys`. The column name IS `tenant_id` on that table. The bug was passing `client_id` (the Python variable) as the value — which contains the wrong identifier (Python variable named client_id doesn't mean the column named client_id). This is subtle: it's not a column-name bug, it's a variable-value confusion. The sentinel needs to catch `client_id` VARIABLE being used where `tenant_id` VARIABLE should be passed — not `tenant_id` column name.

The current Step 3 check is for `.eq("tenant_id"` on leads/conversations where the COLUMN should be `client_id`. On `tenant_api_keys`, the column IS `tenant_id` — correct. The VALUE passed should also be `tenant_id` (the variable). Using `client_id` (the variable) as the value is wrong.

This means the sentinel expansion would need a DIFFERENT grep pattern — not `.eq("tenant_id"` (correct column) but rather `.eq("tenant_id", client_id)` (correct column, wrong variable) on `tenant_api_keys`.

**Has something similar been tried and rejected?**
No, sentinel extension hasn't been proposed before.

**Is this too similar to the current active direction?**
Current active direction is Steps 9F/9G (KB monitoring). This is a separate Step 3 expansion. Orthogonal but same SKILL.md file.

### Defend

The bug class is the most frequent in the codebase. The 2026-08-01 bug reached production undetected and was only caught by nightly after the fact. A sentinel that catches this at next nightly is high-value.

The nuance identified in the challenge (column name vs variable value confusion) actually STRENGTHENS the case — the right sentinel isn't just `.eq("tenant_id"` on tenant_api_keys (which would be a false positive since the column name is correct). The right sentinel is `.eq("tenant_id", client_id)` on tenant_api_keys — checking the value argument, not just the column name. This is a TIGHTER, MORE ACCURATE grep than what Step 3 currently does. Less noise, more signal.

Implementation: `grep -rn '\.eq("tenant_id".*client_id' backend/` catches the specific pattern. This catches: column=tenant_id but value=client_id (Python variable), which is the bug class.

### Verdict: SURVIVES

Evidence is strong (4th occurrence, same bug class, recently hit production). Challenge revealed the sentinel needs a precise grep pattern `.eq("tenant_id".*client_id` on tenant_api_keys — catches variable-value confusion, not column-name confusion. WEAKENED slightly by the nuance: correct column name makes naive grep produce false positives, requires specific pattern. Still survives because the correct pattern is achievable.

---

## Synthesis Rankings

| Idea | Verdict | Rank | Reason |
|------|---------|------|--------|
| Step 9H (PR pile alerter) | SURVIVES | 1 — WINNER | Governance mandate; systemic signal; XS via proven SKILL.md channel; 0 current alert exists |
| Idea 3 (client_id sentinel, tenant_api_keys) | SURVIVES | 2 — Parking Lot | Strong evidence; prevents 5th recurrence; nuanced grep pattern needed but achievable |
| GH #500 diagnostic comment | WEAKENED | 3 — Parking Lot | One-shot; causal chain inferred not confirmed; low systemic leverage; can be bonus action |
| Idea 4 (Step 9I completion verify) | Not debated | 4 — Parking Lot | Lower priority vs mandate items; useful but Step 9H is the mandate |
| Idea 5 (Grandfathered gate audit) | Not debated | 5 — Parking Lot | Valid concern; post-sprint audit work; not urgent enough to beat mandate |

**WINNER: Idea 1 — Step 9H Idempotent PR Pile Alerter**
