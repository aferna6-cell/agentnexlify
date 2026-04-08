export function apiErrorMessage(status, body = {}) {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        const location = Array.isArray(item?.loc) ? item.loc.join(".") : item?.loc;
        const message = item?.msg || item?.message || JSON.stringify(item);
        return location ? `${location}: ${message}` : message;
      })
      .join("; ");
  }
  if (typeof body?.message === "string" && body.message.trim()) return body.message;
  if (status === 0) return "Network error. Check your connection and try again.";
  return `API error ${status}`;
}

export function reportError(error, context = {}) {
  const normalizedError = error instanceof Error ? error : new Error(String(error));
  const sentry = globalThis.window?.Sentry || globalThis.Sentry;

  if (sentry?.captureException) {
    sentry.captureException(normalizedError, { extra: context });
    return;
  }

  // Keep this centralized so adding Sentry later only changes one file.
  console.error("Frontend error", normalizedError, context);
}
