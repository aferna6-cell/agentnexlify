---
name: vis-it
description: Turn content into the best-fit visual explainer or interactive widget, using HTML when true interactivity is needed.
created_by: codex
---

# vis-it

## Purpose
Choose the strongest visual format for the material and produce the lightest useful interactive explainer, chart, comparison, timeline, or pipeline representation.

## When To Use
- Use when the user wants a chart, comparison, pipeline, timeline, or explainer instead of plain prose.
- Use when the content would benefit from a small interactive HTML widget rather than a static answer.
- Use when the main goal is to make data, process, or tradeoffs easier to scan and compare.

## Inputs
- Source material from text, docs, URLs, or conversation
- Any preference for chart type, widget style, or interaction pattern
- Any destination constraints such as inline display versus saved HTML artifact

## Workflow Steps
- Read the source and identify whether the core visual need is comparison, change over time, sequence, breakdown, or explanation.
- Choose the simplest format that fits: timeline, comparison layout, pipeline, chart, or annotated explainer.
- Use Mermaid when the structure itself is the story and interactivity would add little value.
- Build a single self-contained HTML file when the user benefits from hover states, toggles, sorting, tabs, or lightweight interaction.
- Return the visual immediately and add only a brief note if interpretation or assumptions matter.

## Constraints
- Do not force interactivity when a static visual is clearer.
- Do not invent data or imply precision that the source does not support.
- Keep HTML outputs mobile-friendly and easy to open locally.
- If inline interactive rendering is not truly available, save the widget as an artifact instead of pretending it is inline.

## Examples
- Use when asked: "Vis this memo."
- Use when asked: "Turn this data into an interactive explainer."
- Use when asked: "Make a pipeline widget from this process."
