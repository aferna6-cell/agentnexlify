# Debate Log — Run 115 (2026-09-02-pm)

Top 3 ideas ranked by impact × feasibility × evidence strength.

Ranking order: Idea 1 > Idea 3 > Idea 2.
(Idea 3 ranked ahead of 2 because god-class split has a stability blocker; Idea 3 is debated to surface mechanism issue.)

---

## Idea 1: Step 9J Diagnostic Enhancement

### Challenge
- **Is the evidence strong enough?** Three nightly logs, two of which are ambiguous. The skip on 2026-09-02 might be correct — PRs #721 and #722 were rebased on 2026-09-01 and may have since auto-merged or closed. No proof of a regression.
- **Is this the highest-leverage thing right now?** Step 9K just shipped last run. Three consecutive runs with Step 9J ambiguity is real signal but not urgent.
- **What could go wrong?** The log line adds 3 characters of noise per nightly if always printed; no correctness risk.
- **Tried before?** No similar diagnostic enhancement has been proposed or rejected.
- **Too similar to active direction?** Run 114's active direction was Step 9K; this is Step 9J improvement, different block.

### Defend
- Evidence IS strong: three consecutive nightly logs with same ambiguity. The mandate (run 115 item 3) specifically flagged Step 9J as open. Even if 2026-09-02 skip is correct, adding diagnostics prevents the same ambiguity tomorrow.
- Leverage is appropriate: ~3-line SKILL.md edit, zero production code, zero risk. Cost-benefit is overwhelmingly positive.
- Autonomous-executable: same channel (SKILL.md edit) that successfully delivered Steps 9C, 9E, 9F, 9G, 9I, 9J, 9K. Pattern is proven.
- The "silent-green automation" pattern from bug-patterns.md is directly applicable here: a step that says "skipped" is indistinguishable from "skipped because no work" vs "skipped because detection failed" — identical to Keys Koffee.

### Verdict: **SURVIVES → chosen as winner**

---

## Idea 3: Step 9L — Per-Tenant Widget Health Alert

### Challenge
- **Is the evidence strong enough?** Yes — bug-patterns.md documents the exact scenario (Keys Koffee silent widget disconnect). The pattern is real.
- **Is this the highest-leverage thing?** A widget health check would catch the highest-severity customer churn risk. High value.
- **What could go wrong?** The mechanism is blocked. Supabase MCP is unavailable in headless/nightly sessions (confirmed run 88). Without DB access, the step cannot query `widget_configs`. Filing a GH issue without data is noise, not signal.
- **Has something similar been tried?** Not as a SKILL.md step, but the Supabase MCP headless block is a documented hard constraint.

### Defend
- The mechanism block is real but potentially workaround-able: if Step 9L used the Supabase REST API directly (anon key, RLS) rather than MCP, it could query `widget_configs`. But this introduces a new pattern (REST calls in SKILL.md) that hasn't been validated and requires exposing the anon key to the nightly runner.
- The workaround introduces more scope than the subconscious recommendation should take on in one run.
- Even if the REST workaround works, the nightly runner's access to `widget_configs` depends on RLS policies — unknown without testing.

### Verdict: **WEAKENED → parking lot**
Valuable idea, mechanism blocked. Revisit when either: (a) Supabase MCP becomes available in headless, or (b) a safe REST query pattern is validated for nightly use.

---

## Idea 2: os_tool_executions.py God Class Split

### Challenge
- **Is the evidence strong enough?** 775 lines, 3 concerns, >600 threshold — evidence is clear. Run 115 mandate item 5 flagged this explicitly.
- **Is this the highest-leverage thing?** A well-split file would clean up M9.2 blast radius. High structural value.
- **What could go wrong?** Two commits landed since 2026-08-30 (M8 close fixes: "preserve send_email input", "send-only Gmail proof"). The 4d+ stability threshold is not met. Splitting an actively-changing file risks a merge conflict with in-flight M8/M9 work.
- **Has something similar been tried?** No — never proposed. But the timing constraint is binding.

### Defend
- The stability argument is real. A god-class split during active M8 close-out commits is risky — callers are changing, a split would need to track those changes simultaneously.
- The mandate item 5 condition was "if stable (0 commits 4d+)". That condition is not met. Subconscious follows its own mandate.
- The correct action is to check again in run 116 when the 4d window may have passed.

### Verdict: **WEAKENED → parking lot (recheck run 116)**
Condition not met. Carry forward to run 116 with explicit stability check.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Step 9J Diagnostic Enhancement | SURVIVES | **Winner** |
| Step 9L Per-Tenant Widget Health | WEAKENED | Parking lot — mechanism blocked |
| os_tool_executions.py split | WEAKENED | Parking lot — stability threshold not met |
| M9.2 Schema Migration Guard | Not debated | Implementation task, not subconscious scope |
| SUPABASE_ACCESS_TOKEN Escalation | Not debated | Step 9M candidate for future run |
