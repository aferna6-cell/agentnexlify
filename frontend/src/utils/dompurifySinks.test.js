import DOMPurify from "dompurify";
import { describe, expect, it } from "vitest";

const PAYLOAD =
  '<img src="x" onerror="alert(1)"><script>alert(1)</script>' +
  '<a href="javascript:alert(1)">x</a><svg><animate onbegin="alert(1)" /></svg>' +
  "<p>Hello <strong>KB</strong></p>";

function documentsSanitize(html) {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["iframe", "object", "embed", "form", "link", "meta"],
  });
}

describe("DOMPurify sinks", () => {
  it("strips executable markup and keeps benign formatting", () => {
    for (const clean of [
      DOMPurify.sanitize(PAYLOAD),
      documentsSanitize(PAYLOAD),
    ]) {
      expect(clean).not.toMatch(/onerror|onbegin|<script|javascript:/i);
      expect(clean).toContain("<p>");
      expect(clean).toContain("<strong>KB</strong>");
    }
  });

  it("documents policy drops forbidden tags", () => {
    const clean = documentsSanitize(
      '<iframe src="https://evil.test"></iframe><p>ok</p>',
    );
    expect(clean).not.toContain("iframe");
    expect(clean).toContain("<p>ok</p>");
  });
});
