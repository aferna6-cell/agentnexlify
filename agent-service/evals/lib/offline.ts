/**
 * Offline determinism switch. Import FIRST from eval CLI entrypoints only.
 *
 * Deleting the key makes classify() take classifyHeuristic and drafts use the
 * local composer. Lives here, not in scoring, so tests can import predicates
 * without mutating the environment.
 */
export function goOffline(): void {
  delete process.env.ANTHROPIC_API_KEY;
  delete process.env.AGENT_OS_DRAFTS_DISABLED;
}

export function assertOffline(): void {
  if (process.env.ANTHROPIC_API_KEY) {
    throw new Error(
      "goOffline() must be called before the orchestrator is imported",
    );
  }
}
