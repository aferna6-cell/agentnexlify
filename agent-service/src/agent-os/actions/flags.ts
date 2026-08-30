/**
 * Process env flags for the action layer. Defaults are fail-closed.
 *
 * Canonical capability lists live in ../capabilities/send_email.ts so
 * department resolvers can read them without crossing the action boundary.
 * Policy still imports from here.
 */

export {
  SEND_EMAIL_FLAG,
  SALES_DEPARTMENT,
  SEND_EMAIL_TOOL_ID,
  SEND_EMAIL_PROPOSE_DEPARTMENTS,
  SEND_EMAIL_CANDIDATE_DEPARTMENTS,
  envFlagEnabled,
  sendEmailEnabled,
  canProposeSendEmail,
} from "../capabilities/send_email.ts";
