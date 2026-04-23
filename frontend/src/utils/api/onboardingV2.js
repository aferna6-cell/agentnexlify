const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const BASE = "/api/v1/onboarding/v2";

async function apiFetch(path, { token, method = "POST", body, signal } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err.detail || err.message || `Request failed: ${res.status}`,
    );
  }
  return res.json();
}

export function startWizard(token, vertical) {
  return apiFetch(`${BASE}/start`, { token, body: { vertical } });
}

export function saveStep(token, stepNum, fieldUpdates) {
  return apiFetch(`${BASE}/step/${stepNum}`, { token, body: fieldUpdates });
}

export function completeWizard(token) {
  return apiFetch(`${BASE}/complete`, { token });
}

export function autoKb(token, websiteUrl, signal) {
  return apiFetch(`${BASE}/auto-kb`, {
    token,
    body: { url: websiteUrl },
    signal,
  });
}

export function getPreset(token, vertical) {
  return apiFetch(`${BASE}/preset/${vertical}`, { token });
}

export function getReadiness(token) {
  return apiFetch(`${BASE}/readiness`, { token, method: "GET" });
}

export function bulkImportFaqs(token, text) {
  return apiFetch(`${BASE}/faqs/bulk`, { token, body: { text } });
}

export function saveHours(token, timezone, hours) {
  return apiFetch(`${BASE}/hours`, { token, body: { timezone, hours } });
}

export function getWidgetHealth(token, domain) {
  return apiFetch(
    `${API_BASE}/api/v1/widget/health?domain=${encodeURIComponent(domain)}`,
    { token, method: "GET" },
  );
}
