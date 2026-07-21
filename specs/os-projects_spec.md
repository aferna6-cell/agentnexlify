# Spec: Multi-Department Projects ("OS Projects")

Status: SPEC (suite item 4 — orchestration pillar). Implementation is a
separate effort; this locks scope and contracts first per daily-skills
sequencing.

## Goal
One owner ask ("launch a spring promo") becomes a visible, approvable PLAN of
department steps, then executes across departments with per-step deliverables
riding the existing approval + outbound-guard rails. This is the
supervisor/sub-agent pattern (Gemini Enterprise, Copilot multi-agent) sized
for a business owner: one approval for the plan, normal approvals for each
outbound artifact.

## Non-goals (v1)
- No agent-to-agent free-form negotiation; the plan is a static DAG once
  approved.
- No cross-tenant or cross-vendor (A2A) execution.
- No new engine departments; steps route to the existing 8.
- No parallel step execution; sequential with explicit ordering.

## User stories
1. Owner types a big ask; the OS replies with a numbered plan (department +
   objective per step) and an Approve plan button.
2. Owner approves; steps run one at a time; each deliverable appears in the
   normal approvals queue tagged with the project.
3. Owner opens the project view: steps with status (pending / running /
   awaiting approval / done / failed) and links to each run's trace.
4. Owner cancels a project; unstarted steps never run.

## Data model (migration N+1)
- `os_projects` (client_id, title, ask, status: draft|approved|running|done|
  canceled|failed, created_at, updated_at)
- `os_project_steps` (client_id, project_id FK, position int, department,
  objective text, status, agent_run_id nullable, created_at, updated_at)
Both client_id-scoped (os_* family), RLS on/no policies, tenant_scope
overrides added.

## Flow
1. PLAN: `POST /api/v1/os/projects` {ask} → planner call (Opus advisor,
   task-budget rules apply) returns 2-6 steps [{department, objective}];
   validate departments against KNOWN_DEPARTMENTS; persist draft.
2. APPROVE: `POST /projects/{id}/approve` → status approved; runner picks up.
3. EXECUTE: background runner (5-min automation tier, same lease) takes the
   next pending step of each approved project, drives one engine turn via
   os_thread_runner with force_agent_id=department and prompt =
   project ask + step objective + summaries of completed steps' deliverables.
   Step → awaiting_approval when the run parks a draft; a step completes when
   its deliverable is approved+sent or needs no deliverable.
4. OBSERVE: `GET /projects/{id}` returns steps + run ids (trace viewer links).
5. CANCEL: `POST /projects/{id}/cancel`.

## Invariants
- Every outbound artifact still passes resolve_deliverable_status +
  NEVER_AUTO_SEND_AGENTS + outbound guard — a project approval is NOT an
  auto-send grant.
- Steps cap: 6. Active projects per tenant cap: 3.
- Step context passes deliverable SUMMARIES (title + first 300 chars), never
  raw customer PII dumps.
- Planner failure → project stays draft with error note; never a half-plan.

## Tests
- Plan validation (department whitelist, caps, malformed planner output).
- Runner picks steps in order, one per tick, skips canceled.
- Deliverable approval advances the step; rejection fails the step and pauses
  the project.
- Trace links resolve.

## Rollout
agent_os plan only; flag `os_projects_enabled` (platform_settings), default
off; pilot on the Agent Nexlify tenant first.
