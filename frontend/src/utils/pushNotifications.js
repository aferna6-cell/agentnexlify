/**
 * Web Push registration + subscription for pending-approval notifications.
 *
 * Degrades gracefully: fetchVapidPublicKey() returns null when the backend
 * has no VAPID keys configured (endpoint 404s) - callers hide the UI.
 * No localStorage - the Push API itself owns subscription state.
 */

import { request, ApiError } from "./api/_client";

export function pushSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** Public VAPID key, or null when push is not configured server-side. */
export async function fetchVapidPublicKey() {
  try {
    const data = await request("/api/v1/push/vapid-public-key");
    return data?.public_key || null;
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function registerServiceWorker() {
  return navigator.serviceWorker.register("/sw.js");
}

/** Current subscription if the browser already holds one, else null. */
export async function getExistingSubscription() {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration("/sw.js");
  if (!registration) return null;
  return registration.pushManager.getSubscription();
}

/**
 * Ask permission, subscribe the browser, and store the subscription on the
 * backend. Throws Error("permission-denied") when the user blocks.
 */
export async function enablePushNotifications(tenantId, token, publicKey) {
  if (!pushSupported()) throw new Error("unsupported");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("permission-denied");

  const registration = await registerServiceWorker();
  await navigator.serviceWorker.ready;

  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  const json = subscription.toJSON();
  await request(`/api/v1/push/${tenantId}/subscribe`, {
    method: "POST",
    token,
    body: { endpoint: json.endpoint, keys: json.keys },
  });
  return subscription;
}

/** Unsubscribe the browser and remove the subscription from the backend. */
export async function disablePushNotifications(tenantId, token) {
  const subscription = await getExistingSubscription();
  if (!subscription) return;
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  await request(`/api/v1/push/${tenantId}/unsubscribe`, {
    method: "POST",
    token,
    body: { endpoint },
  });
}
