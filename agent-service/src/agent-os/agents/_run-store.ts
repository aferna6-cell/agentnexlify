/**
 * RunStore wiring for the agent-service runtime.
 *
 * The orchestrator imports this module for the side effect that, in the
 * standalone, registers PrismaRunStore. In the agent-service the RunStore is
 * registered explicitly at startup (an HTTP store that persists into the
 * FastAPI/Supabase `os_*` data plane), so this module intentionally registers
 * nothing. Kept so the vendored orchestrator's `import "./_run-store.ts"`
 * resolves unchanged.
 */

export {};
