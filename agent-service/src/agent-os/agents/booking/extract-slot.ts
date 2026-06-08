/**
 * Extract a human "day + time" slot from free-text owner instructions when the
 * orchestrator didn't pre-fill offered_slot / requested_day.
 *
 * Deterministic regex, not an LLM call — the booking agent only needs to echo
 * the slot the owner already named (e.g. "...Thursday at 10:30 AM..." →
 * "Thursday at 10:30 AM"). Returns undefined when no day or time is present, so
 * the agent keeps its honest "ask for availability" fallback.
 */

const DAY_WORDS: Record<string, string> = {
  today: "today",
  tomorrow: "tomorrow",
  mon: "Monday", monday: "Monday",
  tue: "Tuesday", tues: "Tuesday", tuesday: "Tuesday",
  wed: "Wednesday", weds: "Wednesday", wednesday: "Wednesday",
  thu: "Thursday", thur: "Thursday", thurs: "Thursday", thursday: "Thursday",
  fri: "Friday", friday: "Friday",
  sat: "Saturday", saturday: "Saturday",
  sun: "Sunday", sunday: "Sunday",
};

const DAY_RE =
  /\b(today|tomorrow|mondays?|tuesdays?|tues|wednesdays?|weds?|thursdays?|thurs?|thu|fridays?|sat(?:urday)?s?|sun(?:day)?s?|mon|tue|fri)\b/i;
const TIME_RE =
  /\b(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)|\d{1,2}:\d{2}|noon|midnight)\b/i;

function normalizeDay(raw: string): string | undefined {
  const key = raw.toLowerCase().replace(/s$/, "");
  return DAY_WORDS[key] ?? DAY_WORDS[raw.toLowerCase()];
}

function normalizeTime(raw: string): string {
  // Uppercase the am/pm marker and collapse spacing: "10:30 am" -> "10:30 AM".
  return raw
    .trim()
    .replace(/\s+/g, " ")
    .replace(/a\.?m\.?/i, "AM")
    .replace(/p\.?m\.?/i, "PM");
}

/** Return a slot phrase like "Thursday at 10:30 AM", or undefined if none. */
export function extractSlot(text: string | undefined): string | undefined {
  if (!text) return undefined;
  const dayMatch = text.match(DAY_RE);
  const timeMatch = text.match(TIME_RE);
  const day = dayMatch ? normalizeDay(dayMatch[1]) : undefined;
  const time = timeMatch ? normalizeTime(timeMatch[1]) : undefined;

  if (day && time) return `${day} at ${time}`;
  if (day) return day;
  if (time) return time;
  return undefined;
}
