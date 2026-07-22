/**
 * Agent OS API functions - P0.
 *
 * All endpoints derive client_id from the JWT, so no tenant id is passed
 * in the path. Just the bearer token.
 */
import { BASE, request } from "./_client";

// --- Threads + the orchestration flow ---

export function listOsThreads(token) {
  return request("/api/v1/os/threads", { token });
}

export function createOsThread(token, title) {
  return request("/api/v1/os/threads", {
    method: "POST",
    token,
    body: { title: title || "New conversation" },
  });
}

export function fetchOsThreadMessages(token, threadId) {
  return request(`/api/v1/os/threads/${threadId}/messages`, { token });
}

export function postOsMessage(token, threadId, content) {
  return request(`/api/v1/os/threads/${threadId}/messages`, {
    method: "POST",
    token,
    body: { content },
  });
}

// Orchestrate one turn through the Agent OS engine (the vendored demo
// framework). Inserts the user message, runs the engine over the tenant's
// SharedContext, and persists the result. Returns
// { user_message, assistant_message, agent_run, status, agent_id }.
export function orchestrateOsTurn(token, threadId, content, forceAgentId) {
  const body = { thread_id: threadId, content };
  if (forceAgentId) body.force_agent_id = forceAgentId;
  return request("/api/v1/os/orchestrate", { method: "POST", token, body });
}

// --- Agent runs ---

export function fetchOsAgentRun(token, runId) {
  return request(`/api/v1/os/agent-runs/${runId}`, { token });
}

export function reportOsRunBug(token, runId) {
  return request(`/api/v1/os/agent-runs/${runId}/report-bug`, {
    method: "POST",
    token,
  });
}

// --- Deliverables ---

export function editOsDeliverable(token, runId, { title, body, recipient }) {
  return request(`/api/v1/os/deliverables/${runId}`, {
    method: "PATCH",
    token,
    body: { title, body, recipient },
  });
}

export function approveOsDeliverable(token, runId) {
  return request(`/api/v1/os/deliverables/${runId}/approve`, {
    method: "POST",
    token,
  });
}

export function rejectOsDeliverable(token, runId) {
  return request(`/api/v1/os/deliverables/${runId}/reject`, {
    method: "POST",
    token,
  });
}

export function fetchOsPendingDeliverables(token) {
  return request("/api/v1/os/deliverables/pending", { token });
}

// Poll one action run to learn whether the real send (SMS/email/widget)
// actually succeeded. Approval schedules the send as a background task, so
// deliverable_status flips to "approved" before the send resolves; the true
// outcome lives on os_action_runs.status (queued|running|succeeded|failed).
export function getOsActionRun(token, actionRunId) {
  return request(`/api/v1/os/action-runs/${actionRunId}`, { token });
}

// Owner-only: retry a failed action run. Creates a fresh os_action_runs row
// and returns it (status "queued") so the caller can resume polling. Pass
// { recipient } to fix a send that failed with "missing recipient" - the
// backend writes it onto the deliverable before requeueing.
export function retryOsActionRun(token, actionRunId, { recipient } = {}) {
  return request(`/api/v1/os/action-runs/${actionRunId}/retry`, {
    method: "POST",
    token,
    body: recipient ? { recipient } : undefined,
  });
}

// --- Memory ---

export function listOsMemory(token) {
  return request("/api/v1/os/memory", { token });
}

export function createOsMemory(token, { content, kind }) {
  return request("/api/v1/os/memory", {
    method: "POST",
    token,
    body: { content, kind: kind || "fact" },
  });
}

export function rememberOsFact(token, content) {
  return request("/api/v1/os/memory/remember", {
    method: "POST",
    token,
    body: { content },
  });
}

export function updateOsMemory(token, memoryId, patch) {
  return request(`/api/v1/os/memory/${memoryId}`, {
    method: "PATCH",
    token,
    body: patch,
  });
}

export function deleteOsMemory(token, memoryId) {
  return request(`/api/v1/os/memory/${memoryId}`, {
    method: "DELETE",
    token,
  });
}

// --- Backlog ---

export function listOsBacklog(token) {
  return request("/api/v1/os/backlog", { token });
}

export function decideOsBacklog(token, requestId, { decision, note }) {
  return request(`/api/v1/os/backlog/${requestId}/decision`, {
    method: "POST",
    token,
    body: { decision, note: note || "" },
  });
}

// --- Usage ---

export function fetchOsUsage(token) {
  return request("/api/v1/os/usage", { token });
}

// --- Knowledge graph (long-term memory) ---

export function fetchOsGraph(token) {
  return request("/api/v1/os/graph", { token });
}

export function forgetOsGraphNode(token, nodeId) {
  return request(`/api/v1/os/graph/nodes/${nodeId}`, {
    method: "DELETE",
    token,
  });
}

// --- Enterprise-audit surfaces (trace, usage breakdown, instructions) ---

export function fetchOsRunTrace(token, runId) {
  return request(`/api/v1/os/agent-runs/${runId}/trace`, { token });
}

export function fetchOsUsageBreakdown(token) {
  return request("/api/v1/os/usage/breakdown", { token });
}

export function fetchOsInstructions(token) {
  return request("/api/v1/os/instructions", { token });
}

export function putOsInstruction(token, department, text) {
  return request(`/api/v1/os/instructions/${department}`, {
    method: "PUT",
    token,
    body: { text },
  });
}

// --- Scheduled tasks (recurring department prompts) ---

export function listOsTasks(token) {
  return request("/api/v1/os/tasks", { token });
}

export function createOsTask(token, { department, prompt, interval_days, enabled }) {
  return request("/api/v1/os/tasks", {
    method: "POST",
    token,
    body: { department, prompt, interval_days, enabled },
  });
}

export function updateOsTask(token, taskId, fields) {
  return request(`/api/v1/os/tasks/${taskId}`, {
    method: "PATCH",
    token,
    body: fields,
  });
}

export function deleteOsTask(token, taskId) {
  return request(`/api/v1/os/tasks/${taskId}`, { method: "DELETE", token });
}

// --- Ask your business (deterministic data answers) ---

export function askBusinessData(token, question) {
  return request("/api/v1/os/ask-data", {
    method: "POST",
    token,
    body: { question },
  });
}

export function fetchAskDataSupported(token) {
  return request("/api/v1/os/ask-data/supported", { token });
}

// --- Multi-department projects ---

export function listOsProjects(token) {
  return request("/api/v1/os/projects", { token });
}

export function createOsProject(token, ask) {
  return request("/api/v1/os/projects", { method: "POST", token, body: { ask } });
}

export function fetchOsProject(token, projectId) {
  return request(`/api/v1/os/projects/${projectId}`, { token });
}

export function approveOsProject(token, projectId) {
  return request(`/api/v1/os/projects/${projectId}/approve`, {
    method: "POST",
    token,
  });
}

export function cancelOsProject(token, projectId) {
  return request(`/api/v1/os/projects/${projectId}/cancel`, {
    method: "POST",
    token,
  });
}

export function fetchOsTaskSuggestions(token) {
  return request("/api/v1/os/tasks/suggestions", { token });
}

// --- Deep research (propose-only briefs from owned sources) ---

export function runOsResearch(token, topic, urls) {
  const body = { topic };
  if (urls && urls.length > 0) body.urls = urls;
  return request("/api/v1/os/research", { method: "POST", token, body });
}

// Seed a multi-department project from a research brief's findings. Returns
// { project, steps } - the project parks as an approvable draft plan.
export function createProjectFromResearch(token, runId) {
  return request(`/api/v1/os/research/${runId}/to-project`, {
    method: "POST",
    token,
  });
}

// --- Insights + composer attachments ---

export function fetchOsInsights(token) {
  return request("/api/v1/os/insights", { token });
}

// Multipart upload - FormData can't ride the JSON request() helper, but the
// fetch still belongs in this layer. Returns {ok, status, body} so the
// composer keeps its friendly per-status error copy instead of thrown text.
export async function uploadOsAttachment(token, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/v1/os/uploads`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

export async function generateOsImage(token, prompt) {
  const res = await fetch(`${BASE}/api/v1/os/images/generate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt }),
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}
