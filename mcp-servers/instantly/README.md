# Instantly.ai MCP server

Wraps the [Instantly.ai](https://instantly.ai) v2 API so Claude can run cold-email
campaigns: list inboxes, create a campaign, add leads, start/stop sending, and
read analytics + replies.

- **Base URL:** `https://api.instantly.ai/api/v2`
- **Auth:** `Authorization: Bearer $INSTANTLY_API_KEY`
- **Transport:** stdio (FastMCP)

## Setup

1. In Instantly: **Settings → Integrations → API keys → Create key**.
2. Export the key in the environment that launches Claude Code:
   ```bash
   export INSTANTLY_API_KEY="your-key"
   ```
   The key is read from the process env — it is never stored in this repo.
3. Add the server to `.mcp.json` (see the `instantly` entry in `.mcp.example.json`),
   then restart Claude Code. Verify the tools load with `/mcp`.

Standalone smoke test:
```bash
cd mcp-servers/instantly
INSTANTLY_API_KEY=... uv run python server.py   # or: pip install -e . && python server.py
```

## Tools

| Tool | Instantly endpoint | Use |
|------|--------------------|-----|
| `list_sending_accounts` | `GET /accounts` | See connected/warmed inboxes (check first) |
| `list_campaigns` | `GET /campaigns` | List campaigns + status |
| `get_campaign` | `GET /campaigns/{id}` | One campaign's full config |
| `create_campaign` | `POST /campaigns` | Build a campaign (schedule + email step) — created in DRAFT |
| `add_lead_to_campaign` | `POST /leads` | Add a prospect to a campaign |
| `activate_campaign` | `POST /campaigns/{id}/activate` | **Start sending real emails** |
| `pause_campaign` | `POST /campaigns/{id}/pause` | Stop sending |
| `get_campaign_analytics` | `POST /campaigns/analytics` | Sent / opens / replies / bounces |
| `list_emails` | `GET /emails` | Read sent + received messages (replies) |

Every tool returns `{"ok": true, "data": ...}` on success or
`{"ok": false, "status": <code>, "error": <message>}` on failure — including a
clear message when `INSTANTLY_API_KEY` is unset.

## Typical flow

```
list_sending_accounts()            # confirm an inbox is connected + warmed
→ create_campaign(name, subject, body, sending_accounts=[...])   # DRAFT
→ add_lead_to_campaign(campaign_id, email, first_name=..., company_name=...)   # repeat per lead
→ activate_campaign(campaign_id)   # sending starts
→ get_campaign_analytics(campaign_id)   # monitor
→ list_emails(campaign_id)         # read replies
→ pause_campaign(campaign_id)      # stop when done
```

`create_campaign` starts DRAFT on purpose — leads and inboxes get attached before
anything sends. `activate_campaign` is the only tool that puts email on the wire.

## Eval prompts

Run these with the server loaded to check tool triggering + coverage:

1. "Which Instantly inboxes are connected and warmed up?" → `list_sending_accounts`
2. "Show me my Instantly campaigns and whether they're active." → `list_campaigns`
3. "Create an Instantly campaign called 'AgentNexLiFy — Plumbers Q3', subject
   'Quick question about {{companyName}}', body '<...>', sending from
   support@agentnexlify.com." → `create_campaign` (draft)
4. "Add jane@acme.com (Jane Doe, Acme Plumbing) to campaign <id>." → `add_lead_to_campaign`
5. "Start sending campaign <id>." → `activate_campaign`
6. "How many replies has campaign <id> gotten this month?" → `get_campaign_analytics`
7. "Show me the latest replies on campaign <id>." → `list_emails`
8. "Pause campaign <id>." → `pause_campaign`
9. "What's the full config of campaign <id>?" → `get_campaign`

## API reference

- Base + auth + endpoints: `https://developer.instantly.ai/llms.txt`
- Create campaign body: `https://developer.instantly.ai/api-reference/campaign/create-campaign.md`
- Create lead body: `https://developer.instantly.ai/api-reference/lead/create-lead.md`
