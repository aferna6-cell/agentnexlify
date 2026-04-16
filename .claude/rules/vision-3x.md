# 3x Vision — Opus 4.7 Higher-Resolution Images

## What it is
Opus 4.7 accepts images up to **2,576 pixels on the long edge** (~3.75 megapixels) — more than 3x prior Claude models. Model-level change; no API parameter. Images are simply processed at higher fidelity.

## Where this matters in AgentNexLiFy

| Use case | Why 3x vision helps |
|---|---|
| Screenshot debugging (widget embeds, dashboard renders) | Dense UI elements now readable — tooltip text, tiny buttons |
| Computer-use agent workflows | Reading claude.ai web UIs, OAuth dialogs, Stripe portals |
| Design comp analysis | Figma exports, Tailwind class inspection from high-res refs |
| Diagram ingestion | Architecture charts, ER diagrams, sequence diagrams |
| Data extraction from complex PDFs | Invoice line items, form fields, compliance docs |
| OCR-adjacent tasks | Screenshots of handwritten notes, receipts uploaded via widget |
| Frontend design review | `preview_screenshot` + hand-off to Opus 4.7 for design-taste check |

## When to use high-res input
- When you need pixel-perfect references
- When the task depends on fine visual detail
- When downsampling would lose meaningful information
- When the failure mode of low-res is the failure mode of the task

## When to DOWNSAMPLE first
- When you don't need the detail (list screenshots, generic layouts)
- When token cost matters — higher-res = more tokens consumed
- When the task only needs "is this a login page?" level understanding
- Batch image processing at scale

Downsample target: ~1,024px long edge usually enough for non-detail tasks.

## Token cost awareness
Higher-resolution images consume more tokens. For cost-sensitive batch workloads:
- Downsample via `pillow` or `sharp` before API call
- Use `task_budget` (see `task-budgets.md`) to cap per-image output
- Pre-OCR with a cheap model (Haiku) if full vision isn't needed

## Tools that leverage this
- `preview_screenshot` — saves dashboard/widget screenshots, now readable in detail
- `mcp__computer-use__screenshot` — desktop captures, usable without downsampling
- `mcp__Claude_in_Chrome__computer` with `action: screenshot` — browser automation visuals
- Widget upload flow — customer screenshots now analyzable at shipped resolution

## Anti-patterns
- Never downsample BEFORE asking "do I need the detail?"
- Never claim "I can't read that screenshot" without trying the high-res input
- Never send raw 12MP camera photos — downsample; 3.75MP ceiling applies
- Never skip Haiku triage on a batch of 1000 images — reserve Opus for the hard ones

## Cross-refs
- `rules/opus-4-7.md`
- `rules/task-budgets.md` — control token cost of high-res inputs
- `preview_screenshot` (Claude Preview MCP)
- `mcp__computer-use__screenshot`
