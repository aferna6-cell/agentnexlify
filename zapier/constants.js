'use strict';

// Base URL of the AgentNexLiFy backend that serves the Zapier polling endpoint.
// Overridable via env for staging/local testing; defaults to production Railway.
const BASE_URL =
  process.env.AGENTNEXLIFY_BASE_URL ||
  'https://agentnexlify-production.up.railway.app';

// Polling trigger lookback: the endpoint returns leads created after `since`,
// oldest-first, capped at `limit`. Zapier de-duplicates on the lead `id`, so a
// rolling recent window plus id-dedup reliably fires once per new lead without
// re-importing history. 30 days comfortably covers the 1/min poll cadence at
// realistic small-business lead volume. An exact server-side cursor is the
// optional #59 follow-up (v2 endpoint).
const LOOKBACK_MS = 30 * 24 * 60 * 60 * 1000;
const PAGE_LIMIT = 50;

module.exports = { BASE_URL, LOOKBACK_MS, PAGE_LIMIT };
