import { STORAGE_KEY_PREFIX } from "./constants";

export function getStoredState(tenantId) {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${tenantId}`);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function setStoredState(tenantId, state) {
  localStorage.setItem(
    `${STORAGE_KEY_PREFIX}${tenantId}`,
    JSON.stringify(state),
  );
}
