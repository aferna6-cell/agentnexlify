#!/usr/bin/env python3
"""Generate editable Excalidraw and docs-friendly SVG from a compact JSON spec."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


DEFAULT_NODE_WIDTH = 220
DEFAULT_NODE_HEIGHT = 76
DEFAULT_X_GAP = 90
DEFAULT_Y_GAP = 80
TITLE_HEIGHT = 56
MARGIN = 32


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "diagram"


def stable_int(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:8], 16)


def element_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:16]}"


def load_spec(path: str) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    spec = json.loads(raw)
    if not isinstance(spec, dict):
        raise SystemExit("Spec must be a JSON object.")
    if not isinstance(spec.get("nodes"), list) or not spec["nodes"]:
        raise SystemExit("Spec must include a non-empty nodes array.")
    return spec


def normalize_nodes(spec: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = []
    layout = spec.get("layout") or {}
    columns = int(layout.get("columns") or min(3, max(1, math.ceil(math.sqrt(len(spec["nodes"]))))))
    x_gap = int(layout.get("x_gap") or DEFAULT_X_GAP)
    y_gap = int(layout.get("y_gap") or DEFAULT_Y_GAP)
    y_offset = TITLE_HEIGHT if spec.get("title") else 0

    for index, raw in enumerate(spec["nodes"]):
        if not isinstance(raw, dict):
            raise SystemExit("Each node must be a JSON object.")
        if not raw.get("id") or not raw.get("label"):
            raise SystemExit("Each node must include id and label.")

        width = int(raw.get("w") or raw.get("width") or DEFAULT_NODE_WIDTH)
        height = int(raw.get("h") or raw.get("height") or DEFAULT_NODE_HEIGHT)
        row = index // columns
        col = index % columns
        x = int(raw.get("x") if raw.get("x") is not None else col * (width + x_gap))
        y = int(raw.get("y") if raw.get("y") is not None else y_offset + row * (height + y_gap))

        node = dict(raw)
        node.update({"w": width, "h": height, "x": x, "y": y})
        nodes.append(node)
    return nodes


def text_lines(label: str, max_chars: int = 22) -> list[str]:
    words = str(label).split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def base_element(kind: str, key: str, x: float, y: float, width: float, height: float) -> dict[str, Any]:
    seed = stable_int(key)
    return {
        "id": element_id(kind, key),
        "type": kind,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": seed,
        "version": 1,
        "versionNonce": seed,
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def make_excalidraw(spec: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []

    if spec.get("title"):
        title = base_element("text", "title:" + spec["title"], 0, 0, 640, 34)
        title.update(
            {
                "text": spec["title"],
                "fontSize": 28,
                "fontFamily": 1,
                "textAlign": "left",
                "verticalAlign": "top",
                "containerId": None,
                "originalText": spec["title"],
                "lineHeight": 1.25,
                "baseline": 25,
            }
        )
        elements.append(title)

    node_map = {node["id"]: node for node in nodes}
    for node in nodes:
        rect = base_element("rectangle", "node:" + node["id"], node["x"], node["y"], node["w"], node["h"])
        rect["backgroundColor"] = node.get("color") or "#ffffff"
        elements.append(rect)

        label = str(node["label"])
        text = base_element("text", "text:" + node["id"], node["x"] + 12, node["y"] + 16, node["w"] - 24, node["h"] - 24)
        text.update(
            {
                "text": label,
                "fontSize": int(node.get("font_size") or 20),
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": rect["id"],
                "originalText": label,
                "lineHeight": 1.25,
                "baseline": 23,
            }
        )
        elements.append(text)

    for index, edge in enumerate(spec.get("edges") or []):
        start = node_map.get(edge.get("from"))
        end = node_map.get(edge.get("to"))
        if not start or not end:
            raise SystemExit(f"Edge {index} references an unknown node.")

        sx = start["x"] + start["w"]
        sy = start["y"] + start["h"] / 2
        ex = end["x"]
        ey = end["y"] + end["h"] / 2
        if ex < sx:
            sx = start["x"] + start["w"] / 2
            sy = start["y"] + start["h"]
            ex = end["x"] + end["w"] / 2
            ey = end["y"]

        arrow = base_element("arrow", f"edge:{index}:{edge.get('from')}:{edge.get('to')}", sx, sy, ex - sx, ey - sy)
        arrow.update(
            {
                "points": [[0, 0], [ex - sx, ey - sy]],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": "arrow",
            }
        )
        elements.append(arrow)

        if edge.get("label"):
            label = str(edge["label"])
            lx = sx + (ex - sx) / 2 - 80
            ly = sy + (ey - sy) / 2 - 28
            text = base_element("text", f"edge-label:{index}:{label}", lx, ly, 160, 24)
            text.update(
                {
                    "text": label,
                    "fontSize": 14,
                    "fontFamily": 2,
                    "textAlign": "center",
                    "verticalAlign": "middle",
                    "containerId": None,
                    "originalText": label,
                    "lineHeight": 1.2,
                    "baseline": 17,
                }
            )
            elements.append(text)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "excalidraw-docs skill",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }


def bounds(nodes: list[dict[str, Any]], title: str | None) -> tuple[int, int, int, int]:
    min_x = 0
    min_y = 0
    max_x = max(node["x"] + node["w"] for node in nodes)
    max_y = max(node["y"] + node["h"] for node in nodes)
    if title:
        max_y = max(max_y, TITLE_HEIGHT)
    return min_x, min_y, max_x, max_y


def node_center(node: dict[str, Any], side: str) -> tuple[float, float]:
    if side == "right":
        return node["x"] + node["w"], node["y"] + node["h"] / 2
    if side == "left":
        return node["x"], node["y"] + node["h"] / 2
    if side == "bottom":
        return node["x"] + node["w"] / 2, node["y"] + node["h"]
    return node["x"] + node["w"] / 2, node["y"]


def render_svg(spec: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    title = spec.get("title")
    min_x, min_y, max_x, max_y = bounds(nodes, title)
    width = max_x - min_x + MARGIN * 2
    height = max_y - min_y + MARGIN * 2
    node_map = {node["id"]: node for node in nodes}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{min_x - MARGIN} {min_y - MARGIN} {width} {height}" role="img" aria-label="{escape(str(title or "Diagram"))}">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#1e1e1e" />',
        "</marker>",
        "</defs>",
        '<rect x="{0}" y="{1}" width="{2}" height="{3}" fill="#ffffff" />'.format(min_x - MARGIN, min_y - MARGIN, width, height),
    ]

    if title:
        parts.append(f'<text x="0" y="0" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#1e1e1e">{escape(str(title))}</text>')

    for edge in spec.get("edges") or []:
        start = node_map[edge["from"]]
        end = node_map[edge["to"]]
        sx, sy = node_center(start, "right")
        ex, ey = node_center(end, "left")
        if ex < sx:
            sx, sy = node_center(start, "bottom")
            ex, ey = node_center(end, "top")
        parts.append(f'<line x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}" stroke="#1e1e1e" stroke-width="2" marker-end="url(#arrow)" />')
        if edge.get("label"):
            lx = sx + (ex - sx) / 2
            ly = sy + (ey - sy) / 2 - 10
            parts.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">{escape(str(edge["label"]))}</text>')

    for node in nodes:
        fill = escape(str(node.get("color") or "#ffffff"))
        parts.append(f'<rect x="{node["x"]}" y="{node["y"]}" width="{node["w"]}" height="{node["h"]}" rx="8" fill="{fill}" stroke="#1e1e1e" stroke-width="2" />')
        lines = text_lines(str(node["label"]))
        total = len(lines)
        start_y = node["y"] + node["h"] / 2 - ((total - 1) * 12)
        for offset, line in enumerate(lines):
            y = start_y + offset * 24 + 7
            parts.append(f'<text x="{node["x"] + node["w"] / 2}" y="{y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="600" fill="#111827">{escape(line)}</text>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def markdown_snippet(title: str, name: str, svg_path: Path, excalidraw_path: Path, md_path: Path) -> str:
    svg_ref = svg_path.name if svg_path.parent == md_path.parent else svg_path.as_posix()
    exc_ref = excalidraw_path.name if excalidraw_path.parent == md_path.parent else excalidraw_path.as_posix()
    alt = title or name.replace("-", " ").title()
    return f"![{alt}]({svg_ref})\n\nEditable source: [{excalidraw_path.name}]({exc_ref})\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="Path to spec JSON, or '-' for stdin")
    parser.add_argument("--out-dir", default=".", help="Directory for generated files")
    parser.add_argument("--name", help="Output basename. Defaults to title or spec filename")
    parser.add_argument("--no-svg", action="store_true", help="Skip SVG generation")
    parser.add_argument("--no-markdown", action="store_true", help="Skip Markdown snippet generation")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    nodes = normalize_nodes(spec)
    inferred_name = spec.get("title") or (Path(args.spec).stem if args.spec != "-" else "diagram")
    name = slugify(args.name or inferred_name)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    excalidraw_path = out_dir / f"{name}.excalidraw"
    svg_path = out_dir / f"{name}.svg"
    md_path = out_dir / f"{name}.md"

    scene = make_excalidraw(spec, nodes)
    excalidraw_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    written = [excalidraw_path]
    if not args.no_svg:
        svg_path.write_text(render_svg(spec, nodes), encoding="utf-8")
        written.append(svg_path)
    if not args.no_markdown:
        md_path.write_text(markdown_snippet(str(spec.get("title") or ""), name, svg_path, excalidraw_path, md_path), encoding="utf-8")
        written.append(md_path)

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
