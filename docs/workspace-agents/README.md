# AgentNexLiFy Workspace Agents

This folder contains builder-ready blueprints for ChatGPT workspace agents tailored to AgentNexLiFy.

These agents are meant for internal team workflows, not the customer-facing widget itself. The widget serves end customers. Workspace agents help the AgentNexLiFy team onboard tenants, monitor automations, and handle support faster.

## Recommended Build Order

1. `onboarding-concierge.md`
2. `tenant-ops-monitor.md`
3. `support-triage.md`

## Shared Defaults

- Start each agent as `Private to me` during setup and preview.
- Prefer agent-owned accounts backed by service accounts where possible.
- Keep write actions on `Always ask` for v1.
- For Slack, use shared authentication on every connected app and start in mention-only channels.
- Attach the most relevant product specs and SOP docs as Files before broad rollout.
- Publish to the workspace directory only after a few dry runs with realistic examples.

## Suggested Files To Attach

- `README.md`
- `specs/onboarding-v2_spec.md`
- `specs/ops-automation-surfacing_spec.md`
- `specs/marketing-automation_spec.md`
- `specs/self-maintenance_spec.md`
- `docs/dev-knowledge/canonical-schema.md`
- Any internal onboarding SOPs, support macros, escalation playbooks, or customer success docs

## Suggested App And Tool Pattern

Use whichever apps are enabled in the ChatGPT workspace, but the most useful mix is usually:

- Slack
- Google Drive, SharePoint, or Box
- Gmail or Outlook
- Google Calendar
- Linear or Jira
- Web search
- Custom MCPs for internal tenant/admin data

## Publish Flow

1. Open `Agents` in ChatGPT.
2. Select `Create`.
3. Paste the builder prompt from the chosen blueprint file.
4. Add tools, apps, files, and starter prompts from that file.
5. Preview with 3 to 5 realistic prompts.
6. Keep write actions approval-gated until the workflow is stable.
7. Publish to the workspace directory when the agent is reliable.

## Current Blueprints

| Agent | Purpose | Primary Channel |
|------|---------|-----------------|
| Onboarding Concierge | Move a new tenant from signed deal to live widget and ready-to-launch status | ChatGPT + optional Slack |
| Tenant Ops Monitor | Watch automations, integrations, and silent failures across active tenants | Scheduled ChatGPT + Slack |
| Support Triage | Turn support requests into clear replies, internal notes, and routed tickets | Slack + ChatGPT |
