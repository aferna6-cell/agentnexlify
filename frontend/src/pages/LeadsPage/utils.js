export function formatDate(dateStr) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function scoreClass(score) {
  if (score >= 70) return "score-hot";
  if (score >= 40) return "score-warm";
  return "score-cold";
}

export function scoreLabel(score) {
  if (score >= 70) return "Hot";
  if (score >= 40) return "Warm";
  return "Cold";
}
