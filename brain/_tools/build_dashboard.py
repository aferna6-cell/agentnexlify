#!/usr/bin/env python3
"""Build a self-contained visual dashboard for the second brain.

Scans brain/**/*.md, extracts frontmatter (type/name), a short summary, and
[[wikilinks]], then emits a single standalone HTML file with all data inlined
(no external requests) at brain/_index/dashboard.html.

The page renders: an interactive force-directed knowledge graph, a searchable /
filterable note browser, a detail panel, and live "Cold Outreach" metrics.

Run: python3 brain/_tools/build_dashboard.py
"""

import json
import os
import re
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # brain/
OUT = os.path.join(ROOT, "_index", "dashboard.html")

WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
FM = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def frontmatter(text):
    m = FM.match(text)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" ") and not line.startswith("-"):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"')
    return fm


def summary(text):
    body = FM.sub("", text)
    # first paragraph with prose; strip leading heading lines within it
    for para in re.split(r"\n\s*\n", body):
        lines = [ln for ln in para.splitlines() if not ln.strip().startswith("#")]
        p = " ".join(lines).strip()
        if not p:
            continue
        p = re.sub(r"\s+", " ", p)
        p = WIKILINK.sub(lambda m: m.group(1), p)
        p = re.sub(r"[*`>]", "", p)
        return p[:260]
    return ""


def collect():
    notes = {}
    for dirpath, _, files in os.walk(ROOT):
        if os.sep + "_" in dirpath:  # skip _tools, _index
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(dirpath, f)
            text = open(path, encoding="utf-8").read()
            stem = f[:-3]
            fm = frontmatter(text)
            folder = os.path.relpath(dirpath, ROOT)
            notes[stem] = {
                "id": stem,
                "label": fm.get("name", stem),
                "type": (fm.get("type") or "note").lower(),
                "folder": "(root)" if folder == "." else folder,
                "summary": summary(text),
                "links": [],
            }
    # resolve links by label or id
    by_label = {n["label"]: sid for sid, n in notes.items()}
    for sid, text_note in list(notes.items()):
        pass
    for dirpath, _, files in os.walk(ROOT):
        if os.sep + "_" in dirpath:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            stem = f[:-3]
            if stem not in notes:
                continue
            text = open(os.path.join(dirpath, f), encoding="utf-8").read()
            targets = set()
            for t in WIKILINK.findall(text):
                t = t.strip()
                tid = t if t in notes else by_label.get(t)
                if tid and tid != stem:
                    targets.add(tid)
            notes[stem]["links"] = sorted(targets)
    return notes


def build_graph(notes):
    nodes = [{"id": n["id"], "label": n["label"], "type": n["type"],
              "folder": n["folder"], "summary": n["summary"],
              "links": n["links"]} for n in notes.values()]
    edges = []
    seen = set()
    for n in notes.values():
        for t in n["links"]:
            key = tuple(sorted((n["id"], t)))
            if key in seen:
                continue
            seen.add(key)
            edges.append({"source": n["id"], "target": t})
    return {"nodes": nodes, "edges": edges}


# Live metrics for this build (updated per session; source: Cold Outreach Engine).
METRICS = {
    "campaign": "Small Business CT 7/10",
    "leads": 371,
    "sent": 197,
    "bounced": 0,
    "opens": 27,
    "replies": 1,
    "verticals": 11,
    "note": "371 verified CT small businesses, 0 bounces. Draining at 20/inbox/day.",
}

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentNexLiFy — Second Brain</title>
<style>
:root{--bg:#0f1115;--panel:#161923;--panel2:#1d2130;--line:#2a2f42;--tx:#cdd6f4;--dim:#8b93b0;--acc:#89b4fa}
:root[data-theme=light]{--bg:#f4f6fb;--panel:#fff;--panel2:#eef1f8;--line:#dde3f0;--tx:#1c2333;--dim:#5b647e;--acc:#3b6fd6}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#f4f6fb;--panel:#fff;--panel2:#eef1f8;--line:#dde3f0;--tx:#1c2333;--dim:#5b647e;--acc:#3b6fd6}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 system-ui,-apple-system,sans-serif;overflow:hidden}
#app{display:grid;grid-template-columns:270px 1fr 320px;height:100vh}
@media(max-width:900px){#app{grid-template-columns:1fr;grid-template-rows:auto 40vh auto;overflow:auto;height:auto}#graphwrap{height:40vh}}
.col{overflow:auto;padding:14px}
#left{border-right:1px solid var(--line);background:var(--panel)}
#right{border-left:1px solid var(--line);background:var(--panel)}
h1{font-size:15px;margin:0 0 2px}
.sub{color:var(--dim);font-size:12px;margin-bottom:12px}
#search{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel2);color:var(--tx);margin-bottom:10px}
.sec{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:14px 0 6px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:20px;background:var(--panel2);border:1px solid var(--line);font-size:11px;cursor:pointer;margin:0 4px 4px 0;user-select:none}
.chip .dot{width:8px;height:8px;border-radius:50%}
.chip.off{opacity:.35}
.note{padding:7px 9px;border-radius:8px;cursor:pointer;border:1px solid transparent}
.note:hover{background:var(--panel2)}
.note.sel{background:var(--panel2);border-color:var(--acc)}
.note .t{font-weight:600;font-size:13px}
.note .m{color:var(--dim);font-size:11px}
#graphwrap{position:relative}
canvas{display:block;cursor:grab}
#legend{position:absolute;bottom:10px;left:10px;font-size:11px;color:var(--dim);background:color-mix(in srgb,var(--panel) 80%,transparent);padding:6px 8px;border-radius:8px;border:1px solid var(--line);max-width:60%}
#hud{position:absolute;top:10px;left:10px;font-size:12px;color:var(--dim)}
.card{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:12px}
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.metric{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.metric .n{font-size:20px;font-weight:700}
.metric .l{font-size:10px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.good{color:#a6e3a1}
#detail h2{font-size:16px;margin:0 0 2px}
#detail .badge{display:inline-block;font-size:10px;padding:2px 8px;border-radius:20px;background:var(--panel2);border:1px solid var(--line);color:var(--dim);margin-bottom:8px}
#detail p{color:var(--tx)}
.lnk{display:block;padding:4px 0;color:var(--acc);cursor:pointer;font-size:13px;text-decoration:none}
.lnk:hover{text-decoration:underline}
#theme{position:absolute;top:10px;right:10px;cursor:pointer;background:var(--panel2);border:1px solid var(--line);color:var(--tx);border-radius:8px;padding:4px 8px;font-size:12px}
</style></head><body>
<div id="app">
  <div id="left" class="col">
    <h1>Second Brain</h1>
    <div class="sub">AgentNexLiFy operating memory · __NODES__ notes · __EDGES__ links</div>
    <input id="search" placeholder="Search notes...">
    <div class="sec">Filter by type</div>
    <div id="filters"></div>
    <div class="sec">Notes (<span id="count"></span>)</div>
    <div id="list"></div>
  </div>
  <div id="graphwrap">
    <canvas id="c"></canvas>
    <div id="hud"></div>
    <button id="theme">◐ theme</button>
    <div id="legend"></div>
  </div>
  <div id="right" class="col">
    <div class="card">
      <div class="sec" style="margin-top:0">● Live · Cold Outreach</div>
      <div style="font-weight:600;margin-bottom:8px">__CAMPAIGN__</div>
      <div class="metrics">
        <div class="metric"><div class="n">__LEADS__</div><div class="l">verified leads</div></div>
        <div class="metric"><div class="n">__SENT__</div><div class="l">emails sent</div></div>
        <div class="metric"><div class="n good">__BOUNCED__</div><div class="l">bounced</div></div>
        <div class="metric"><div class="n">__REPLIES__</div><div class="l">replies</div></div>
      </div>
      <div class="m" style="color:var(--dim);font-size:11px;margin-top:8px">__NOTE__</div>
    </div>
    <div id="detail"><div class="sub">Click a node or note to read it.</div></div>
  </div>
</div>
<script>
const DATA=__DATA__, METRICS=__METRICS__;
const COL={person:'#f38ba8',company:'#fab387',product:'#a6e3a1',project:'#89b4fa',topic:'#cba6f7',
decision:'#f9e2af',commitment:'#eba0ac',procedure:'#94e2d5',preference:'#74c7ec','context-pack':'#f5c2e7',
map:'#b4befe',source:'#6c7086',readme:'#9399b2',note:'#9399b2'};
const N={};DATA.nodes.forEach(n=>N[n.id]=n);
const deg={};DATA.edges.forEach(e=>{deg[e.source]=(deg[e.source]||0)+1;deg[e.target]=(deg[e.target]||0)+1});
let active=new Set(Object.keys(COL)), sel=null, query='';

// ---------- filters ----------
const types=[...new Set(DATA.nodes.map(n=>n.type))].sort();
const fEl=document.getElementById('filters');
types.forEach(t=>{const c=document.createElement('span');c.className='chip';
  c.innerHTML='<span class="dot" style="background:'+(COL[t]||COL.note)+'"></span>'+t;
  c.onclick=()=>{active.has(t)?active.delete(t):active.add(t);c.classList.toggle('off');renderList();draw()};
  fEl.appendChild(c)});
const leg=document.getElementById('legend');
leg.innerHTML=types.map(t=>'<span style="color:'+(COL[t]||COL.note)+'">●</span> '+t).join(' &nbsp; ');

// ---------- note list ----------
const listEl=document.getElementById('list'),countEl=document.getElementById('count');
function visible(n){return active.has(n.type)&&(!query||(n.label+' '+n.summary).toLowerCase().includes(query))}
function renderList(){
  const ns=DATA.nodes.filter(visible).sort((a,b)=>(deg[b.id]||0)-(deg[a.id]||0));
  countEl.textContent=ns.length;
  listEl.innerHTML='';
  ns.slice(0,120).forEach(n=>{const d=document.createElement('div');
    d.className='note'+(sel===n.id?' sel':'');
    d.innerHTML='<div class="t">'+esc(n.label)+'</div><div class="m">'+n.type+' · '+(deg[n.id]||0)+' links</div>';
    d.onclick=()=>select(n.id);listEl.appendChild(d)})}
document.getElementById('search').oninput=e=>{query=e.target.value.toLowerCase();renderList();draw()};

// ---------- detail ----------
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function select(id){sel=id;const n=N[id];if(!n)return;
  const links=n.links.filter(l=>N[l]).map(l=>'<a class="lnk" onclick="select(\\''+l.replace(/'/g,"")+'\\')">→ '+esc(N[l].label)+'</a>').join('');
  document.getElementById('detail').innerHTML='<h2>'+esc(n.label)+'</h2><span class="badge">'+n.type+' · '+n.folder+'</span>'+
    '<p>'+esc(n.summary||'(no summary)')+'</p>'+(links?'<div class="sec">Links</div>'+links:'');
  renderList();draw()}

// ---------- graph ----------
const cv=document.getElementById('c'),ctx=cv.getContext('2d');let W,H;
function rs(){const r=cv.parentElement.getBoundingClientRect();W=cv.width=r.width;H=cv.height=r.height}
addEventListener('resize',rs);rs();
DATA.nodes.forEach((n,i)=>{n.x=Math.cos(i*2.4)*Math.min(W,H)*0.4+W/2;n.y=Math.sin(i*2.4)*Math.min(W,H)*0.4+H/2;n.vx=0;n.vy=0});
const E=DATA.edges.filter(e=>N[e.source]&&N[e.target]);
let ox=0,oy=0,z=1,drag=false,lx,ly,moved=false;
cv.onmousedown=e=>{drag=true;moved=false;lx=e.clientX;ly=e.clientY};
addEventListener('mouseup',()=>drag=false);
cv.onmousemove=e=>{if(drag){ox+=e.clientX-lx;oy+=e.clientY-ly;lx=e.clientX;ly=e.clientY;moved=true}};
cv.onwheel=e=>{const f=e.deltaY<0?1.1:0.9;z*=f;e.preventDefault()};
cv.onclick=e=>{if(moved)return;const r=cv.getBoundingClientRect();const mx=(e.clientX-r.left-ox)/z,my=(e.clientY-r.top-oy)/z;
  let best=null,bd=400;for(const n of DATA.nodes){if(!visible(n))continue;const d=(n.x-mx)**2+(n.y-my)**2;if(d<bd){bd=d;best=n}}if(best)select(best.id)};
let ticks=0;
function step(){if(ticks++>320)return;for(const n of DATA.nodes){n.vx*=.86;n.vy*=.86}
  for(let i=0;i<DATA.nodes.length;i++)for(let j=i+1;j<DATA.nodes.length;j++){const a=DATA.nodes[i],b=DATA.nodes[j];
    let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1,f=1400/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
  for(const e of E){const a=N[e.source],b=N[e.target];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-92)*.008;
    a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
  for(const n of DATA.nodes){n.x+=n.vx;n.y+=n.vy}}
function draw(){ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(ox,oy);ctx.scale(z,z);
  const nbr=new Set();if(sel){nbr.add(sel);E.forEach(e=>{if(e.source===sel)nbr.add(e.target);if(e.target===sel)nbr.add(e.source)})}
  for(const e of E){const a=N[e.source],b=N[e.target];if(!visible(a)||!visible(b))continue;
    const on=sel&&(e.source===sel||e.target===sel);
    ctx.strokeStyle=on?'rgba(137,180,250,.7)':'rgba(120,130,160,.16)';ctx.lineWidth=on?1.4/z:0.6/z;
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
  for(const n of DATA.nodes){if(!visible(n))continue;const r=4+Math.min(deg[n.id]||0,11);
    const dim=sel&&!nbr.has(n.id);ctx.globalAlpha=dim?0.28:1;
    ctx.fillStyle=COL[n.type]||COL.note;ctx.beginPath();ctx.arc(n.x,n.y,r,0,7);ctx.fill();
    if(n.id===sel){ctx.strokeStyle='#fff';ctx.lineWidth=2/z;ctx.stroke()}
    if(z>0.75||n.id===sel){ctx.globalAlpha=dim?0.4:1;ctx.fillStyle=getComputedStyle(document.body).color;
      ctx.font=(10/z<3?10:10)+'px system-ui';ctx.fillText(n.label,n.x+r+3,n.y+3)}}
  ctx.globalAlpha=1;ctx.restore()}
document.getElementById('hud').textContent='drag to pan · scroll to zoom · click a node';
function loop(){step();draw();requestAnimationFrame(loop)}loop();
document.getElementById('theme').onclick=()=>{const r=document.documentElement;
  const cur=r.getAttribute('data-theme');r.setAttribute('data-theme',cur==='light'?'dark':'light')};
renderList();
</script></body></html>"""


def main():
    notes = collect()
    graph = build_graph(notes)
    # keep _index/graph.json in sync too
    json.dump(graph, open(os.path.join(ROOT, "_index", "graph.json"), "w"),
              ensure_ascii=False)
    page = (TEMPLATE
            .replace("__DATA__", json.dumps(graph, ensure_ascii=False))
            .replace("__METRICS__", json.dumps(METRICS))
            .replace("__NODES__", str(len(graph["nodes"])))
            .replace("__EDGES__", str(len(graph["edges"])))
            .replace("__CAMPAIGN__", html.escape(METRICS["campaign"]))
            .replace("__LEADS__", str(METRICS["leads"]))
            .replace("__SENT__", str(METRICS["sent"]))
            .replace("__BOUNCED__", str(METRICS["bounced"]))
            .replace("__REPLIES__", str(METRICS["replies"]))
            .replace("__NOTE__", html.escape(METRICS["note"])))
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"dashboard: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges -> {OUT}")


if __name__ == "__main__":
    main()
