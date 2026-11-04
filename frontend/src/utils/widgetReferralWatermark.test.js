import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";

const widgetPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../../widget/agentnexlify-widget.js",
);

function installWidgetScript() {
  document.body.innerHTML = "";
  window.__agentNexlifyWidget = false;
  const script = document.createElement("script");
  script.setAttribute("data-api-key", "anx_embed_key_should_not_leak");
  script.setAttribute("data-api-base", "https://api.test");
  document.body.appendChild(script);
}

function stubConfig(referralCode) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/widget/config/")) {
        return {
          ok: true,
          json: async () => ({
            bot_name: "Aria",
            referral_code: referralCode,
            plan: "free",
          }),
        };
      }
      return { ok: true, json: async () => ({ ok: true }) };
    }),
  );
}

async function waitForLink() {
  await vi.waitFor(() => {
    expect(document.querySelector("#anx-powered a")).toBeTruthy();
  });
  return document.querySelector("#anx-powered a");
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
  window.__agentNexlifyWidget = false;
});

describe("widget watermark referral link", () => {
  it("uses a link with no ref when the code is null", async () => {
    installWidgetScript();
    stubConfig(null);
    await import("../../../widget/agentnexlify-widget.js?boot=null");
    const link = await waitForLink();
    expect(link.href).not.toContain("ref=");
    expect(link.href).not.toContain("anx_");
  });

  it("uses a link with no ref when the code is an anx_ key", async () => {
    installWidgetScript();
    stubConfig("anx_should_not_leak");
    await import("../../../widget/agentnexlify-widget.js?boot=anx");
    const link = await waitForLink();
    expect(link.href).not.toContain("ref=");
    expect(link.href).not.toContain("anx_");
    expect(readFileSync(widgetPath, "utf8")).not.toContain(
      "ref=${encodeURIComponent(API_KEY)}",
    );
  });

  it("adds only the public code when config provides one", async () => {
    installWidgetScript();
    stubConfig("ab12cd34");
    await import("../../../widget/agentnexlify-widget.js?boot=public");
    const link = await waitForLink();
    expect(link.href).toContain("ref=ab12cd34");
    expect(link.href).not.toContain("anx_");
    link.click();
    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
  });
});
