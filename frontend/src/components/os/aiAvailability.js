/**
 * The chat should say when a reply was not produced by live AI.
 * This reads signals the engine already returns. It does not decide
 * whether the model is up.
 */

const OFFLINE_TEXT = [
  "offline mode",
  "real ai generation is currently unavailable",
  "agent engine is temporarily unavailable",
];

export function aiGenerationUnavailable(messages, runs) {
  const list = Array.isArray(messages) ? messages : [];
  const assistant = [...list]
    .reverse()
    .find(
      (message) => message?.role === "assistant" || message?.role === "agent",
    );
  const text = (assistant?.content || "").toLowerCase();
  if (OFFLINE_TEXT.some((phrase) => text.includes(phrase))) return true;
  const runList = Array.isArray(runs) ? runs : [];
  const run = runList.find(
    (item) => item?.id && item.id === assistant?.agent_run_id,
  );
  const source = run?.deliverable?.metadata?.source;
  return source === "local";
}
