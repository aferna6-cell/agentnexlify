---
name: diagram-it
description: "Turn source material into the clearest diagram format and render it quickly without inventing structure."
version: 1.0.0
origin: generated
triggers: ["diagram", "flowchart", "map this", "visualize", "draw this"]
---

# diagram-it

## Purpose
Convert a URL, document, pasted text, or conversation context into the clearest diagram for the material, favoring simple visuals that reduce cognitive load and preserve meaning.

## When To Use
- Use when a user asks to diagram, map, flowchart, visualize, or explain a system visually.
- Use when the source material contains process steps, timelines, structures, hierarchies, or connected ideas.
- Use when dense text will be easier to understand as a Mermaid diagram or a saved visual artifact.

## Inputs
- Source content from a URL, attachment, pasted text, or prior conversation
- Any user preference for diagram style, such as flowchart, timeline, tree, or concept map
- Constraints on output format, such as inline Mermaid or a saved `.excalidraw` or SVG file

## Workflow Steps
- Read the source and identify the real structure before drawing anything: sequence, dependency, chronology, hierarchy, or relationship map.
- Choose the smallest diagram type that preserves meaning: flowchart for decisions, structural graph for systems, timeline for dated events, tree for nesting, concept map for linked ideas.
- Render the result in Mermaid when possible because it is easy to review and share in-text.
- If the user explicitly wants Excalidraw and the environment cannot render it inline, create a saved `.excalidraw` or SVG artifact instead of pretending it is inline.
- Add at most one short note after the diagram when an assumption or compression choice matters.

## Constraints
- Do not invent dependencies, dates, ownership, or sequencing that the source does not support.
- Keep node labels short and concrete.
- Prefer one clear diagram over a large overloaded canvas.
- Group repetitive low-value details instead of exploding the diagram into noise.

## Examples
- Use when asked: "Diagram this onboarding flow."
- Use when asked: "Turn this spec into a timeline."
- Use when asked: "Map this system architecture for me."
