'use strict';

// API-key authentication (#61, spec Resolved Q2 C — API key for v1; OAuth is
// v1.1, issue #63). The tenant generates a key in the AgentNexLiFy dashboard
// (Settings -> Integrations -> Zapier), shown once, and pastes it here. The key
// is sent on every request as the X-API-Key header (see beforeRequest in
// index.js).

const { BASE_URL } = require('./constants');

// Auth test: hit the leads endpoint with an epoch `since` and limit 1. A valid
// key returns 200 with a (possibly empty) array; an invalid/revoked key returns
// 401; a Free/cancelled tenant returns 402. Zapier treats a non-2xx as a failed
// connection and surfaces the endpoint's detail message to the tenant.
const test = (z, bundle) =>
  z.request({
    url: `${BASE_URL}/api/zapier/leads/new`,
    params: { since: '1970-01-01T00:00:00Z', limit: 1 },
  });

module.exports = {
  type: 'custom',
  fields: [
    {
      key: 'api_key',
      label: 'API Key',
      type: 'string',
      required: true,
      helpText:
        'Generate in AgentNexLiFy: Settings -> Integrations -> Zapier -> ' +
        'Generate API key. The key is shown only once, so copy it before ' +
        'closing the dialog.',
    },
  ],
  test,
  // Shown on the connected-account label in the Zap editor.
  connectionLabel: 'AgentNexLiFy',
};
