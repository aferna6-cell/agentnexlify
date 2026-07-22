'use strict';

// AgentNexLiFy Zapier integration app definition (#61).
// Structure per zapier-platform-core: authentication + a single polling trigger
// (new_lead). External submission steps (validate/test/push/promote, dev
// account, logo, beta) are owner actions — see README.md.

const authentication = require('./authentication');
const newLeadTrigger = require('./triggers/new_lead');

// Attach the tenant's API key to every outgoing request as X-API-Key. The
// endpoint resolves the key to a client_id and enforces the tier gate.
const addApiKeyHeader = (request, z, bundle) => {
  if (bundle.authData && bundle.authData.api_key) {
    request.headers = request.headers || {};
    request.headers['X-API-Key'] = bundle.authData.api_key;
  }
  return request;
};

module.exports = {
  version: require('./package.json').version,
  platformVersion: require('zapier-platform-core').version,

  authentication,
  beforeRequest: [addApiKeyHeader],

  triggers: {
    [newLeadTrigger.key]: newLeadTrigger,
  },

  searches: {},
  creates: {},
  resources: {},
};
