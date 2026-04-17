---
name: excalidraw-docs
description: Create, update, and embed editable Excalidraw diagrams in documentation. Use when Codex needs to turn architecture notes, flows, system maps, process explanations, or docs content into `.excalidraw` source files plus rendered SVG/Markdown assets for READMEs, docs pages, planning docs, or implementation notes.
---

# Excalidraw Docs

## Overview

Use this skill to add Excalidraw-style diagrams to docs while keeping an editable source file beside the rendered asset. Prefer a source `.excalidraw` file plus an SVG embed so docs render reliably in GitHub, local Markdown previews, and static docs sites.

## Workflow

1. Identify the doc target and diagram purpose.
   - Architecture: show services, storage, APIs, queues, and trust boundaries.
   - Flow: show user/system steps and decision points.
   - Data model: show entities and relationships without duplicating full schema docs.
   - Plan: show phases, dependencies, and handoffs.

2. Place diagram files near the doc that uses them.
   - Default: `docs/diagrams/<slug>.excalidraw` and `docs/diagrams/<slug>.svg`.
   - For feature plans: keep diagrams under the same feature or plan directory.
   - Never overwrite a hand-edited `.excalidraw` file without reading it first.

3. Keep the rendered asset and editable source together.
   - Embed the SVG in Markdown.
   - Link the `.excalidraw` file immediately below or near the image.
   - Use concise labels; put detailed explanation in surrounding prose, not inside boxes.

4. Validate the output.
   - Confirm the SVG renders.
   - Confirm the `.excalidraw` JSON opens in Excalidraw.
   - Confirm labels are legible at typical docs width.

## Quick Generate

For simple node-and-arrow diagrams, create a small JSON spec and run:

```bash
python <skill-dir>/scripts/make_excalidraw_doc_diagram.py spec.json --out-dir docs/diagrams --name agent-flow
```

The helper writes:

- `<name>.excalidraw`: editable Excalidraw source
- `<name>.svg`: docs-renderable image
- `<name>.md`: Markdown snippet with image and source link

Read `references/spec-format.md` before using the helper for the first time or when a diagram needs manual placement.

## Editing Existing Diagrams

When editing an existing `.excalidraw` file:

- Preserve unknown fields, `files`, and element ids unless replacing the diagram intentionally.
- Make small scene edits directly in JSON only when the structure is simple.
- For complex visual edits, create a new spec, render a new SVG, then compare the result with the existing docs context.
- Keep rendered SVG output deterministic so doc diffs are reviewable.

## Documentation Style

- Use 3-7 primary nodes for overview diagrams.
- Use left-to-right flow for request paths and top-to-bottom flow for lifecycle or process diagrams.
- Name edges only when the label adds information, such as endpoint names, event names, or queue topics.
- Show boundaries explicitly for auth, tenant isolation, payments, external systems, and production infrastructure.
- Avoid copying dense prose into diagram labels; docs should explain what the diagram cannot.

## Resources

- `scripts/make_excalidraw_doc_diagram.py`: generate editable `.excalidraw`, rendered `.svg`, and Markdown snippets from a compact JSON spec.
- `references/spec-format.md`: JSON spec shape, examples, and placement guidance.
