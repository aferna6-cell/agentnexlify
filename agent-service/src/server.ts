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
