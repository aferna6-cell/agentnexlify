module.exports = {
  type: "custom",
  fields: [
    {
      key: "api_key",
      label: "API Key",
      required: true,
      type: "password",
      helpText:
        "Generate from AgentNexLiFy Dashboard → Integrations → ⚡ Zapier API Keys",
    },
  ],
  test: {
    url: "https://api.agentnexlify.com/api/zapier/leads/new",
    method: "GET",
    headers: { "X-API-Key": "{{bundle.authData.api_key}}" },
    params: { limit: 1 },
  },
  connectionLabel: "AgentNexLiFy ({{bundle.authData.api_key.slice(0,12)}}...)",
};
