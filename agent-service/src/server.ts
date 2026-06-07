/**
 * Minimal HTTP server for agent-service.
 *
 * Routes:
 *   GET  /health             -> 200 {"status":"ok"}
 *   POST /agents/:name/run   -> RunResult JSON
 *
 * Request body for /agents/:name/run:
 *   { "prompt": "...", "timeout_ms": 30000 }
 *
 * No external HTTP framework — plain node:http to keep the image small.
 */

import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { runAgent } from './runner.ts';
import { runOrchestration } from './agent-os-runtime/orchestrate.ts';
import type { SharedContext } from './agent-os/types/agent.ts';

const PORT = parseInt(process.env.PORT ?? '3100', 10);

async function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk: Buffer) => { data += chunk.toString('utf8'); });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function json(res: ServerResponse, status: number, body: unknown): void {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

/** Extract :name from /agents/:name/run, or null if path does not match. */
function parseAgentName(url: string): string | null {
  const parts = url.split('/');
  // Expect ['', 'agents', '<name>', 'run']
  if (parts.length === 4 && parts[1] === 'agents' && parts[3] === 'run') {
    const name = parts[2];
    // Validate: lowercase alphanumeric + hyphens only
    if (/^[a-z0-9-]+$/.test(name)) return name;
  }
  return null;
}

const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
  try {
    if (req.method === 'GET' && req.url === '/health') {
      json(res, 200, { status: 'ok' });
      return;
    }

    // Agent OS orchestration. FastAPI (the data plane) authenticates the tenant,
    // assembles its SharedContext from Supabase, and POSTs it here; agent-service
    // runs the engine and returns the result + a record for FastAPI to persist.
    // agent-service never touches a database.
    if (req.method === 'POST' && req.url === '/orchestrate') {
      const raw = await readBody(req);
      let body: { accountId?: unknown; ask?: unknown; context?: unknown; forceAgentId?: unknown };
      try {
        body = JSON.parse(raw) as typeof body;
      } catch {
        json(res, 400, { error: 'invalid JSON body' });
        return;
      }
      if (typeof body.accountId !== 'string' || !body.accountId.trim()) {
        json(res, 400, { error: 'accountId must be a non-empty string' });
        return;
      }
      if (typeof body.ask !== 'string' || !body.ask.trim()) {
        json(res, 400, { error: 'ask must be a non-empty string' });
        return;
      }
      if (typeof body.context !== 'object' || body.context === null) {
        json(res, 400, { error: 'context must be the tenant SharedContext object' });
        return;
      }
      if (body.forceAgentId !== undefined && typeof body.forceAgentId !== 'string') {
        json(res, 400, { error: 'forceAgentId must be a string when provided' });
        return;
      }
      const out = await runOrchestration({
        accountId: body.accountId,
        ask: body.ask,
        context: body.context as SharedContext,
        forceAgentId: body.forceAgentId,
      });
      json(res, 200, out);
      return;
    }

    const agentName = parseAgentName(req.url ?? '');
    if (!agentName || req.method !== 'POST') {
      json(res, 404, { error: 'not found' });
      return;
    }

    const rawBody = await readBody(req);

    let payload: { prompt?: unknown; timeout_ms?: unknown };
    try {
      payload = JSON.parse(rawBody) as { prompt?: unknown; timeout_ms?: unknown };
    } catch {
      json(res, 400, { error: 'invalid JSON body' });
      return;
    }

    if (typeof payload.prompt !== 'string' || !payload.prompt.trim()) {
      json(res, 400, { error: 'prompt must be a non-empty string' });
      return;
    }

    const timeoutMs =
      typeof payload.timeout_ms === 'number' && payload.timeout_ms > 0
        ? payload.timeout_ms
        : undefined;

    const result = await runAgent(agentName, payload.prompt, timeoutMs);
    json(res, 200, result);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('agent-service: unhandled error:', err);
    json(res, 500, { error: message });
  }
});

server.listen(PORT, () => {
  console.log(
    `agent-service: listening on :${PORT} (REPO_ROOT=${process.env.REPO_ROOT ?? '(auto)'})`,
  );
});
