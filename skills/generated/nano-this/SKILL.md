---
name: nano-this
description: Turn a document or pasted content into a polished Swiss Pulse-style infographic with a fallback prompt when image generation is unavailable.
created_by: codex
---

# nano-this

## Purpose
Reduce text-heavy material into a one-page Swiss Pulse-style infographic with a strong headline, a dominant metric or hook, a few supporting facts, and a polished visual output.

## When To Use
- Use when the user wants a poster, infographic, one-pager, or social-ready PNG from a document or URL.
- Use when the source contains a clear narrative, metric, trend, or set of facts that should be compressed visually.
- Use when the user asks for "Swiss Pulse", "polished infographic", or a fast visual digest of a report.

## Inputs
- Source document, URL, note, or conversation excerpt
- Any requested size or aspect ratio
- Any required brand or tone constraints the infographic must preserve

## Workflow Steps
- Read the source and extract one headline, one hero metric or hook, three to seven supporting facts, and one closing takeaway.
- Reduce the copy aggressively so the output reads like an infographic, not a report pasted into a poster.
- Apply a Swiss Pulse visual direction: editorial grid, bold typography, restrained palette, clear spacing, and one vivid accent.
- Generate the bitmap output with the best available image-generation path in the current environment.
- If image generation is unavailable, return the final generation prompt, the compressed copy blocks, and the recommended aspect ratio so the task is still reusable.

## Constraints
- Do not invent numbers, dates, sources, or quotes.
- Default to a 4:5 portrait output unless the user asks for another format.
- Keep the copy sparse and high-signal.
- Use the best tool actually available in the environment; do not claim Gemini access unless it exists.

## Examples
- Use when asked: "Nano this PDF."
- Use when asked: "Turn this report into an infographic."
- Use when asked: "Make a Swiss Pulse PNG from these notes."
