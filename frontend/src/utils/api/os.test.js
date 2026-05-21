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

beforeEach(() => {
  request.mockReset();
  request.mockResolvedValue({ ok: true });
});

describe("os threads api", () => {
  it("listOsThreads issues a GET with token", async () => {
    await listOsThreads(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      token: TOKEN,
    });
  });

  it("createOsThread posts the given title", async () => {
    await createOsThread(TOKEN, "Plan launch");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      method: "POST",
      token: TOKEN,
      body: { title: "Plan launch" },
    });
  });

  it("createOsThread falls back to a default title", async () => {
    await createOsThread(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads", {
      method: "POST",
      token: TOKEN,
      body: { title: "New conversation" },
    });
  });

  it("fetchOsThreadMessages targets the thread path", async () => {
    await fetchOsThreadMessages(TOKEN, "t1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads/t1/messages", {
      token: TOKEN,
    });
  });

  it("postOsMessage posts content to the thread", async () => {
    await postOsMessage(TOKEN, "t1", "do the thing");
    expect(request).toHaveBeenCalledWith("/api/v1/os/threads/t1/messages", {
      method: "POST",
      token: TOKEN,
      body: { content: "do the thing" },
    });
  });
});

describe("os agent runs api", () => {
  it("fetchOsAgentRun targets the run path", async () => {
    await fetchOsAgentRun(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/agent-runs/r1", {
      token: TOKEN,
    });
  });

  it("reportOsRunBug posts to the report-bug path", async () => {
    await reportOsRunBug(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith(
      "/api/v1/os/agent-runs/r1/report-bug",
      {
        method: "POST",
        token: TOKEN,
      },
    );
  });
});

describe("os deliverables api", () => {
  it("editOsDeliverable patches title and body", async () => {
    await editOsDeliverable(TOKEN, "r1", { title: "T", body: "B" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1", {
      method: "PATCH",
      token: TOKEN,
      body: { title: "T", body: "B" },
    });
  });

  it("approveOsDeliverable posts to the approve path", async () => {
    await approveOsDeliverable(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1/approve", {
      method: "POST",
      token: TOKEN,
    });
  });

  it("rejectOsDeliverable posts to the reject path", async () => {
    await rejectOsDeliverable(TOKEN, "r1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/deliverables/r1/reject", {
      method: "POST",
      token: TOKEN,
    });
  });
});

describe("os memory api", () => {
  it("listOsMemory issues a GET", async () => {
    await listOsMemory(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", { token: TOKEN });
  });

  it("createOsMemory posts content with explicit kind", async () => {
    await createOsMemory(TOKEN, { content: "c", kind: "preference" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", {
      method: "POST",
      token: TOKEN,
      body: { content: "c", kind: "preference" },
    });
  });

  it("createOsMemory defaults kind to fact", async () => {
    await createOsMemory(TOKEN, { content: "c" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory", {
      method: "POST",
      token: TOKEN,
      body: { content: "c", kind: "fact" },
    });
  });

  it("rememberOsFact posts to the remember path", async () => {
    await rememberOsFact(TOKEN, "we ship Fridays");
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/remember", {
      method: "POST",
      token: TOKEN,
      body: { content: "we ship Fridays" },
    });
  });

  it("updateOsMemory patches the memory row", async () => {
    await updateOsMemory(TOKEN, "m1", { content: "new" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/m1", {
      method: "PATCH",
      token: TOKEN,
      body: { content: "new" },
    });
  });

  it("deleteOsMemory deletes the memory row", async () => {
    await deleteOsMemory(TOKEN, "m1");
    expect(request).toHaveBeenCalledWith("/api/v1/os/memory/m1", {
      method: "DELETE",
      token: TOKEN,
    });
  });
});

describe("os backlog api", () => {
  it("listOsBacklog issues a GET", async () => {
    await listOsBacklog(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog", {
      token: TOKEN,
    });
  });

  it("decideOsBacklog posts decision and note", async () => {
    await decideOsBacklog(TOKEN, "req1", { decision: "approve", note: "go" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog/req1/decision", {
      method: "POST",
      token: TOKEN,
      body: { decision: "approve", note: "go" },
    });
  });

  it("decideOsBacklog defaults the note to empty", async () => {
    await decideOsBacklog(TOKEN, "req1", { decision: "reject" });
    expect(request).toHaveBeenCalledWith("/api/v1/os/backlog/req1/decision", {
      method: "POST",
      token: TOKEN,
      body: { decision: "reject", note: "" },
    });
  });
});

describe("os usage api", () => {
  it("fetchOsUsage issues a GET", async () => {
    await fetchOsUsage(TOKEN);
    expect(request).toHaveBeenCalledWith("/api/v1/os/usage", { token: TOKEN });
  });
});
