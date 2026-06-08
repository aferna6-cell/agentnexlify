# Agent OS North Star — What's Done, What's Left

**Plan** · 2026-06-08 · branch `claude/nexlify-small-business-positioning-zRwhQ`

> **North star (internal, not a sales pitch):** an AI agent that sits on top of a
> company's data and takes actions for them — and learns from those actions over time.
> Vehicle: the **Agent OS**. Framing: **Know → Decide → Act → Learn.**
>
> This plan is grounded in a direct read of `main` on 2026-06-08, not in docs. The
> headline correction from the prior positioning pass: the Agent OS foundation **and**
> its action layer are **already merged to `main`** (PR #177, merged 2026-05-27). The
> product is substantially further along than `planning/quick-suite-positioning-2026-06-08.md`
> claimed. This plan supersedes that doc's state assessment.

---

## 1. The north star in four verbs

| Verb | Meaning | Quick Suite analog | Agent OS piece |
|---|---|---|---|
| **Know** | Hear every channel + remember the business | Quick Index | Group A inbound bridges + `os_memory` + widget KB / `tenant_profile` |
| **Decide** | Route each message: answer / delegate / backlog | (the agent's judgment) | `orchestrator.py` (Opus 4.7) |
| **Act** | Do the thing back out in the real world | "take action" — the defining property | Group B action handlers + approval gate |
| **Learn** | Tie actions to outcomes, get better | (Quick's data flywheel) | **not built** — the open frontier |

Success = an SMB owner talks to one teammate that hears all their channels, decides
what to do, acts (with an approval gate they can relax), and gets better the longer
it runs.

---

## 2. What's DONE — verified in `main` (2026-06-08)

This is the corrected picture. All paths below are present on `origin/main`.

### Know — the OS hears + remembers
- **Inbound bridges (Group A):** `backend/routers/os_inbound.py` + `migrations/124_os_threads_inbound.sql`, `125_tenant_integrations_inbound_bridges.sql`. Widget + email + SMS + Facebook land in `os_threads`. Tests: `test_os_inbound_{bridge,email,facebook,sms,routes}.py`, `test_agent_os_bridge.py`.
- **Semantic memory:** `backend/services/os_memory.py` + `migrations/121_os_memory_entries.sql`. Voyage `voyage-3-lite` 512d, cosine ANN via `match_os_memory`. Kinds: fact / preference / decision / conversation_summary.
- **Read-only data access:** `os_workers/tools.py` `WorkerTools` — recent_leads, stale_leads, widget_conversation, appointments_between, tenant_profile + widget KB, semantic memory. Tenant-scoped on `client_id`.

### Decide — the orchestrator routes
- **`backend/services/orchestrator.py`** — Opus 4.7 classifies each turn → answer / delegate / backlog. In `main`.
- **`os_thread_runner.py`** — single source of truth for one user turn; same pipeline for owner chat and inbound bridge.
- **Routers live in app:** `os_agent_runs`, `os_backlog`, `os_orchestrate`, `os_threads`, `os_usage`, `os_memory` all mounted.

### Act — the OS does things (this is the big correction)
- **8 action handlers, all in `main`** under `backend/services/os_actions/`: `calendar.py`, `crm.py`, `email.py`, `gbp.py`, `sms.py`, `social_facebook.py`, `social_instagram.py`, `widget.py`. Each declares `SPEC: ActionSpec` + async `run`; auto-discovered by the registry (`__init__.py`).
- **Approval gate:** `backend/routers/os_deliverables.py` — `approve_deliverable` creates an `os_action_runs` row (queued) and schedules `run_action` via BackgroundTasks. Retry route present.
- **Per-tenant auto-send toggle:** `migrations/128_tenants_os_auto_send.sql` (`os_auto_send_enabled`). `_tenant_auto_send_enabled()` sets deliverable status `approved` (auto) vs `pending_approval`.
- **Idempotency:** `migrations/126_os_action_runs.sql` — partial unique index on (deliverable_id, action_type) WHERE status='succeeded'.
- **5 workers emit `action_type`:** booking → `calendar.event.create`, customer_question → `widget.message`, campaign + lead_nurture → `_choose_action_type()`, generalist.
- **Frontend approval UI:** `frontend/src/pages/AgentOS.jsx`, `components/os/DeliverablePanel.jsx`, `components/os/AgentRunFlowchart.jsx` — all with `.test.jsx`.

### Consistency — sync (Group C)
- **`backend/routers/os_sync.py`** + `migrations/127_os_sync_state.sql`, `129_chat_messages_os_mirror.sql`. Outbound mirror back to channel stores. Background tick.

### Tests
- `test_os_actions.py` (61 tests), `test_os_workers_tools.py`, `test_os_sync.py`, plus the inbound suite. OS MVP runs end-to-end.

**Corrected maturity: ~65–75% of the way to the north star.** Know, Decide, and Act
all ship today and are merged. The skeleton, the action layer, and the approval/auto-send
gate — the hard parts — are done.

---

## 3. What's NOT done — the real gaps, ranked

| # | Gap | North-star verb | Why it matters | Size |
|---|---|---|---|---|
| 1 | **End-to-end hardening of Group B** | Act | 8 handlers exist + 61 tests, but no verified live round-trip per handler against real provider creds (M365/Resend/Twilio/GBP/Meta). "Builds + tests pass" ≠ "sends a real email to a real lead." | M |
| 2 | **Learning loop** (action → outcome → memory) | **Learn** | The north star's 4th verb has **zero code**. Actions fire and write `os_action_runs`, but no outcome is captured (did the lead reply? book? convert?) and fed back. Without this, the OS never gets better — it's stateless per task. | M–L |
| 3 | **Research worker** | Know/Decide | Quick Research pillar. `deep_researcher` Managed Agent type exists but is NOT an OS worker. No `os_workers/researcher.py`. | S |
| 4 | **Analyst worker** (NL BI) | Know/Decide | Quick Sight pillar. `data_analyst` Managed Agent type exists but is NOT an OS worker. `WorkerTools` already has the read methods. No `os_workers/analyst.py`. | S |
| 5 | **Multi-step orchestration** | Decide/Act | Quick Automate. Orchestrator does **one delegate per turn** (confirmed: no `plan_sequence`/`chain_workers`/`next_worker` markers in `backend/services/`). "Onboard a new client" = welcome email + portal + booking + contract can't run as one chained request. | M |
| 6 | **NL→`automation_rule` compiler** | Act | Quick Flows. Owner describes a rule in chat → no worker emits rule JSON for the existing automation engine (14 triggers / 9 actions). Drafts yes; persist-and-run no. Confirmed: no `automation_rule` reference in `os_workers/`. | S–M |
| 7 | **OS as front door** | (UX) | `AgentOS.jsx` exists but isn't the product home. ~70 dashboard pages still the primary surface. Pillars (Ask / Analyze / Research / Automate) not surfaced as affordances. | M |
| 8 | **Graph memory** | Learn | Deferred 2026-05-25 (`planning/decisions/2026-05-25-agent-os-graph-memory.md`). Revisit only after the learning loop produces signal that semantic recall is insufficient. | L (deferred) |

---

## 4. The path — sequenced

> Principle: the skeleton + hands exist. Prove the hands work, build the missing brains,
> close the learning loop, then make the OS the front door. Don't rebuild what's merged.

### Phase 1 — Prove Act works end-to-end (gap #1) · DO FIRST
The action handlers are merged but unproven against live providers. Before adding
anything new, take each of the 8 handlers through one real round-trip in a controlled
tenant: queue → approve → `run_action` → real provider call → `os_action_runs` succeeded
→ verify idempotency replay is a no-op. Document any handler that fails. This converts
"built" into "trusted" and is the cheapest high-value step because the code already exists.

**Status (2026-06-08):** prep done, live verification NOT done.
- ✅ Closed the test-coverage hole: Instagram (two-step Graph) + GBP handlers had zero
  behavioral `_run` tests — only SPEC sanity. Added 9 tests (`test_os_actions.py` now 61),
  mirroring the Facebook httpx-stub pattern: success path + each distinct failure stage
  (`validate`, `connector`, `ig_create_container`, `ig_publish`, `gbp_api`).
- ✅ Wrote the live round-trip runbook: `docs/agent-os-act-verification.md` — per handler:
  connector/creds, deliverable to approve, expected `os_action_runs` row, provider-side
  effect, rollback, plus failure-stage triage table.
- ☐ **The actual 8 live round-trips remain unrun.** They need real provider creds in
  staging (M365/Resend/Twilio/GBP/Meta) and a human to observe inbox/phone/calendar/page.
  Cannot run from the dev container (no creds → every send fails at `stage='connector'`).
  Phase 1 closes only when the runbook's 8-row PASS table is filled against staging.

### Phase 2 — Close the learning loop (gap #2) · the north star's 4th verb
This is the piece the user explicitly wants ("memory to reference and learn") and the
one with no code today. Minimum viable version:
- On every action that targets a lead/conversation, record the **outcome** when it
  arrives (reply received, appointment booked, payment, no-show, no-response-after-N-days).
- Write the outcome as an `os_memory` entry (kind `decision` or a new `outcome` kind)
  linked to the action and the lead, so the next time the orchestrator reasons about
  that lead/segment it can recall "last time we texted this segment at 6pm, 40% booked."
- Deterministic-first: outcome capture is a join on existing tables (leads.status,
  appointments, chat_messages), not an LLM call. Only the summary write embeds.
- This is the on-ramp to graph memory (gap #8) — build the flat learning loop first,
  measure recall, then decide on the graph per the 2026-05-25 decision triggers.

### Phase 3 — Add the two dormant pillars as workers (gaps #3, #4) · low blast radius
- **Analyst worker** — `os_workers/analyst.py` over `WorkerTools` read methods. NL question → numbers over the tenant's own leads/appointments/conversations. Back it with the `data_analyst` Managed Agent type.
- **Research worker** — `os_workers/researcher.py` fusing `widget_knowledge_base()` + web. Back it with `deep_researcher`.
- Both are **registry adds**: drop the module, orchestrator auto-discovers via `worker_descriptions()`. No platform change.

### Phase 4 — Multi-step + Flows (gaps #5, #6)
- **Multi-step (Automate):** orchestrator plans a *sequence* of workers for one request, not a single route. Real design step (state between steps, partial-failure handling, approval per step vs per plan).
- **Flows:** NL→`automation_rule` compiler worker — owner describes a rule in chat → worker emits rule JSON for the existing engine → approve → persisted + active. Bridges conversational OS to the deterministic automation substrate.

### Phase 5 — Make the OS the front door (gap #7)
Promote `AgentOS.jsx` to product home. Surface Ask / Analyze / Research / Automate as
affordances. Existing dashboard pages become drill-downs the agent links into. The
thought-process flowchart + memory already in place become the UX.

### Phase 6 — Differentiation (gap #8 + verticals)
- Re-decide graph memory once the Phase 2 learning loop produces measured signal.
- Vertical worker presets (salon / dental / restaurant / contractor) on the per-tenant KB moat.

---

## 5. Why this order

1. **Phase 1 before anything** — you have a loaded action layer no one has fired in anger. Cheapest way to de-risk the whole north star.
2. **Phase 2 second** — "learn" is the only verb with zero code and the one the user keeps returning to. It's also the on-ramp to graph memory, so building it first prevents over-engineering the graph before there's signal.
3. **Phases 3–4 are additive** — workers are registry adds; multi-step + Flows extend the orchestrator without touching the action layer.
4. **Phase 5 last among build work** — front-door UX only pays off once there's a Research + Analyst worker and multi-step to expose. Promoting the chat before the brains are in makes it look thin.

---

## 6. Success metrics (per phase)

- **P1:** all 8 handlers complete one live round-trip; idempotency replay verified no-op; failures documented.
- **P2:** ≥1 outcome kind captured per action class; orchestrator can cite a prior outcome in a routing decision; recall measured against real threads.
- **P3:** analyst + researcher answer a real tenant question end-to-end through the OS chat.
- **P4:** one chained request ("onboard a client") runs ≥3 actions in sequence with per-step approval; one NL rule compiles + persists + fires.
- **P5:** AgentOS is the default post-login route; ≥1 dashboard page reachable as an agent drill-down.

---

## 7. Risks + honest caveats

- **"Merged" is not "works against live providers."** Phase 1 exists precisely because the 52 tests are unit-level; provider creds + real sends are unverified.
- **Learning loop scope creep.** Easy to balloon into the graph-memory build. Hold the line: flat outcome capture first, measure, then decide the graph per the 2026-05-25 triggers.
- **Multi-step is a real design step, not wiring.** Partial-failure + per-step approval are where bugs live. Don't fold it into a worker — it's an orchestrator change.
- **Router sprawl (~80 routers)** is both the action surface Group B wraps and drag on the pivot. Don't let the long tail distract from Phases 1–2.
- **Don't fix-and-audit in one session** — Phase 1 hardening produces findings; fixes are a separate compound-engineering session.

---

## 8. One-line answer

The Agent OS already **knows, decides, and acts** — orchestrator + 5 workers + 8 action
handlers + approval/auto-send gate + semantic memory + inbound bridges + sync are all
merged to `main`. It is ~65–75% of the north star. What's left, in order: **prove the
action layer works live (P1), build the learning loop the OS is missing (P2), add the
Research + Analyst workers (P3), teach it multi-step + NL automation (P4), and make the
OS chat the front door (P5)** — turning a teammate that acts into one that also learns.

---

*Grounded in a direct read of `origin/main` on 2026-06-08. Supersedes the state
assessment in `planning/quick-suite-positioning-2026-06-08.md`, which predated
confirmation that PR #177 had merged.*
