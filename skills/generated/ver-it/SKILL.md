---
name: ver-it
description: "Build a Swiss Pulse-style interactive HTML summary with a hero metric, stats, chart, and dark-mode presentation."
version: 1.0.0
origin: generated
triggers: ["ver this", "HTML summary", "dark-mode page", "shareable page"]
---

# ver-it

## Purpose
Transform source material into a polished Swiss Pulse-style HTML page that highlights a hero metric, supporting stats, a chart or comparison, and short takeaways in a clean dark-mode layout.

## When To Use
- Use when the user wants a shareable HTML explainer or mini dashboard from a report, deck, or article.
- Use when the source contains enough structure for a hero metric plus supporting stats and one meaningful visual.
- Use when the user explicitly asks for Swiss Pulse HTML, a dark-mode summary page, or a shareable link.

## Inputs
- Source content from a report, URL, notes, or conversation
- Any requested deployment or sharing target
- Any required branding, palette, or metric emphasis

## Workflow Steps
- Read the source and extract the headline, hero metric, three to six supporting stats, and one chart-worthy comparison or series.
- Build a single HTML page with an eyebrow label, strong title, dark-mode hero section, concise stat cards, one visual, and short takeaways.
- Use Chart.js or a simpler inline visual only when the source has enough real numeric structure to justify it.
- Save the HTML locally first so it can be reviewed before any sharing step.
- If the user asks for a public result and a real deployment path exists, publish it and return the actual link; otherwise return the local file path.

## Constraints
- Do not invent trends, metrics, or chart data.
- Do not promise a public URL unless one was actually created.
- Keep the output responsive and readable on desktop and mobile.
- Prefer one strong chart over a noisy dashboard.

## Examples
- Use when asked: "Ver this earnings summary."
- Use when asked: "Turn this deck into a shareable dark-mode page."
- Use when asked: "Build a Swiss Pulse HTML summary from this writeup."
