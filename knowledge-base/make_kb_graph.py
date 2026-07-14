#!/usr/bin/env python3
"""Knowledge graph of the AgentNexLiFy knowledge base (wiki), body-only Artifact."""
import json, os, re, html

WIKI = "/home/user/agentnexlify/knowledge-base/wiki"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_index", "kb-graph.html")
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
FM = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def fm_field(block, key):
    m = re.search(rf"^{key}:\s*(.+)$", block, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else ""


arts = {}   # stem -> record
for dp, _, files in os.walk(WIKI):
    if "_outputs" in dp:
        continue
    for f in files:
        if not f.endswith(".md") or f.startswith("_"):
            continue
        text = open(os.path.join(dp, f), encoding="utf-8").read()
        stem = f[:-3]
        m = FM.match(text)
        block = m.group(1) if m else ""
        cat = fm_field(block, "category") or os.path.basename(dp)
        title = fm_field(block, "title") or stem.replace("-", " ")
        summ = fm_field(block, "summary")
        tags = fm_field(block, "tags").strip("[]")
        arts[stem] = {"id": stem, "label": title, "cat": cat,
                      "summary": summ, "tags": tags,
                      "raw": text, "links": []}

by_title = {a["label"].lower(): sid for sid, a in arts.items()}
for sid, a in arts.items():
    targets = set()
    for t in WIKILINK.findall(a["raw"]):
        t = t.strip()
        tid = t if t in arts else by_title.get(t.lower())
        if tid and tid != sid:
            targets.add(tid)
    a["links"] = sorted(targets)

nodes = [{"id": a["id"], "label": a["label"], "cat": a["cat"],
          "summary": a["summary"], "tags": a["tags"], "links": a["links"]}
         for a in arts.values()]
edges, seen = [], set()
for a in arts.values():
    for t in a["links"]:
        k = tuple(sorted((a["id"], t)))
        if k not in seen:
            seen.add(k)
            edges.append({"source": a["id"], "target": t})
graph = {"nodes": nodes, "edges": edges}

cats = {}
for a in arts.values():
    cats[a["cat"]] = cats.get(a["cat"], 0) + 1
stats = {"articles": len(arts), "links": len(edges), "cats": len(cats)}

BODY = r"""
<style>
:root{--bg:#0f1016;--panel:#171922;--panel2:#1e212e;--line:#2a2f40;--tx:#e9ecf6;--dim:#969fbc;--faint:#68718e;
  --acc:#7c8cf8;--acc-soft:#7c8cf822;--grid:#ffffff0d;--shadow:0 8px 24px #00000045}
:root[data-theme="light"]{--bg:#f6f7fb;--panel:#fff;--panel2:#eef1f8;--line:#dde3f1;--tx:#161c2b;--dim:#525c78;--faint:#8791a8;
  --acc:#4b5bd4;--acc-soft:#4b5bd414;--grid:#0f101610;--shadow:0 8px 24px #16223012}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){--bg:#f6f7fb;--panel:#fff;--panel2:#eef1f8;--line:#dde3f1;
  --tx:#161c2b;--dim:#525c78;--faint:#8791a8;--acc:#4b5bd4;--acc-soft:#4b5bd414;--grid:#0f101610;--shadow:0 8px 24px #16223012}}
*{box-sizing:border-box}
#kb{--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  position:fixed;inset:0;background:var(--bg);color:var(--tx);font-family:var(--sans);font-size:14px;
  display:grid;grid-template-columns:262px 1fr 322px;overflow:hidden}
#kb *{scrollbar-width:thin;scrollbar-color:var(--line) transparent}
.pane{overflow:auto;min-height:0}
#kb-left{border-right:1px solid var(--line);background:var(--panel);padding:18px 14px}
#kb-right{border-left:1px solid var(--line);background:var(--panel);padding:16px 14px}
.eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.wordmark{font-size:17px;font-weight:680;letter-spacing:-.02em;margin:2px 0 1px}
.metaline{font-family:var(--mono);font-size:11px;color:var(--dim);margin-bottom:14px}
.metaline b{color:var(--tx)}
#kb-search{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:9px;background:var(--panel2);color:var(--tx);font-size:13px;outline:none}
#kb-search:focus{border-color:var(--acc);box-shadow:0 0 0 3px var(--acc-soft)}
.grouphdr{margin:18px 0 7px;display:flex;justify-content:space-between;align-items:baseline}
.filters{display:flex;flex-wrap:wrap;gap:5px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:7px;background:var(--panel2);
  border:1px solid var(--line);font-size:11px;cursor:pointer;user-select:none;font-family:var(--mono)}
.chip:hover{border-color:var(--acc)}.chip .dot{width:8px;height:8px;border-radius:2px}.chip.off{opacity:.32}
.chip:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
.count{font-family:var(--mono);font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
#kb-list{display:flex;flex-direction:column;gap:2px}
.item{padding:8px 9px;border-radius:8px;cursor:pointer;border:1px solid transparent}
.item:hover{background:var(--panel2)}.item.sel{background:var(--acc-soft);border-color:var(--acc)}
.item .t{font-weight:600;font-size:13px;letter-spacing:-.01em}
.item .m{font-family:var(--mono);font-size:10.5px;color:var(--dim);margin-top:1px}
#kb-stage{position:relative;background:radial-gradient(circle at 50% 42%,color-mix(in srgb,var(--acc) 6%,transparent),transparent 60%),var(--bg)}
#kb-canvas{display:block;cursor:grab}#kb-canvas:active{cursor:grabbing}
#kb-hint{position:absolute;top:14px;left:16px;font-family:var(--mono);font-size:11px;color:var(--faint);pointer-events:none}
#kb-legend{position:absolute;bottom:12px;left:14px;right:14px;display:flex;flex-wrap:wrap;gap:4px 12px;font-family:var(--mono);font-size:10.5px;color:var(--dim);pointer-events:none}
#kb-legend i{width:8px;height:8px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:middle}
.bars{margin:2px 0 4px}
.bar{display:grid;grid-template-columns:96px 1fr 26px;align-items:center;gap:8px;margin:5px 0;font-size:12px}
.bar .cap{color:var(--dim);font-family:var(--mono);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .track{height:7px;background:var(--panel2);border-radius:4px;overflow:hidden}.bar .fill{height:100%;border-radius:4px}
.bar .v{font-family:var(--mono);font-size:11px;color:var(--dim);text-align:right;font-variant-numeric:tabular-nums}
.sec{font-family:var(--mono);font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--faint);margin:16px 0 8px}
#kb-detail{border-top:1px solid var(--line);margin-top:14px;padding-top:14px}
#kb-detail .ph{color:var(--dim);font-size:13px}
#kb-detail h2{font-size:16px;letter-spacing:-.01em;margin:2px 0 7px;text-wrap:balance;line-height:1.3}
.badge{display:inline-flex;gap:6px;align-items:center;font-family:var(--mono);font-size:10px;letter-spacing:.05em;
  padding:3px 9px;border-radius:20px;background:var(--panel2);border:1px solid var(--line);color:var(--dim);text-transform:uppercase}
#kb-detail p.sum{color:var(--tx);font-size:13px;margin:12px 0}
.tags{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
.tag{font-family:var(--mono);font-size:10px;color:var(--dim);background:var(--panel2);border:1px solid var(--line);border-radius:5px;padding:2px 6px}
.linkhdr{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin:14px 0 4px}
.lnk{display:flex;align-items:center;gap:7px;padding:5px 8px;margin:0 -8px;border-radius:7px;color:var(--acc);cursor:pointer;font-size:13px}
.lnk:hover{background:var(--acc-soft)}.lnk .ld{width:7px;height:7px;border-radius:2px;flex:none}
@media (max-width:920px){#kb{position:static;height:auto;grid-template-columns:1fr}#kb-stage{height:56vh}
  #kb-left,#kb-right{border:0;border-bottom:1px solid var(--line)}}
</style>
<div id="kb">
  <aside id="kb-left" class="pane">
    <div class="eyebrow">AgentNexLiFy</div>
    <div class="wordmark">Knowledge Base</div>
    <div class="metaline"><b id="kb-na"></b> articles · <b id="kb-nl"></b> links · LLM-compiled wiki</div>
    <input id="kb-search" placeholder="Search titles, summaries, tags…" aria-label="Search articles">
    <div class="grouphdr"><span class="eyebrow">Category</span></div>
    <div class="filters" id="kb-filters"></div>
    <div class="grouphdr"><span class="eyebrow">Articles</span><span class="count" id="kb-count"></span></div>
    <div id="kb-list"></div>
  </aside>
  <main id="kb-stage">
    <canvas id="kb-canvas"></canvas>
    <div id="kb-hint">drag to pan · scroll to zoom · click a node to open</div>
    <div id="kb-legend"></div>
  </main>
  <aside id="kb-right" class="pane">
    <div class="eyebrow">Coverage by category</div>
    <div class="bars" id="kb-bars"></div>
    <div id="kb-detail"><div class="ph">Click a node or article to read its summary and follow citations.</div></div>
  </aside>
</div>
<script>
(function(){
const DATA=__DATA__;
const COL={'ai-llm':'#7c8cf8','competitors':'#e0796f','growth':'#57c98a','regulations':'#e6b566',
  'small-biz-saas':'#6fb0e0','technical':'#78c8c0','verticals':'#c58ce0','_outputs':'#8089a8'};
const fallback='#8089a8';
const $=id=>document.getElementById(id);
const N={};DATA.nodes.forEach(n=>N[n.id]=n);
const deg={};DATA.edges.forEach(e=>{deg[e.source]=(deg[e.source]||0)+1;deg[e.target]=(deg[e.target]||0)+1});
let active=new Set(DATA.nodes.map(n=>n.cat)), sel=null, query='';
$('kb-na').textContent=DATA.nodes.length;$('kb-nl').textContent=DATA.edges.length;

const cats={};DATA.nodes.forEach(n=>cats[n.cat]=(cats[n.cat]||0)+1);
const catList=Object.keys(cats).sort((a,b)=>cats[b]-cats[a]);
const fEl=$('kb-filters');
catList.forEach(c=>{const b=document.createElement('button');b.className='chip';b.type='button';
  b.innerHTML='<span class="dot" style="background:'+(COL[c]||fallback)+'"></span>'+c;
  b.onclick=()=>{active.has(c)?active.delete(c):active.add(c);b.classList.toggle('off');renderList();draw()};fEl.appendChild(b);});
$('kb-legend').innerHTML=catList.map(c=>'<span><i style="background:'+(COL[c]||fallback)+'"></i>'+c+'</span>').join('');
const mx=Math.max(...Object.values(cats));
$('kb-bars').innerHTML=catList.map(c=>'<div class="bar"><span class="cap">'+c+'</span>'+
  '<span class="track"><span class="fill" style="width:'+(cats[c]/mx*100)+'%;background:'+(COL[c]||fallback)+'"></span></span>'+
  '<span class="v">'+cats[c]+'</span></div>').join('');

const visible=n=>active.has(n.cat)&&(!query||(n.label+' '+n.summary+' '+n.tags).toLowerCase().includes(query));
const listEl=$('kb-list'),countEl=$('kb-count');
function renderList(){const ns=DATA.nodes.filter(visible).sort((a,b)=>(deg[b.id]||0)-(deg[a.id]||0));
  countEl.textContent=ns.length;listEl.innerHTML='';
  ns.slice(0,150).forEach(n=>{const d=document.createElement('div');d.className='item'+(sel===n.id?' sel':'');d.tabIndex=0;
    d.innerHTML='<div class="t">'+esc(n.label)+'</div><div class="m">'+n.cat+' · '+(deg[n.id]||0)+' links</div>';
    d.onclick=()=>select(n.id);d.onkeydown=e=>{if(e.key==='Enter')select(n.id)};listEl.appendChild(d);});}
$('kb-search').oninput=e=>{query=e.target.value.toLowerCase();renderList();draw()};

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function select(id){sel=id;const n=N[id];if(!n)return;
  const tags=n.tags?('<div class="tags">'+n.tags.split(',').map(t=>t.trim()).filter(Boolean).slice(0,8).map(t=>'<span class="tag">'+esc(t)+'</span>').join('')+'</div>'):'';
  const links=n.links.filter(l=>N[l]).map(l=>'<div class="lnk" tabindex="0" role="button" data-id="'+esc(l)+'">'+
    '<span class="ld" style="background:'+(COL[N[l].cat]||fallback)+'"></span>'+esc(N[l].label)+'</div>').join('');
  $('kb-detail').innerHTML='<h2>'+esc(n.label)+'</h2><span class="badge">'+
    '<span class="ld" style="width:7px;height:7px;border-radius:2px;background:'+(COL[n.cat]||fallback)+'"></span>'+n.cat+'</span>'+
    '<p class="sum">'+esc(n.summary||'(no summary)')+'</p>'+tags+
    (links?'<div class="linkhdr">Cites / linked ('+links.length+')</div>'+links:'');
  $('kb-detail').querySelectorAll('.lnk').forEach(el=>{const go=()=>select(el.getAttribute('data-id'));el.onclick=go;el.onkeydown=e=>{if(e.key==='Enter')go()};});
  renderList();draw();}

const cv=$('kb-canvas'),ctx=cv.getContext('2d');let W,H,DPR=Math.min(devicePixelRatio||1,2);
function rs(){const r=cv.parentElement.getBoundingClientRect();W=r.width;H=r.height;cv.width=W*DPR;cv.height=H*DPR;cv.style.width=W+'px';cv.style.height=H+'px'}
addEventListener('resize',()=>{rs();draw()});rs();
DATA.nodes.forEach((n,i)=>{const a=i*2.399;n.x=Math.cos(a)*Math.min(W,H)*.4+W/2;n.y=Math.sin(a)*Math.min(W,H)*.4+H/2;n.vx=0;n.vy=0});
const E=DATA.edges.filter(e=>N[e.source]&&N[e.target]);
let ox=0,oy=0,z=.85,drag=false,lx,ly,moved=false;
cv.onmousedown=e=>{drag=true;moved=false;lx=e.clientX;ly=e.clientY};addEventListener('mouseup',()=>drag=false);
cv.onmousemove=e=>{if(drag){ox+=e.clientX-lx;oy+=e.clientY-ly;lx=e.clientX;ly=e.clientY;moved=true}};
cv.onwheel=e=>{const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,f=e.deltaY<0?1.12:.89;ox=mx-(mx-ox)*f;oy=my-(my-oy)*f;z*=f;e.preventDefault();draw()};
cv.onclick=e=>{if(moved)return;const r=cv.getBoundingClientRect(),mx=(e.clientX-r.left-ox)/z,my=(e.clientY-r.top-oy)/z;
  let best=null,bd=520;for(const n of DATA.nodes){if(!visible(n))continue;const d=(n.x-mx)**2+(n.y-my)**2;if(d<bd){bd=d;best=n}}if(best)select(best.id)};
const css=v=>getComputedStyle(document.body).getPropertyValue(v).trim()||'#888';
function draw(){ctx.setTransform(DPR,0,0,DPR,0,0);ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(ox,oy);ctx.scale(z,z);
  const nb=new Set();if(sel){nb.add(sel);E.forEach(e=>{if(e.source===sel)nb.add(e.target);if(e.target===sel)nb.add(e.source)})}
  for(const e of E){const a=N[e.source],b=N[e.target];if(!visible(a)||!visible(b))continue;const on=sel&&(e.source===sel||e.target===sel);
    ctx.strokeStyle=on?css('--acc'):css('--grid');ctx.lineWidth=(on?1.4:0.6)/z;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
  const label=css('--tx');
  for(const n of DATA.nodes){if(!visible(n))continue;const r=3.5+Math.min(deg[n.id]||0,14)*0.7;const dim=sel&&!nb.has(n.id);
    ctx.globalAlpha=dim?0.2:1;ctx.fillStyle=COL[n.cat]||fallback;ctx.beginPath();ctx.arc(n.x,n.y,r,0,7);ctx.fill();
    if(n.id===sel){ctx.strokeStyle=label;ctx.lineWidth=2/z;ctx.stroke()}
    if((z>0.9&&(deg[n.id]||0)>=4)||n.id===sel){ctx.globalAlpha=dim?.35:.92;ctx.fillStyle=label;
      ctx.font='11px ui-monospace,monospace';let t=n.label.length>34?n.label.slice(0,32)+'…':n.label;ctx.fillText(t,n.x+r+4,n.y+3.5)}}
  ctx.globalAlpha=1;ctx.restore()}
const reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;let ticks=0;
function step(){if(ticks++>360)return false;for(const n of DATA.nodes){n.vx*=.86;n.vy*=.86}
  for(let i=0;i<DATA.nodes.length;i++)for(let j=i+1;j<DATA.nodes.length;j++){const a=DATA.nodes[i],b=DATA.nodes[j];
    let dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy)||1;if(d>420)continue;let f=1500/(d*d);a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
  for(const e of E){const a=N[e.source],b=N[e.target];let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,f=(d-96)*.008;
    a.vx+=dx/d*f;a.vy+=dy/d*f;b.vx-=dx/d*f;b.vy-=dy/d*f}
  for(const n of DATA.nodes){n.x+=n.vx;n.y+=n.vy}return true}
if(reduce){for(let k=0;k<360;k++)step();draw()}else{(function loop(){const m=step();draw();if(m)requestAnimationFrame(loop)})()}
renderList();
})();
</script>
"""
page = BODY.replace("__DATA__", json.dumps(graph, ensure_ascii=False))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(page)
print(f"KB graph: {len(nodes)} articles, {len(edges)} links, {len(cats)} categories -> {OUT}")
print("by category:", dict(sorted(cats.items(), key=lambda x:-x[1])))
