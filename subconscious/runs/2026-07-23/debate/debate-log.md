# Debate Log — 2026-07-23 (Run 100)

Top 3 ideas: Idea 1 (Step 9G), Idea 2 (LoopHealthPage.jsx), Idea 4 (MCP adoption monitoring Step 9H).
Ideas 3 + 5 are lower-tier — Idea 3 (voice test audit) already covered by nightly's own verification notes; Idea 5 (quickstart doc) is useful but not systemic.

---

## Idea 1: Step 9G — kb-autopopulate self-healing trigger

### Challenge
**C1: Is the evidence strong enough?**
Step 9F fired once (nightly-2026-07-22). KB stale 10 days. But the root cause is unknown: is it a secret-rotation issue (same as the 63-day gap), a code bug in kb-autopopulate.yml, or a GitHub Actions runner issue? Triggering the workflow blindly may fail silently for a different reason.

**C2: What could go wrong?**
`gh workflow run` requires `actions: write` permission on the GITHUB_TOKEN. Nightly review uses the standard GITHUB_TOKEN from the workflow runner — it may not have this permission by default. If it fails silently, Step 9G adds noise without value.

**C3: Has this been rejected?**
No. Steps 9B-9F are all SKILL.md edits with bash blocks. This is Step 9G, same pattern. Never proposed before.

**C4: Too similar to active direction?**
Step 9F is marked `implemented`. Step 9G is the logical next step in the same chain. Not a repetition — an escalation.

**C5: Is this highest-leverage right now?**
KB 10 days stale. All 3 live tenants' AI chat uses KB for vertical answers (salon FAQ, etc.). Freshness directly impacts tenant NPS. With only 3 tenants, one bad KB answer is 33% of prod.

### Defend
**D1:** `gh workflow run` uses `workflow_dispatch` event. The nightly review runs under the standard GITHUB_TOKEN (actions: read + write). GH Actions `workflow_dispatch` can be triggered by authenticated API calls. The nightly already does `gh issue comment`, `gh run list` (read), and `gh label add` — write-side GH API calls. `gh workflow run` is the same permission tier. If it fails, we catch it with a status check and comment on GH #403 with the specific error.

**D2:** Even if the trigger fails, Step 9G generates a diagnostic log entry and GH Actions run page for human inspection. Information value: know whether the failure is a permission error vs secret-empty vs code error. Much more actionable than the current "Step 9F: KB stale" generic alert.

**D3:** Implementation is XS: ~30-line bash block, same template as Steps 9B-9F. Proven channel. No new infrastructure. Risk: SKILL.md edit → same as 5 preceding steps, all implemented.

### Verdict: **SURVIVES** → WINNER
Strongest evidence, XS effort, proven autonomous channel, directly addresses active 10-day stale window. Includes diagnostic component so failure is visible. Self-healing if secrets are valid.

---

## Idea 2: LoopHealthPage.jsx — admin frontend for Agent OS loop health

### Challenge
**C1: Is the evidence strong enough?**
Backend exists (5 vitals + Round 8 funnel metrics). But only 2-3 tenants use Agent OS. Admin currently gets the data via direct JSON call to `/api/admin/loop-health`. Is a full JSX page worth L effort at this scale?

**C2: Is this highest-leverage?**
With 2-3 Agent OS tenants, the approval loop is monitored ad-hoc. When something breaks, the admin runs `curl /api/admin/loop-health`. A page doesn't change the signal, just the UX to access it.

**C3: What could go wrong?**
L-effort frontend changes carry regression risk. Round 7 already moved 51 files. Adding another frontend page + route + sidebar entry touches App.jsx, Sidebar.jsx, and creates a new page. Low risk of breaking things but non-trivial diff.

**C4: Has something similar been rejected?**
BotHealthPage.jsx was implemented in PR #475 — not rejected, but it was a governance correction from an existing idea. LoopHealthPage would be new. Not rejected.

**C5: Too similar to active direction?**
admin_loop_health endpoint is implemented and marked `operational` in active directions. A frontend is the natural next step. But it's L effort with no immediate urgency.

### Defend
**D1:** Round 8 specifically adds funnel metrics to the endpoint. This indicates the admin is actively using the data and wants more granular insight. Someone is polling it and adding to it. A page reduces friction.

**D2:** BotHealthPage.jsx is the identical template. Implementation is 1 JSX file (~120 lines), 1 sidebar entry, 1 route. With BotHealthPage as reference, the effort is more M than L.

**D3:** As Agent OS scales (3 tenants → 10+ over the next month based on sprint velocity), a health page prevents "which tenant's loop broke?" debugging in production.

### Verdict: **WEAKENED** → Parking Lot
L effort at current Agent OS scale (2-3 tenants) is premature. Step 9G's XS KB fix delivers more value to more tenants right now. Promote LoopHealthPage as next run's candidate when Agent OS > 5 active tenants. Effort recalibrates as M once BotHealthPage.jsx is used as template.

---

## Idea 4: MCP adoption monitoring — Step 9H tracking

### Challenge
**C1: Is the evidence strong enough?**
Only 1 MCP tenant activated as of 2026-07-23. That's a sample size of 1. Monitoring 1 tenant's MCP health may not justify adding a Step 9H to the nightly SKILL.md.

**C2: What could go wrong?**
The Step 9H health check (`curl $RAILWAY_BACKEND_URL/health`) would test the general backend health, not MCP-specific functionality. The `/mcp` endpoint auth requires an `mcp_` prefix key — the nightly doesn't have one and shouldn't store tenant credentials. This makes a meaningful MCP-specific health check impossible from the nightly runner.

**C3: Is this the highest-leverage thing right now?**
1 MCP tenant → monitoring is premature. If the MCP server is down, the tenant will report it. At this stage, the investment in observability infrastructure returns more value when there are 5+ tenants.

**C4: Similar to active direction?**
Step 9F (KB staleness) and Step 9G (KB self-healing trigger) are both nightly SKILL.md additions. A Step 9H would be the 3rd nightly step in this run — risk of nightly bloat. Steps should be added when the monitoring gap is demonstrated, not pre-emptive.

### Defend
**D1:** The docs record is a good signal: `mcp-owner-server.md` was created in the same PR as MCP launch. Someone is tracking adoption. A nightly Step is useful for establishing a baseline before problems surface.

**D2:** A simple HTTP health check on `/docs` or `/` (no auth required) would still catch the MCP server being down. Not perfect but better than nothing.

### Verdict: **KILLED** — Evidence too thin (1 tenant), mechanism weak (can't test auth without tenant key), premature observability. Revisit when 5+ MCP tenants activated or when a MCP outage is reported.

---

## Final Rankings

| Idea | Verdict | Destination |
|------|---------|-------------|
| Idea 1: Step 9G (KB self-healing) | SURVIVES → **WINNER** | Implementation sketch |
| Idea 2: LoopHealthPage.jsx | WEAKENED | Parking lot (promote when Agent OS >5 tenants) |
| Idea 3: Voice test regression audit | Not debated (evidence already covered by nightly) | Parking lot (low) |
| Idea 4: MCP Step 9H | KILLED | Rejected (premature, mechanism weak) |
| Idea 5: MCP quickstart doc | Not debated | Parking lot (human-authored content) |
