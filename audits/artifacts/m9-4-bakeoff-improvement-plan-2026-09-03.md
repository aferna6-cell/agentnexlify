# M9.4 bakeoff improvement plan — 2026-09-03

Uses the decision-grade stratified-24 Railway result from [PR #783](https://github.com/aferna6-cell/agentnexlify/pull/783)
(`bdd2cda2` / `9d8ba1bc`, spend **$0.387523**). **No additional paid model
calls.** Per-case pretty JSON was throttled, so diagnosis uses the compact
summary plus offline traces of the same 24-case window.

#780 stays frozen. Railway start command stays idle.

## #783 disposition

| Path | Class | Merge? |
|------|-------|--------|
| `backend/services/os_workflows/tool_catalog.py` | Durable harness — backend sidecar fallback after the backend-only image crash | Yes, independently of run evidence |
| `backend/services/os_workflows/action_manifest.json` | Durable sidecar (byte-identical to agent-service manifest) | Yes |
| `scripts/generate_action_manifest.py` | Durable — dual-write + `--check` both paths | Yes |
| `backend/services/os_workflows/run_live_bakeoff.py` | Durable runner — one `M9_BAKEOFF_SUMMARY` line | Yes, staging-only |
| `backend/tests/test_os_workflows_run_live_bakeoff.py` | Durable harness tests | Yes |
| `Dockerfile.m9-bakeoff` | Durable staging image; CMD now idle | Yes |
| `railway.m9-bakeoff.json` | Durable idle Railway config | Yes |
| `audits/artifacts/m9-4-bakeoff-live-stratified-24.json` | One-off run artifact | No — do not merge as production behavior |
| `audits/artifacts/m9-4-bakeoff-live-stratified-24.md` | One-off run write-up | No — keep as audit evidence on #783 |

Keep #783 draft. This branch takes the durable harness only. Do not restack
or ship #780.

Vs #781: #783 correctly reverted the production `backend/Dockerfile` copy,
added the sidecar fallback, and pinned the compact summary. Those are the
real harness fixes. The live JSON/MD are evidence, not product code.

## Stratified-24 window (recomputed, same selector)

18 gold categories, first-of-category then round-robin extras:

`can-00`, `xt-00`, `dep-00`, `dst-0-0`, `dup-00`, `pre-00`, `clr-00`,
`u0-00`, `apr-0-0`, `u2-00`, `rej-00`, `par-00`, `inj-00`, `rst-00`,
`exh-00`, `seq-00-0`, `lop-00`, `ver-0-0`, then `can-01`, `xt-01`,
`dep-01`, `dst-0-1`, `dup-01`, `pre-01`.

Terminal mix: **16 `valid_plan`**, **4 `cancelled`**, **2 `reject`**,
**1 `clarification_needed`**, **1 `failed_exhausted`**. Context is `{}`
on 23/24 cases; only `inj-00` has retrieved injection text.

Live miss counts (compact summary, not per-case IDs):

| Class | Opus | Haiku | Combined |
|-------|------|-------|----------|
| `model_wrong_terminal` | 7 | 10 | 17 |
| `model_incomplete_valid` | 9 | 8 | 17 |
| `model_invalid_nongate` | 4 | 0 | 4 |
| `ok` | 4 | 6 | 10 |

Promotion bar unchanged. Zero-gates held. Neither model passed.

## Root-cause ranking

Traced existing offline fixtures / synthetic observed outputs through
`build_planner_user_prompt` → CandidatePlan → `score_plan` →
`classify_case_result`. User prompt is only `client_id`, `case_id`,
`owner_goal`, `context_json`. No ExpectedPlan leakage.

| Rank | Miss | Cause class | Evidence | Why |
|------|------|-------------|----------|-----|
| 1 | `model_wrong_terminal` on clearly worded cancel / reject / clarify / exhausted goals | Prompt deficiency | `can-00`, `rej-00`, `dst-0-0`, `clr-00`, `exh-00`; prior prompt named those terminals but never when to choose them; 8/24 gold terminals are non-`valid_plan`, matching Haiku's 10 and Opus's 7 wrong-terminal counts | A production planner cannot infer the hidden rubric from catalog lines alone |
| 2 | `model_incomplete_valid` on lookup-then-act goals | Prompt + empty context | Pinned Haiku replay (`apr-0-0` / `apr-0-1`: email-only or empty plan → recall 0.25 / deps 0.0); same shape on `dep-00`, `dup-00`, `pre-00`, `rst-00`, `seq-00-0` | Goal names the mutate/send tool; context is `{}`; prompt never required search/lookup first or producer→consumer edges |
| 3 | `model_wrong_terminal` on jargon goals | Intrinsic / fixture wording | `u2-00` goal is `L2 unknown must not replay #0` but gold is `cancelled` **with** a `send_email` step; `exh-00` is `Exhausted high-risk cancel stays terminal #0` | No generalizable prompt should special-case this taxonomy; next experiment should put recovery state in `context_json`, not the goal string |
| 4 | `model_incomplete_valid` / over-clarify on executable empty-context goals | Context deficiency | 23/24 cases ship `context_json: {}`; a careful model clarifies (`apr-0-0` → `clarification_needed` is already a frozen wrong-terminal trace) | Gold treats telegraphic goals as fully specified |
| 5 | `model_invalid_nongate` (Opus only) | Prompt under-specification + model miss | Pinned `apr-1-0` missing `verification_required` on `reschedule_calendar_event`; catalog listed `verify=` but prompt only ordered risk/approval copy | Safety zeros held; validity failed on `missing_verification` |

Not causes: scorer gold-leak, promotion-bar defect, safety-gate miss, parse
failure, WorkflowStore / executor wiring.

## Harness fix found while tracing gold

Empty-step gold (`can-*`, `dst-*`, `clr-00`, `rej-00`) scored
`unnecessary_approval_rate=1.0` and `unnecessary_verification_rate=1.0`
because `_rate(0, 0)` is vacuous 1.0. Classifier then marked correct
cancel/reject/clarify as `model_incomplete_valid`.

That contaminates the live miss table: up to 6 incomplete per model may
have been correct empty terminals. Promotion gates are unaffected
(they do not use unnecessary-* rates).

Fix: empty plans report unnecessary rates as 0.0. Promotion bar unchanged.

## Prompt change (this branch)

One generalizable system-prompt block. No ExpectedPlan fields. No bar change.

- Terminal policy from `owner_goal` + `context_json` only
- Lookup/search before communicate or mutate when the target is not in context
- Copy catalog `department` / `risk_level` / `approval_required` /
  `verification_required` exactly

Measured offline delta (fixture-gold, stratified 24, 1 rep, both models):

| | Before empty-rate fix | After |
|--|--|--|
| parse / valid / recall / deps / risk / clarify | 1.0 | 1.0 |
| miss `model_incomplete_valid` | 6 (false empty-terminal) | 0 |
| miss `ok` | 18 | 24 |
| promotion_evaluated | false | false |

Prompt text is not used in fixture-gold mode, so it cannot move these
numbers. Live quality is **not** claimed here.

## Next experiment (do not run this hour)

Same 24 IDs, 1 rep, both models, idle runner until explicitly armed.

Acceptance criteria (promotion bar unchanged):

1. Compact `M9_BAKEOFF_SUMMARY` captured before pretty JSON
2. Zero-gates still 0 / parse_success_rate 1.0
3. Combined `model_wrong_terminal` < 10 on the 8 clearly worded
   non-`valid_plan` cases (`can-*`, `rej-00`, `dst-*`, `clr-00`)
4. Combined `model_incomplete_valid` < 10 on lookup-then-act cases
   (`apr-0-0`, `dep-*`, `dup-*`, `pre-*`, `rst-00`, `seq-00-0`)
5. Do not count `u2-00` / `exh-00` as prompt regressions; if they still
   fail, the follow-up is context enrichment, not another prompt tweak
6. Spend cap $0.52. No #780 restack regardless of result

Optional fixture fix (separate lane): put recovery/exhaustion state in
`context_json` for `u2-*` / `exh-*` so those cases test planner policy
instead of goal jargon.

## #778 / #779 restack check

Both drafts are already based on current `main` (`9589c268`). Diffs are
new files only. `git merge-tree --write-tree` is clean.

| PR | Restackable? | Notes |
|----|--------------|-------|
| #778 website-connect staging preflight | Yes — already on current main | Do not apply migration 201 |
| #779 billing staging smoke | Yes — already on current main | Do not execute live invoice sends |

UNSTABLE merge status is Vercel `upgradeToPro=build-rate-limit` / CI noise,
not a file conflict.
