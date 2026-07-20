/**
 * Golden-question eval API (enterprise-audit item 2).
 *
 * Owner-managed regression suite for the widget bot's grounding: questions
 * customers ask + phrases the compiled knowledge must contain. Runs are
 * deterministic server-side.
 */
import { request } from "./_client";

export function listEvalQuestions(token) {
  return request("/api/v1/kb-evals/questions", { token });
}

export function createEvalQuestion(token, { question, expected_phrases }) {
  return request("/api/v1/kb-evals/questions", {
    method: "POST",
    token,
    body: { question, expected_phrases },
  });
}

export function deleteEvalQuestion(token, questionId) {
  return request(`/api/v1/kb-evals/questions/${questionId}`, {
    method: "DELETE",
    token,
  });
}

export function runEvals(token) {
  return request("/api/v1/kb-evals/run", { method: "POST", token });
}

export function fetchLatestEvalRun(token) {
  return request("/api/v1/kb-evals/runs/latest", { token });
}
