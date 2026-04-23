const getFallbackRealLeads = async (z, bundle) => {
  const since = bundle.meta.isLoadingSample
    ? new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
    : bundle.meta.lastPolledAt ||
      new Date(Date.now() - 60 * 1000).toISOString();

  const response = await z.request({
    url: "https://api.agentnexlify.com/api/zapier/leads/new",
    method: "GET",
    headers: { "X-API-Key": "{{bundle.authData.api_key}}" },
    params: { since, limit: 100 },
  });

  return response.data.results || [];
};

module.exports = {
  key: "new_lead",
  noun: "Lead",
  display: {
    label: "New Lead",
    description:
      "Triggers when a new lead is captured by your AgentNexLiFy widget.",
  },
  operation: {
    type: "polling",
    perform: getFallbackRealLeads,
    sample: {
      id: "sample-uuid",
      client_id: "tenant-uuid",
      name: "Jane Smith",
      email: "jane@example.com",
      phone: "555-867-5309",
      areas_of_interest: "Drain Cleaning;Leak Repair",
      status: "new",
      created_at: new Date().toISOString(),
    },
  },
};
