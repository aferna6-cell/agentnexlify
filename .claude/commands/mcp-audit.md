---
description: Audit MCP server token costs and connection status
---

## MCP Server Audit

Check which MCP servers are connected and their token consumption.

!`cat .mcp.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); servers=d.get('mcpServers',{}); [print(f'  {k}: {\"DISABLED\" if v.get(\"disabled\") else \"active\"}') for k,v in servers.items()]" 2>/dev/null || echo "No .mcp.json found"`

Review the above MCP servers. For each active server:
1. Is it currently needed for this session's work?
2. If not, recommend disconnecting to save context window tokens.
3. Flag any servers that might be consuming excessive tokens.

The article warns: "I've seen projects where a forgotten MCP connection was eating 15% of the context window every session."

Run `/mcp` to see live token costs per server.
