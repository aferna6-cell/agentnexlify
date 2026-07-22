'use strict';

// new_lead polling trigger (#61, spec Zapier app AC). Zapier calls `perform`
// once a minute per active Zap; it de-duplicates the returned rows on `id` and
// fires the Zap for each previously-unseen lead. The endpoint returns the flat
// v1 schema from backend/routers/zapier.py (GET /api/zapier/leads/new).

const { BASE_URL, LOOKBACK_MS, PAGE_LIMIT } = require('../constants');

const perform = async (z, bundle) => {
  // Rolling recent window; Zapier's id-dedup makes this fire once per new lead.
  // Date is evaluated per poll so the window stays current without a stored
  // cursor. (bundle.meta.isLoadingSample uses the same path — sample below.)
  const since = new Date(Date.now() - LOOKBACK_MS).toISOString();
  const response = await z.request({
    url: `${BASE_URL}/api/zapier/leads/new`,
    params: { since, limit: PAGE_LIMIT },
  });
  // z.request parses JSON into response.data; the endpoint returns an array.
  return response.data || [];
};

module.exports = {
  key: 'new_lead',
  noun: 'Lead',
  display: {
    label: 'New Lead',
    description:
      'Triggers when a new lead arrives in AgentNexLiFy. Send it to Jobber, ' +
      'ServiceTitan, Housecall Pro, HubSpot, or any CRM Zapier connects to.',
  },
  operation: {
    type: 'polling',
    perform,
    // Sample shown in the Zap editor and used for field mapping when no live
    // lead is available. Matches the flat v1 schema exactly.
    sample: {
      id: '11111111-2222-3333-4444-555555555555',
      client_id: '00000000-0000-0000-0000-000000000001',
      name: 'Jane Contractor',
      email: 'jane@example.com',
      phone: '+15551234567',
      areas_of_interest: 'plumbing;emergency',
      status: 'new',
      created_at: '2026-07-22T12:00:00Z',
    },
    // Explicit output field types so Zapier renders the mapper correctly.
    outputFields: [
      { key: 'id', label: 'Lead ID', type: 'string' },
      { key: 'client_id', label: 'Tenant ID', type: 'string' },
      { key: 'name', label: 'Name', type: 'string' },
      { key: 'email', label: 'Email', type: 'string' },
      { key: 'phone', label: 'Phone', type: 'string' },
      {
        key: 'areas_of_interest',
        label: 'Areas of Interest',
        type: 'string',
        helpText: 'Semicolon-joined list, e.g. "plumbing;emergency".',
      },
      { key: 'status', label: 'Status', type: 'string' },
      { key: 'created_at', label: 'Created At', type: 'datetime' },
    ],
  },
};
