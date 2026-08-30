/**
 * RAG_ENABLED defaults OFF. Same fail-closed pattern as SEND_EMAIL_ENABLED.
 */

import { envFlagEnabled } from "../actions/flags.ts";

export const RAG_FLAG = "RAG_ENABLED";

export function ragEnabled(): boolean {
  return envFlagEnabled(RAG_FLAG, false);
}
