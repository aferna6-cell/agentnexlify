/**
 * Agent OS API functions — P0.
 *
 * All endpoints derive client_id from the JWT, so no tenant id is passed
 * in the path. Just the bearer token.
 */
import { request } from "./_client";

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

export function editOsDeliverable(token, runId, { title, body }) {
  return request(`/api/v1/os/deliverables/${runId}`, {
    method: "PATCH",
    token,
    body: { title, body },
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
