/**
 * leadTemperature(score) - maps a numeric lead or qualifier score to
 * a human-readable temperature label for owner-facing UI.
 *
 * Accepts two scales:
 *   0-10  (rule-based qualifier score)
 *   0-100 (full lead score)
 *
 * Normalizes to 0-1 before bucketing so both scales produce the same result.
 */

export function leadTemperature(score) {
  if (score === null || score === undefined || isNaN(Number(score))) {
    return { emoji: "", label: "New", tone: "new" };
  }

  const n = Number(score);

  // Detect scale: if score <= 10 treat as out-of-10, else out-of-100.
  const normalized = n <= 10 ? n / 10 : n / 100;

  if (normalized >= 0.75) {
    return { emoji: "🔥", label: "Ready to book", tone: "hot" };
  }
  if (normalized >= 0.45) {
    return { emoji: "👀", label: "Just looking", tone: "warm" };
  }
  if (normalized > 0) {
    return { emoji: "❄️", label: "Cold", tone: "cold" };
  }

  // score is exactly 0 (or normalized to 0)
  return { emoji: "", label: "New", tone: "new" };
}
