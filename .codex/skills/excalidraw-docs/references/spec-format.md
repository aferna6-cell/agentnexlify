# Excalidraw Docs Spec Format

Use this compact JSON format with `scripts/make_excalidraw_doc_diagram.py` when a docs diagram is primarily boxes and arrows.

## Minimal Example

```json
{
  "title": "Widget Message Flow",
  "nodes": [
    { "id": "visitor", "label": "Visitor" },
    { "id": "widget", "label": "Embed Widget" },
    { "id": "api", "label": "FastAPI" },
    { "id": "llm", "label": "Claude Runtime" },
    { "id": "db", "label": "Supabase" }
  ],
  "edges": [
    { "from": "visitor", "to": "widget", "label": "chat" },
    { "from": "widget", "to": "api", "label": "POST /api/chat/message" },
    { "from": "api", "to": "llm", "label": "tool call" },
    { "from": "api", "to": "db", "label": "lead + messages" }
  ]
}
```

## Fields

- `title`: Optional diagram title.
- `nodes`: Required array. Each node needs `id` and `label`.
- `nodes[].x`, `nodes[].y`: Optional manual placement in pixels.
- `nodes[].w`, `nodes[].h`: Optional size. Defaults to `220` by `76`.
- `nodes[].color`: Optional fill color. Use sparingly.
- `edges`: Optional array. Each edge needs `from` and `to` node ids.
- `edges[].label`: Optional short text shown near the arrow.
- `layout.columns`: Optional number of automatic layout columns.
- `layout.x_gap`, `layout.y_gap`: Optional spacing for automatic layout.

## Placement Guidance

- For request paths, use left-to-right ordering.
- For lifecycle processes, use top-to-bottom ordering or set `layout.columns` to `1`.
- For architecture diagrams with trust boundaries, create boundary nodes with a light fill and then manually place service nodes around them if needed.
- Keep the source `.excalidraw` and rendered `.svg` in the same directory.

## Markdown Pattern

```markdown
![Widget Message Flow](diagrams/widget-message-flow.svg)

Editable source: [widget-message-flow.excalidraw](diagrams/widget-message-flow.excalidraw)
```
