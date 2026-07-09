/**
 * Referral API functions.
 *   GET /api/v1/referral/my-stats
 *   → { ref_code, share_link, total_clicks, clicks_last_7d, clicks_last_30d,
 *       referred_signups, rewards_count, rewards_earned_cents }
 */
import { request } from "./_client";

export function fetchReferralStats(token) {
  return request("/api/v1/referral/my-stats", { token });
}
