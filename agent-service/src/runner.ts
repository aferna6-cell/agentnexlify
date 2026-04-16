/**
 * Thin wrapper around @anthropic-ai/claude-agent-sdk query().
 *
 * settingSources: ['project'] + cwd: REPO_ROOT causes the SDK to load
 * .claude/agents/<name>.md as the agent definition, so dev config and
 * prod config are the same files.
 *
 * REPO_ROOT is read from the REPO_ROOT env var (set in Dockerfile) and
 * falls back to two levels above this file (correct for local dev where
 * the directory layout is: repo-root/agent-service/src/runner.ts).
 */

import { query, type SDKResultSuccess } from '@anthropic-ai/claude-agent-sdk';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT =
  process.env.REPO_ROOT ??
  join(dirname(fileURLToPath(import.meta.url)), '..', '..');

export type RunResult =
  | { is_error: false; result: string; cost_usd: number; turns: number }
  | { is_error: true; error: string; cost_usd: number; turns: number };

/**
 * Run a named agent from .claude/agents/<name>.md and return its final result.
 *
 * @param agentName - must match the `name:` field in a .claude/agents/*.md file
 * @param prompt    - user message sent as the kickoff prompt
 * @param timeoutMs - hard wall-clock deadline; returns is_error: true on breach
 */
export async function runAgent(
  agentName: string,
  prompt: string,
  timeoutMs = 30_000,
): Promise<RunResult> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);

  try {
    const q = query({
      prompt,
      options: {
        abortController: ac,
        // Load .claude/agents/<name>.md + CLAUDE.md from the repo root.
        settingSources: ['project'],
        cwd: REPO_ROOT,
        // Use this agent definition as the main thread agent.
        agent: agentName,
        // Headless: deny any unexpected permission prompts instead of hanging.
        permissionMode: 'dontAsk',
      },
    });

    for await (const msg of q) {
      if (msg.type !== 'result') continue;

      clearTimeout(timer);

      if (msg.subtype === 'success') {
        const ok = msg as SDKResultSuccess;
        return {
          is_error: false,
          result: ok.result,
          cost_usd: ok.total_cost_usd,
          turns: ok.num_turns,
        };
      }

      // error_during_execution | error_max_turns | error_max_budget_usd
      return {
        is_error: true,
        error: msg.subtype,
        cost_usd: msg.total_cost_usd,
        turns: msg.num_turns,
      };
    }

    // Stream ended without a result message — shouldn't happen in practice.
    return { is_error: true, error: 'stream_ended_without_result', cost_usd: 0, turns: 0 };
  } catch (err: unknown) {
    clearTimeout(timer);
    const isAbort =
      ac.signal.aborted ||
      (err instanceof Error && (err.name === 'AbortError' || err.message.includes('abort')));
    if (isAbort) {
      return { is_error: true, error: 'timeout', cost_usd: 0, turns: 0 };
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
