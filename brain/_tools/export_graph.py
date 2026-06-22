#!/usr/bin/env python3
"""Export the vault's wikilink graph to JSON + a self-contained viewer.

Parses every note, builds nodes (one per note, typed by folder/frontmatter) and edges (one per
resolved wikilink), and writes:
  _index/graph.json   - {nodes:[{id,label,type,folder}], edges:[{source,target}]}
  _index/viewer.html  - zero-dependency force-graph viewer (open in a browser)

Read-only against the vault except for the two _index/ outputs. stdlib only.
"""
import json
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
OUT = VAULT / "_index"
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def md_files():
    return [p for p in VAULT.rglob("*.md") if "_tools" not in p.parts and "_index" not in p.parts]


def frontmatter_type(text):
    m = re.search(r"^type:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip('"\'') if m else "note"


def norm(target):
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    return target[:-3] if target.lower().endswith(".md") else target


def main():
    files = md_files()
    by_base = {}
    for p in files:
        by_base.setdefault(p.stem.lower(), p)
    nodes, edges, seen = [], [], set()
    for p in files:
        rel = p.relative_to(VAULT)
        folder = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        text = p.read_text(encoding="utf-8")
        nid = p.stem
        if nid.lower() not in seen:
            nodes.append({"id": nid, "label": nid, "type": frontmatter_type(text), "folder": folder})
            seen.add(nid.lower())
        for m in LINK_RE.finditer(text):
            tgt = norm(m.group(1))
            if not tgt:
                continue
            key = tgt.split("/")[-1].lower()
            if key in by_base:
                edges.append({"source": nid, "target": by_base[key].stem})
    OUT.mkdir(exist_ok=True)
    (OUT / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=2), encoding="utf-8")
    (OUT / "viewer.html").write_text(VIEWER, encoding="utf-8")
    print(f"graph: {len(nodes)} nodes, {len(edges)} edges → _index/graph.json")
    print("open _index/viewer.html in a browser to explore.")
    return 0


VIEWER = """<!doctype html><html><head><meta charset=\"utf-8\"><title>Brain Graph</title>
<style>body{margin:0;background:#0f1115;color:#cdd6f4;font:13px system-ui}#h{position:fixed;top:8px;left:12px;z-index:9}
canvas{display:block}a{color:#89b4fa}</style></head><body>
<div id=\"h\"><b>Compiled Vault Brain</b> — graph. drag to pan, scroll to zoom. <span id=\"s\"></span></div>
<canvas id=\"c\"></canvas><script>
const cv=document.getElementById('c'),ctx=cv.getContext('2d');let W,H;
function rs(){W=cv.width=innerWidth;H=cv.height=innerHeight}window.onresize=rs;rs();
const COL={person:'#f38ba8',company:'#fab387',product:'#a6e3a1',project:'#89b4fa',topic:'#cba6f7',
decision:'#f9e2af',commitment:'#eba0ac',procedure:'#94e2d5',preference:'#74c7ec','context-pack':'#f5c2e7',
source:'#6c7086',map:'#b4befe',note:'#9399b2'};
fetch('graph.json').then(r=>r.json()).then(g=>{
document.getElementById('s').textContent=g.nodes.length+' nodes, '+g.edges.length+' edges';
const N={};g.nodes.forEach((n,i)=>{n.x=Math.cos(i)*300+W/2;n.y=Math.sin(i*1.3)*300+H/2;n.vx=0;n.vy=0;N[n.id]=n});
const E=g.edges.filter(e=>N[e.source]&&N[e.target]);
let ox=0,oy=0,z=1,drag=false,lx,ly;
cv.onmousedown=e=>{drag=true;lx=e.clientX;ly=e.clientY};cv.onmouseup=()=>drag=false;
cv.onmousemove=e=>{if(drag){ox+=e.clientX-lx;oy+=e.clientY-ly;lx=e.clientX;ly=e.clientY}};
cv.onwheel=e=>{z*=e.deltaY<0?1.1:0.9;e.preventDefault()};
function step(){for(const n of g.nodes){n.vx*=.85;n.vy*=.85}
for(let i=0;i<g.nodes.length;i++)for(let j=i+1;j<g.nodes.length;j++){const a=g.nodes[i],b=g.nodes[j];
let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1,f=1200/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
for(const e of E){const a=N[e.source],b=N[e.target];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-90)*.01;
a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
for(const n of g.nodes){n.x+=n.vx;n.y+=n.vy}}
function draw(){ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(ox,oy);ctx.scale(z,z);
ctx.strokeStyle='rgba(120,130,160,.25)';for(const e of E){const a=N[e.source],b=N[e.target];
ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
for(const n of g.nodes){const deg=E.filter(e=>e.source===n.id||e.target===n.id).length;const r=4+Math.min(deg,10);
ctx.fillStyle=COL[n.type]||COL.note;ctx.beginPath();ctx.arc(n.x,n.y,r,0,7);ctx.fill();
if(z>0.8){ctx.fillStyle='#cdd6f4';ctx.font='10px system-ui';ctx.fillText(n.label,n.x+r+2,n.y+3)}}
ctx.restore()}
(function loop(){for(let k=0;k<2;k++)step();draw();requestAnimationFrame(loop)})();
});</script></body></html>"""


if __name__ == "__main__":
    sys.exit(main())
