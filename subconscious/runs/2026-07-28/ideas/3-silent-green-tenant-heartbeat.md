# Idea 3 — Silent-Green Tenant Heartbeat (Nightly Step 9H)

**Category:** Customer value + operational resilience  
**Evidence strength:** HIGH — Keys Koffee widget dropped 5+ weeks undetected; booking CTA plain text (money path) also silent; bug-patterns.md explicitly calls for prevention pattern  
**Execution channel:** nightly SKILL.md bash block

## What

Add Step 9H to nightly-commit-review SKILL.md: for each active paid tenant, verify at least 1 widget conversation in the last 7 days. Alert on GH (new issue or #403 comment) if any paid tenant shows 0 conversations.

```bash
# Step 9H: Paid tenant heartbeat
python3 -c "
import os, sys
from supabase import create_client
client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Paid tenants: chatbot ($19.99) or agent_os ($99.99) plan
tenants = client.table('tenants').select('id,name,plan').in_('plan', ['chatbot','agent_os','growth','autopilot','professional','enterprise']).eq('is_active', True).execute().data

silent = []
for t in tenants:
    result = client.table('conversations').select('id', count='exact').eq('client_id', t['id']).gte('created_at', '$(date -d \"7 days ago\" --iso-8601)T00:00:00Z').execute()
    if result.count == 0:
        silent.append(f'{t[\"name\"]} ({t[\"id\"][:8]}) — plan={t[\"plan\"]}')

if silent:
    body = 'Silent-green tenant alert (Step 9H): the following paid tenants had 0 widget conversations in the last 7 days:\n\n' + '\n'.join(['- ' + t for t in silent]) + '\n\nCheck: (1) widget embedded on their site? (2) widget_config active? (3) KB serving? Manual test: embed widget, send a message.'
    # Create GH issue if silent tenants found
    gh issue create -R aferna6-cell/agentnexlify --title 'Silent-green tenant alert: {len(silent)} paid tenant(s) with 0 conversations (7 days)' --body '$body' --label 'bug,critical'
" 2>&1 | head -20
```

## Why it matters

Bug-patterns.md explicitly documents this prevention pattern after the Keys Koffee incident: "every automation/tenant integration needs a heartbeat distinguishing 'ran and found nothing' from 'never ran'."

Paying customers at $19.99–$99.99/mo receiving zero AI value = churn risk before complaint. The Keys Koffee failure ran 5+ weeks before detection — 5 subscription weeks of value delivered at $0. At 3 silent tenants per quarter, that's ~$300/quarter in retained revenue vs churn.

The nightly already has Supabase access precedent (KB staleness check queries DB metadata). Adding a conversations heartbeat is additive, same pattern.

## Complexity note

Requires careful tenant filter: exclude `free` plan tenants (internal lapsed state, never sold). Must use `client_id` not `tenant_id` on conversations table (critical invariant). Schema: `conversations.client_id` references `tenants.id`.

Weakness: A tenant with a broken widget but active conversations (e.g., direct API testing) would NOT be flagged. The check catches zero-activity tenants, not zero-quality tenants. Still catches the Keys Koffee class.
