/**
 * Eval-only send-boundary guards.
 *
 * Production attach rule this runner must never hit:
 *   SEND_EMAIL_ENABLED=1 and port is None → live mailbox port.
 *
 * This module never sets SEND_EMAIL_ENABLED, never leaves the port None,
 * and never imports a production send port.
 */

import { FakeGmailPort } from "./fake-gmail-port.ts";
import { LiveOsToolExecutionAbort } from "./live-db-lock.ts";

export function sendEmailFlagOn(env: NodeJS.ProcessEnv = process.env): boolean {
  const raw = env.SEND_EMAIL_ENABLED;
  if (typeof raw !== "string") return false;
  const v = raw.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

/**
 * Fail-closed before any send_email executeAction.
 *
 * flag-on + port is None is an abort even if this process would otherwise
 * continue — that pair is the live Gmail attach path.
 */
export function assertSendEmailEvalSafe(
  env: NodeJS.ProcessEnv = process.env,
  port: unknown,
): void {
  const flag = sendEmailFlagOn(env);
  if (flag && port == null) {
    throw new LiveOsToolExecutionAbort(
      "SEND_EMAIL_ENABLED is on and gmail port is None — live Gmail attach path",
    );
  }
  if (flag) {
    throw new LiveOsToolExecutionAbort(
      "SEND_EMAIL_ENABLED is set — this eval runner never enables live send",
    );
  }
  if (port == null) {
    throw new LiveOsToolExecutionAbort(
      "gmail port is None — FakeGmailPort must be injected on every send_email call",
    );
  }
  if (!(port instanceof FakeGmailPort) || port.durable !== false) {
    throw new LiveOsToolExecutionAbort(
      "gmail port is not FakeGmailPort — refusing any other send boundary",
    );
  }
}
