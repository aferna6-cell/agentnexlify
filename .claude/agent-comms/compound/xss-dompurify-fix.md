# XSS Fix: Replace Regex Sanitizers with DOMPurify

## What was done

Replaced two hand-rolled regex HTML sanitizers with DOMPurify, a battle-tested XSS sanitization library. The regex sanitizers only stripped `<script>` tags and `on*` event handlers, missing SVG-based XSS, `javascript:` protocol URIs, `<iframe>`, `<object>`, `<embed>`, and many other vectors.

### Files modified
- `frontend/package.json` — added `dompurify` dependency
- `frontend/src/pages/Automations/SequenceBuilder.jsx` — replaced `sanitizeHtml()` with DOMPurify, import added at line 2
- `frontend/src/pages/DocumentsPage.jsx` — replaced `sanitizeDocHtml()` with DOMPurify (stricter config), import added at line 13

### Package installed
- `dompurify` (latest) — 22.76 kB production chunk (8.79 kB gzipped), code-split by Vite

## Components

- **SequenceBuilder.jsx `sanitizeHtml()`**: Uses `DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })` — standard HTML profile sanitization
- **DocumentsPage.jsx `sanitizeDocHtml()`**: Uses stricter config with `FORBID_TAGS: ["iframe", "object", "embed", "form", "link", "meta"]` because documents render richer tenant-authored HTML via `dangerouslySetInnerHTML`

## API dependencies

None. This is a frontend-only change. Both sanitizer functions operate on HTML strings already fetched from the backend.

## Testing notes

1. Build passes cleanly (`npm run build` succeeds, 0 errors)
2. Verify SequenceBuilder email preview still renders template HTML correctly (bold, italic, links, headings)
3. Verify DocumentsPage document preview still renders document HTML correctly
4. Test that `<script>alert(1)</script>` is stripped in both previews
5. Test that `<img src=x onerror=alert(1)>` is stripped (this was NOT caught by the old regex)
6. Test that `<svg onload=alert(1)>` is stripped (this was NOT caught by the old regex)
7. Test that `<a href="javascript:alert(1)">` is stripped (this was NOT caught by the old regex)

## Concerns

- None for the orchestrator. This is a drop-in replacement with strictly better security coverage.
- DOMPurify adds ~8.8 kB gzipped to the bundle, loaded only when SequenceBuilder or DocumentsPage are accessed (code-split).
