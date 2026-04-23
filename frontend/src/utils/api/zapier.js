import { request } from "./_client";

export const listZapierKeys = (token) =>
  request("/api/zapier/keys", { method: "GET", token });

export const generateZapierKey = (name, token) =>
  request("/api/zapier/keys", {
    method: "POST",
    token,
    body: JSON.stringify({ name }),
  });

export const revokeZapierKey = (keyId, token) =>
  request(`/api/zapier/keys/${keyId}`, { method: "DELETE", token });
