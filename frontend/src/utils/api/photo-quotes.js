/**
 * Photo-quote dashboard API (#42).
 */
import { request } from "./_client";

export function fetchPhotoQuotes(
  tenantId,
  token,
  { needsHuman, startDate, endDate, limit } = {},
) {
  const params = new URLSearchParams();
  if (needsHuman != null) params.set("needs_human", String(needsHuman));
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString();
  return request(`/api/photo-quotes/${tenantId}${qs ? `?${qs}` : ""}`, {
    token,
  });
}

export function submitQuoteFeedback(tenantId, token, quoteId, feedback) {
  return request(`/api/photo-quotes/${tenantId}/feedback`, {
    method: "POST",
    token,
    body: { quote_id: quoteId, feedback },
  });
}
