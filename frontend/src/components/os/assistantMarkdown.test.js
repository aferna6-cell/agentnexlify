import { describe, expect, it } from "vitest";
import { renderAssistantMarkdown } from "./assistantMarkdown";

describe("renderAssistantMarkdown", () => {
  it("renders bold and bullets instead of raw markdown", () => {
    const html = renderAssistantMarkdown(
      "**Two plans**\n- Chatbot is $19.99/month\n- AI Workforce is $99.99/month",
    );
    expect(html).toContain("<strong>Two plans</strong>");
    expect(html).toContain("<li>Chatbot is $19.99/month</li>");
    expect(html).toContain("<li>AI Workforce is $99.99/month</li>");
    expect(html).not.toContain("**");
  });

  it("drops raw HTML from the assistant message", () => {
    const html = renderAssistantMarkdown(
      "Cancel anytime.\n<script>alert(1)</script>\n<img src=x onerror=alert(1)>",
    );
    expect(html).toContain("Cancel anytime.");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("&lt;img");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<img");
  });
});
