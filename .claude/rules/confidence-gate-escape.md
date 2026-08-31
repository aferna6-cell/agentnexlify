# Confidence Gate Escape — Human / External Blockers

## Rule
When a **CONFIDENCE GATE** (Stop hook or injected user prompt) demands ≥90% or else “keep working,” you may **stop below 90%** if the remaining uncertainty is **not agent-fixable**.

Do **not** busy-loop: reminting OAuth URLs, re-polling status every turn, re-running the same smoke, or spinning subagents that cannot change the outcome.

## When escape applies (all must be true)
1. You already verified what *is* agent-owned (tests, deploys, code fixes, logs).
2. Confidence is honestly **&lt; 90%** because of a **human or external** blocker.
3. Re-checking would only repeat the same evidence (status still false, 0 callbacks, no new credentials).
4. You have already told the human the exact next action once (or the action is unchanged).

Examples of valid escape blockers:
- Google/OAuth consent, phone/device step-up, test-user allowlist
- Owner must paste a secret into Railway / vault
- Manual GCP Console / Stripe Dashboard click
- Waiting for a third-party approval or email you cannot access

## Required stop format
When escaping, finish with something like:

```
Confidence: NN% — HOLD (escape: external blocker)
Verified: <what you already proved> — PASS
Blocked on: <one concrete human action>
Not looping: will resume when you reply <signal> (e.g. `both connected`)
```

Then **stop**. Do not mint another URL pair, launch another poll subagent, or schedule another timer solely because the gate said “keep working.”

## When escape does NOT apply
- Tests failing, build broken, unverified fix → keep working
- Ambiguous code path you have not inspected → keep working
- You have not attempted an available automatable path yet → keep working
- Confidence &lt; 90% for soft reasons (“might regress”) without evidence → keep verifying, don’t claim escape

## Interaction with the hook
`scripts/claude-hooks/confidence-gate.sh` still forces one self-assessment on first Stop. After that assessment, if escape criteria hold, a second Stop is allowed — **do not** interpret &lt;90% as an infinite “keep working” duty when the only gap is human action.

## Why
2026-08-31 M8 staging: PKCE + service_role verified; Calendar/Gmail blocked on owner consent + Google phone step-up. Confidence-gate “keep working” produced dozens of identical remint/poll cycles with no new evidence.

## Cross-refs
- `.claude/rules/self-verification.md`
- `scripts/claude-hooks/confidence-gate.sh`
- `.claude/rules/no-assumptions.md` (honest confidence; don’t invent connected=true)
