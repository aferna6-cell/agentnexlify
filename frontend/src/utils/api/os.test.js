import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./_client", () => ({
  request: vi.fn(),
}));

import { request } from "./_client";
import {
  listOsThreads,
  createOsThread,
  fetchOsThreadMessages,
  postOsMessage,
  orchestrateOsTurn,
  fetchOsAgentRun,
  reportOsRunBug,
  editOsDeliverable,
  approveOsDeliverable,
  rejectOsDeliverable,
  listOsMemory,
  createOsMemory,
  rememberOsFact,
  updateOsMemory,
  deleteOsMemory,
  listOsBacklog,
  decideOsBacklog,
  fetchOsUsage,
} from "./os";

const TOKEN = "jwt-token";

// Sentinel the mocked transport resolves with. Each wrapper is a thin pass
// through, so asserting identity (toBe) proves it returns the transport
// result unchanged - not just that the transport was called.
const API_RESPONSE = { ok: true };

beforeEach(() => {
  request.mockReset();
  request.mockResolvedValue(API_RESPONSE);
});

describe("os threads api", () => {
  it("listOsThreads issues a GET with token", async () => {
    const result = await listOsThreads(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("createOsThread posts the given title", async () => {
    const result = await createOsThread(TOKEN, "Plan launch");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      method: "POST",
      token: TOKEN,
      body: { title: "Plan launch" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("createOsThread falls back to a default title", async () => {
    const result = await createOsThread(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      method: "POST",
      token: TOKEN,
      body: { title: "New conversation" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("fetchOsThreadMessages targets the thread path", async () => {
    const result = await fetchOsThreadMessages(TOKEN, "t1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads/t1/messages", {
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("postOsMessage posts content to the thread", async () => {
    const result = await postOsMessage(TOKEN, "t1", "do the thing");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads/t1/messages", {
      method: "POST",
      token: TOKEN,
      body: { content: "do the thing" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("orchestrateOsTurn posts thread_id + content to the engine", async () => {
    const result = await orchestrateOsTurn(TOKEN, "t1", "draft a quote");
    expect(request).toHaveBeenCalledWith("/api/v1/os/orchestrate", {
      method: "POST",
      token: TOKEN,
      body: { thread_id: "t1", content: "draft a quote" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("orchestrateOsTurn includes force_agent_id when given", async () => {
    const result = await orchestrateOsTurn(TOKEN, "t1", "draft a quote", "sales");
    expect(request).toHaveBeenCalledWith("/api/v1/os/orchestrate", {
      method: "POST",
      token: TOKEN,
      body: { thread_id: "t1", content: "draft a quote", force_agent_id: "sales" },
    });
    expect(result).toBe(API_RESPONSE);
  });
});

describe("os agent runs api", () => {
  it("fetchOsAgentRun targets the run path", async () => {
    const result = await fetchOsAgentRun(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/agent-runs/r1", {
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("reportOsRunBug posts to the report-bug path", async () => {
    const result = await reportOsRunBug(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith(
      "/api/v1/os/agent-runs/r1/report-bug",
      {
        method: "POST",
        token: TOKEN,
      },
    );
    expect(result).toBe(API_RESPONSE);
  });
});

describe("os deliverables api", () => {
  it("editOsDeliverable patches title and body", async () => {
    const result = await editOsDeliverable(TOKEN, "r1", {
      title: "T",
      body: "B",
    });
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1", {
      method: "PATCH",
      token: TOKEN,
      body: { title: "T", body: "B" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("approveOsDeliverable posts to the approve path", async () => {
    const result = await approveOsDeliverable(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1/approve", {
      method: "POST",
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("rejectOsDeliverable posts to the reject path", async () => {
    const result = await rejectOsDeliverable(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1/reject", {
      method: "POST",
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });
});

describe("os memory api", () => {
  it("listOsMemory issues a GET", async () => {
    const result = await listOsMemory(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", { token: TOKEN });
    expect(result).toBe(API_RESPONSE);
  });

  it("createOsMemory posts content with explicit kind", async () => {
    const result = await createOsMemory(TOKEN, {
      content: "c",
      kind: "preference",
    });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", {
      method: "POST",
      token: TOKEN,
      body: { content: "c", kind: "preference" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("createOsMemory defaults kind to fact", async () => {
    const result = await createOsMemory(TOKEN, { content: "c" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", {
      method: "POST",
      token: TOKEN,
      body: { content: "c", kind: "fact" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("rememberOsFact posts to the remember path", async () => {
    const result = await rememberOsFact(TOKEN, "we ship Fridays");
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/remember", {
      method: "POST",
      token: TOKEN,
      body: { content: "we ship Fridays" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("updateOsMemory patches the memory row", async () => {
    const result = await updateOsMemory(TOKEN, "m1", { content: "new" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/m1", {
      method: "PATCH",
      token: TOKEN,
      body: { content: "new" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("deleteOsMemory deletes the memory row", async () => {
    const result = await deleteOsMemory(TOKEN, "m1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/m1", {
      method: "DELETE",
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });
});

describe("os backlog api", () => {
  it("listOsBacklog issues a GET", async () => {
    const result = await listOsBacklog(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog", {
      token: TOKEN,
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("decideOsBacklog posts decision and note", async () => {
    const result = await decideOsBacklog(TOKEN, "req1", {
      decision: "approve",
      note: "go",
    });
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog/req1/decision", {
      method: "POST",
      token: TOKEN,
      body: { decision: "approve", note: "go" },
    });
    expect(result).toBe(API_RESPONSE);
  });

  it("decideOsBacklog defaults the note to empty", async () => {
    const result = await decideOsBacklog(TOKEN, "req1", { decision: "reject" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog/req1/decision", {
      method: "POST",
      token: TOKEN,
      body: { decision: "reject", note: "" },
    });
    expect(result).toBe(API_RESPONSE);
  });
});

describe("os usage api", () => {
  it("fetchOsUsage issues a GET", async () => {
    const result = await fetchOsUsage(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/usage", { token: TOKEN });
    expect(result).toBe(API_RESPONSE);
  });
});
