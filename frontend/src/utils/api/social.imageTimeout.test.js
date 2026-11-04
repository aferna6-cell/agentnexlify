import { afterEach, describe, expect, it, vi } from "vitest";

import { generateSocialImage } from "./social";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("generateSocialImage", () => {
  it("waits 120 seconds instead of the default API timeout", async () => {
    const timeout = vi
      .spyOn(AbortSignal, "timeout")
      .mockReturnValue(new AbortController().signal);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ url: "https://cdn.example/cat.png" }),
      }),
    );

    const result = await generateSocialImage("tenant-1", "token", {
      prompt: "a cat",
      platform: "instagram",
    });

    expect(timeout).toHaveBeenCalledWith(120000);
    expect(result).toEqual({ url: "https://cdn.example/cat.png" });
  });
});
