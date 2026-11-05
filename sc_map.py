"""Starmap section: where you've been, drawn on the real layout of Stanton, Pyro and Nyx.

Positions come from the game's own files and services from UEX Corp; both are baked into
sc_map.json by tools/build_map.py. This module only hands the page its data, CSS and
script. sc_stats.py injects them, so the map stays out of the main file as far as it can.
"""
import json
import os

MAP_FILE = "sc_map.json"


def map_payload(resource_dir):
    """The sc_map.json text for the page, or 'null' if it was never built."""
    path = os.path.join(resource_dir, MAP_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return "null"
    return json.dumps(data, separators=(",", ":")).replace("</", "<\\/")


MAP_NAV = '<a data-sec="starmap" data-label="Starmap"><span>🪐</span> Starmap</a>'

MAP_ICON = ("starmap:_SVG('<circle cx=\"12\" cy=\"12\" r=\"3.2\"/>"
            "<ellipse cx=\"12\" cy=\"12\" rx=\"9.5\" ry=\"4.2\" transform=\"rotate(-24 12 12)\"/>"
            "<circle cx=\"19.6\" cy=\"8.4\" r=\"1.3\" fill=\"currentColor\" stroke=\"none\"/>'),")

MAP_CSS = r"""
/* ---- Starmap (fork addition) ---- */
.scm{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px;align-items:start}
@media (max-width:1180px){.scm{grid-template-columns:minmax(0,1fr)}}
.scm-map{border-radius:var(--r-lg);overflow:hidden;background:#03080d;border:1px solid #10384d;
  box-shadow:0 0 0 1px rgba(33,230,255,.04),0 10px 40px rgba(0,0,0,.35)}
.scm-bar{display:flex;gap:8px 10px;align-items:center;padding:10px 14px;border-bottom:1px solid #10384d;
  background:#050d13;flex-wrap:wrap;font:12px var(--font-mono,ui-monospace,monospace)}
.scm-crumb{display:flex;gap:4px;align-items:center;color:#4f7f93}
.scm-crumb button{background:none;border:0;color:#7fbfd6;cursor:pointer;font:600 11.5px var(--font-mono,ui-monospace,monospace);
  letter-spacing:.12em;text-transform:uppercase;padding:3px 4px;border-radius:4px}
.scm-crumb button:hover{color:#dff9ff;background:#0d2a3a}
.scm-crumb button.cur{color:#21e6ff;text-shadow:0 0 8px rgba(33,230,255,.55);cursor:default;background:none}
.scm-sp{flex:1}
.scm-find{background:#02060a;border:1px solid #133c52;border-radius:6px;color:#cdefff;padding:5px 9px;
  font:12px var(--font-mono,ui-monospace,monospace);width:210px}
.scm-find::placeholder{color:#3f6a7c}
.scm-chips{display:flex;gap:6px;flex-wrap:wrap;padding:8px 14px;border-bottom:1px solid #10384d;background:#040b10}
.scm-chip{border:1px solid #133c52;background:#06141d;color:#7fbfd6;border-radius:999px;padding:3px 10px;
  font:600 10.5px var(--font-mono,ui-monospace,monospace);letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
  display:inline-flex;gap:6px;align-items:center}
.scm-chip i{width:8px;height:8px;border-radius:50%;display:inline-block}
.scm-chip.on{background:#0d2a3a;border-color:#21a6d6;color:#dff9ff}
.scm-chip .n{color:#4f8aa1;font-weight:500}
.scm-wrap{position:relative;width:100%;aspect-ratio:4/3;min-height:460px;max-height:78vh;
  background:radial-gradient(ellipse at 50% 45%,#071a26 0%,#02060a 72%)}
.scm-wrap canvas{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}
.scm-wrap canvas.drag{cursor:grabbing}
.scm-wrap::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(0deg,rgba(0,0,0,.22) 0 1px,transparent 1px 3px)}
.scm-hud{position:absolute;z-index:2;font:600 10.5px var(--font-mono,ui-monospace,monospace);letter-spacing:.12em;
  color:#7fdcff;text-transform:uppercase;display:flex;flex-direction:column;gap:3px;pointer-events:none}
.scm-hud b{color:#21e6ff;font-size:12px;letter-spacing:.2em;text-shadow:0 0 8px rgba(33,230,255,.6)}
.scm-hud.tl{top:12px;left:14px;background:rgba(2,6,10,.7);padding:5px 9px;border-radius:4px}
.scm-hud.tr{top:12px;right:14px;text-align:right;color:#ffb22e;text-shadow:0 0 6px rgba(255,178,46,.5)}
.scm-legend{display:flex;gap:6px 18px;justify-content:space-between;flex-wrap:wrap;padding:8px 14px;border-top:1px solid #10384d;
  background:#040b10;font:600 10px var(--font-mono,ui-monospace,monospace);letter-spacing:.07em;text-transform:uppercase}
#scmBL{display:flex;flex-wrap:wrap;gap:4px 14px;color:#6aa9c2}
#scmBL i{display:inline-block;width:9px;height:9px;margin-right:5px;vertical-align:-1px}
#scmBR{color:#4f8aa1;text-align:right}
.scm-tip{position:absolute;z-index:4;pointer-events:none;background:rgba(3,12,18,.95);border:1px solid #1d6a8c;
  border-radius:6px;padding:8px 10px;font:12px/1.5 var(--font-mono,ui-monospace,monospace);color:#cdefff;min-width:200px;
  max-width:300px;box-shadow:0 0 16px rgba(33,230,255,.15);transform:translate(14px,-50%)}
.scm-tip b{color:#fff;font-size:12.5px}.scm-tip .d{color:#6aa9c2}.scm-tip .v{color:#21e6ff}.scm-tip .h{color:#ffb000}
.scm-foot{padding:8px 14px 10px;border-top:1px solid #10384d;color:#4f8aa1;font:11.5px var(--font-mono,ui-monospace,monospace);
  display:flex;gap:6px 18px;flex-wrap:wrap;background:#03080d}
.scm-foot b{color:#bdf3ff;font-weight:600}
.scm-side{display:flex;flex-direction:column;gap:18px;min-width:0}
.scm-side .card{padding:18px 20px}
.scm-kind{font:600 10.5px var(--font-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.scm-name{font-size:19px;font-weight:600;margin:3px 0 2px;line-height:1.25}
.scm-sub{color:var(--dim);font-size:12.5px}
.scm-vis{display:flex;gap:16px;margin:14px 0 4px;flex-wrap:wrap}
.scm-vis div{display:flex;flex-direction:column}
.scm-vis b{font:600 20px var(--font-mono);color:var(--cyan)}
.scm-vis span{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
.scm-sec{margin-top:16px}
.scm-sec h4{margin:0 0 8px;font:600 10.5px var(--font-mono);letter-spacing:.14em;color:var(--dim);text-transform:uppercase}
.scm-svc{display:flex;flex-wrap:wrap;gap:6px}
.scm-svc span{font:600 10.5px var(--font-mono);letter-spacing:.06em;padding:2px 8px;border-radius:999px;
  border:1px solid var(--glass-line);color:var(--text)}
.scm-svc span i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:6px;vertical-align:0}
.scm-shops{margin:8px 0 0;padding:0;list-style:none;font-size:12.5px;color:var(--dim)}
.scm-shops li{padding:2px 0}.scm-shops li b{color:var(--text);font-weight:550}
.scm-list{display:flex;flex-direction:column;gap:2px;max-height:330px;overflow:auto;margin:0 -6px}
.scm-list button{display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:9px;align-items:center;text-align:left;
  background:none;border:0;border-radius:7px;padding:5px 6px;cursor:pointer;color:var(--text);font-size:13px}
.scm-list button:hover{background:var(--hover-tint)}
.scm-list .dot{width:8px;height:8px;border-radius:50%;background:#2c4554}
.scm-list .dot.on{background:#21e6ff;box-shadow:0 0 6px #21e6ff}.scm-list .dot.home{background:#ffb000;box-shadow:0 0 6px #ffb000}
.scm-list .c{font:12px var(--font-mono);color:var(--dim)}
.scm-list .s{display:block;font-size:11.5px;color:var(--dim)}
.scm-empty{color:var(--dim);font-size:12.5px}
.scm-note{font-size:12px;color:var(--dim);line-height:1.5;margin-top:10px}
"""

MAP_JS = r"""
// ==== Starmap (fork addition) =============================================
// Real layout from the game files, services from UEX, visits from your logs.
const SCM_SVC = [  // key, chip label, colour
  ['refuel','Fuel','#ffb000'], ['ships','Ship dealer','#ff3df2'], ['rental','Rentals','#c99bff'],
  ['fps','Arms & armour','#ff5d5d'], ['parts','Ship parts','#39ff88'], ['repair','Repair','#7fbfd6'],
  ['clinic','Medical','#5dffd8'], ['trade_terminal','Trade','#ffe066'], ['refinery','Refinery','#ff9a3d'],
];
const SCM_SVC_LBL = Object.fromEntries(SCM_SVC.map(s=>[s[0],s[1]]));
const SCM_SVC_COL = Object.fromEntries(SCM_SVC.map(s=>[s[0],s[2]]));
const SCM_SHOP_LBL = {ships:'Ship dealers', rental:'Rentals', fps:'Arms & armour', parts:'Ship parts', shop:'Other shops'};
const SCM_TYPE = {star:'Star', planet:'Planet', moon:'Moon', station:'Station', lagrange:'Lagrange point',
  city:'Landing zone', gate:'Jump gate'};
const SCM_GAL = {  // the galaxy view is a diagram, not the real starmap
  stanton:{x:0, y:0, name:'Stanton', sub:'UEE'}, pyro:{x:-.62, y:-.46, name:'Pyro', sub:'Unclaimed'},
  nyx:{x:-.7, y:.48, name:'Nyx', sub:'Unclaimed'}, terra:{x:.72, y:.1, name:'Terra', sub:'Gate closed', closed:true},
};
const SCM = {view:{lvl:'galaxy'}, sel:null, svc:new Set(), zoom:1, panX:0, panY:0, hits:[], hover:null,
  raf:0, t0:performance.now(), idx:null};
const scmE = s => String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function scmIndex(){
  if(SCM.idx || !SCMAP) return SCM.idx;
  const byId={}, byCode={}, kids={};
  SCMAP.nodes.forEach(n=>{ byId[n.id]=n; (n.codes||[]).forEach(c=>byCode[c.toLowerCase()]=n.id);
    if(n.parent) (kids[n.parent]=kids[n.parent]||[]).push(n.id); });
  return SCM.idx={byId, byCode, kids};
}
// which body a surface location code belongs to: Stanton1b_..., Pyro4_..., Nyx_...
function scmBodyOf(code){
  const m=/^(stanton\d[a-d]?|pyro\d[a-f]?)_/i.exec(code);
  return m ? m[1].toLowerCase() : null;
}
// visits in the current scope: node id -> {n, first, last, codes}; body id -> surface rows
function scmVisits(v){
  const I=scmIndex(), out={node:{}, surface:{}, other:[]};
  const pc=(v&&v.place_codes)||{};
  for(const [code,row] of Object.entries(pc)){
    const [n,first,last,name,sys,kind]=row;
    const id=I.byCode[code.toLowerCase()];
    if(id){ const o=out.node[id]=out.node[id]||{n:0,first:null,last:null};
      o.n+=n; if(first&&(!o.first||first<o.first)) o.first=first; if(last&&(!o.last||last>o.last)) o.last=last; continue; }
    const b=scmBodyOf(code);
    const rec={code, n, first, last, name:name||code, kind:kind||''};
    if(b && I.byId[b]) (out.surface[b]=out.surface[b]||[]).push(rec); else out.other.push(rec);
  }
  // a body counts as visited if you landed anywhere on it
  for(const [b,rows] of Object.entries(out.surface)){
    const o=out.node[b]=out.node[b]||{n:0,first:null,last:null,surf:true};
    rows.forEach(r=>{ o.n+=r.n; if(r.first&&(!o.first||r.first<o.first)) o.first=r.first; if(r.last&&(!o.last||r.last>o.last)) o.last=r.last; });
  }
  // planets and moons light up when you stopped anywhere on or around them
  out.roll={};
  const I2=scmIndex();
  for(const [id,o] of Object.entries(out.node)){ let p=I2.byId[id]; const seen=new Set();
    while(p&&p.parent&&!seen.has(p.parent)){ seen.add(p.parent); const q=I2.byId[p.parent]; if(!q||q.type==='star') break;
      const r=out.roll[q.id]=out.roll[q.id]||{stops:0,places:0}; r.stops+=o.n; r.places+=1; p=q; } }
  for(const [b,rows] of Object.entries(out.surface)){ const r=out.roll[b]=out.roll[b]||{stops:0,places:0}; r.places+=rows.length; }
  let home=null; for(const [id,o] of Object.entries(out.node)){ const t=I.byId[id].type;
    if(t!=='planet'&&t!=='moon'&&(!home||o.n>out.node[home].n)) home=id; }
  out.home=home;
  return out;
}
const scmSys = s => (SCMAP.systems||{})[s];
function scmBodyR(n){ return n.r_km || (n.type==='planet'? (n.sys==='pyro'&&n.id==='pyro5'?3800:900) : 200); }

function secStarmap(v){
  const c=$('#content');
  if(typeof SCMAP==='undefined'||!SCMAP){ c.innerHTML=`<div class="card"><h3>Starmap</h3><p class="scm-empty">The map data
    (sc_map.json) is missing. Build it with <code>python tools/build_map.py &lt;LIVE/Data.p4k&gt;</code>.</p></div>`; return; }
  SCM.vis=scmVisits(v);
  const I=scmIndex(), V=SCM.vis, onMap=SCMAP.nodes.filter(n=>!['star','planet','moon'].includes(n.type)&&(n.kind||n.type!=='lagrange'));
  const docked=onMap.filter(n=>V.node[n.id]).length;
  const systems=new Set(Object.keys(V.node).map(id=>I.byId[id].sys)).size;
  const gates=SCMAP.nodes.filter(n=>n.type==='gate').reduce((a,n)=>a+((V.node[n.id]||{}).n||0),0);
  const home=V.home?I.byId[V.home]:null;
  const kp=(typeof kpiRow==='function')?kpiRow([
    [icon('planet'), `${docked}<span style="font-size:.55em;color:var(--dim)"> / ${onMap.length}</span>`, 'Stations & cities', 'docked or landed at least once'],
    [icon('space'), `${systems}<span style="font-size:.55em;color:var(--dim)"> / 3</span>`, 'Systems', 'with a stop logged'],
    [icon('flight'), fmt(gates), 'Gate stops', 'sessions docked at a jump gate'],
    [icon('ship'), home?scmE(home.name):'—', 'Home base', home?`${V.node[home.id].n} sessions`:'no stops logged'],
  ]):'';
  c.innerHTML=kp+`<div class="scm">
    <div class="scm-map">
      <div class="scm-bar"><div class="scm-crumb" id="scmCrumb"></div><span class="scm-sp"></span>
        <input class="scm-find" id="scmFind" type="search" placeholder="Find a place…" list="scmList" aria-label="Find a place">
        <datalist id="scmList"></datalist></div>
      <div class="scm-chips" id="scmChips"></div>
      <div class="scm-wrap" id="scmWrap"><canvas id="scmCv"></canvas>
        <div class="scm-hud tl" id="scmTL"></div><div class="scm-hud tr" id="scmTR"></div>
        <div class="scm-tip" id="scmTip" hidden></div></div>
      <div class="scm-legend"><div id="scmBL"></div><div id="scmBR"></div></div>
      <div class="scm-foot" id="scmFoot"></div>
    </div>
    <div class="scm-side"><div class="card" id="scmPanel"></div><div class="card" id="scmList2"></div></div>
  </div>`;
  $('#scmList').innerHTML=SCMAP.nodes.filter(n=>n.type!=='star'&&n.name).map(n=>`<option value="${scmE(n.name)}">`).join('');
  $('#scmFind').onchange=e=>{ const q=e.target.value.trim().toLowerCase();
    const n=SCMAP.nodes.find(n=>(n.name||'').toLowerCase()===q) || SCMAP.nodes.find(n=>(n.name||'').toLowerCase().includes(q));
    if(n){ scmFocus(n); e.target.value=''; } };
  scmChips(); scmBind(); scmGo(SCM.view, true);
  cancelAnimationFrame(SCM.raf); SCM.raf=requestAnimationFrame(scmFrame);
}

function scmChips(){
  const cnt=k=>SCMAP.nodes.filter(n=>n.svc&&n.svc[k]).length;
  $('#scmChips').innerHTML=SCM_SVC.map(([k,l,c])=>`<button type="button" class="scm-chip ${SCM.svc.has(k)?'on':''}" data-k="${k}">
    <i style="background:${c};box-shadow:0 0 6px ${c}"></i>${l} <span class="n">${cnt(k)}</span></button>`).join('')+
    (SCM.svc.size?`<button type="button" class="scm-chip" data-k="">Clear</button>`:'');
  document.querySelectorAll('#scmChips .scm-chip').forEach(b=>b.onclick=()=>{
    const k=b.dataset.k; if(!k) SCM.svc.clear(); else SCM.svc.has(k)?SCM.svc.delete(k):SCM.svc.add(k);
    scmChips(); scmSide(); });
}
const scmMatch = n => !SCM.svc.size || [...SCM.svc].every(k=>n.svc&&n.svc[k]);
// a planet or moon "has" a service when something around it does (its stations, cities, moons)
function scmDeep(n){ if(!SCM.svc.size) return false; const I=scmIndex(), st=[n.id], seen=new Set();
  while(st.length){ const id=st.pop(); if(seen.has(id)) continue; seen.add(id);
    for(const k of (I.kids[id]||[])){ const m=I.byId[k]; if(m.type!=='lagrange'&&scmMatch(m)&&m.svc) return true; st.push(k); } }
  return false; }

// ---- navigation
function scmGo(view, keepSel){
  SCM.view=view; SCM.zoom=1; SCM.panX=0; SCM.panY=0; if(!keepSel) SCM.sel=null;
  const I=scmIndex(), parts=[['Galaxy',{lvl:'galaxy'}]];
  if(view.sys) parts.push([scmSys(view.sys).name+' system',{lvl:'system',sys:view.sys}]);
  if(view.lvl==='body'){ const b=I.byId[view.id], p=b.parent&&I.byId[b.parent];
    if(p&&p.type!=='star') parts.push([p.name,{lvl:'body',sys:view.sys,id:p.id}]);
    parts.push([b.name,view]); }
  const cr=$('#scmCrumb'); if(!cr) return;
  cr.innerHTML=parts.map(([l],i)=>`${i?'<span>›</span>':''}<button type="button" class="${i===parts.length-1?'cur':''}" data-i="${i}">${scmE(l)}</button>`).join('');
  cr.querySelectorAll('button').forEach(b=>b.onclick=()=>{ const i=+b.dataset.i; if(i<parts.length-1) scmGo(parts[i][1]); });
  scmSide();
}
function scmFocus(n){
  const I=scmIndex();
  if(n.type==='planet'||n.type==='moon') scmGo({lvl:'body',sys:n.sys,id:n.id});
  else if(n.type==='city'||(n.parent&&I.byId[n.parent]&&I.byId[n.parent].type==='moon')||n.id.startsWith('leo_'))
    scmGo({lvl:'body',sys:n.sys,id:n.parent});
  else if(n.type==='star') scmGo({lvl:'system',sys:n.sys});
  else scmGo({lvl:'system',sys:n.sys});
  SCM.sel=n.id; scmSide();
}

// ---- layout: screen positions for the current view
function scmLayout(w,h){
  const I=scmIndex(), V=SCM.vis, L=[], cx=w/2+SCM.panX, cy=h/2+SCM.panY, R=Math.min(w,h)*.44*SCM.zoom;
  const vw=SCM.view;
  if(vw.lvl==='galaxy'){
    for(const [id,g] of Object.entries(SCM_GAL)){
      const n=Object.values(V.node).length?SCMAP.nodes.filter(x=>x.sys===id&&V.node[x.id]&&!['planet','moon'].includes(x.type)).length:0;
      L.push({kind:'sys', id, x:cx+g.x*R*1.05, y:cy+g.y*R*1.05, r:g.closed?7:13, g, n});
    }
    return L;
  }
  if(vw.lvl==='system'){
    const ns=SCMAP.nodes.filter(n=>n.sys===vw.sys&&(['star','planet','lagrange','station','gate'].includes(n.type)||(n.type==='moon'&&n.parent==='star_'+n.sys))
      && !(n.type==='station'&&n.parent&&I.byId[n.parent]&&I.byId[n.parent].type!=='star'&&!n.id.startsWith('wikelo')));
    const D=Math.max(...ns.map(n=>Math.hypot(n.x,n.y)))||1;
    const P=(x,y)=>{ const d=Math.hypot(x,y); const k=d? Math.pow(d/D,.6)*R/d : 0; return [cx+x*k, cy-y*k]; };
    SCM.sysProj={P,D,cx,cy,R};
    const at={};
    ns.forEach(n=>{ const [x,y]=P(n.x,n.y); const o={kind:'node', n, x, y, r: n.type==='star'?16:n.type==='planet'||n.type==='moon'?10:n.type==='gate'?7:4.5};
      at[n.id]=o; L.push(o); });
    // L1, L2 and the Wikelo bases sit within a few pixels of their planet: move them out to a readable gap
    L.forEach(o=>{ const p=o.n.parent&&at[o.n.parent]; if(!p||p.n.type!=='planet') return;
      let dx=o.x-p.x, dy=o.y-p.y, d=Math.hypot(dx,dy); const gap=22;
      if(d<gap){ if(d<.5){ dx=p.x-cx; dy=p.y-cy; d=Math.hypot(dx,dy)||1; } o.x=p.x+dx/d*gap; o.y=p.y+dy/d*gap; } });
    return L;
  }
  // body view: the body in the middle, its moons and stations around it, its Lagrange points on an outer ring
  const b=I.byId[vw.id]; const kids=(I.kids[b.id]||[]).map(id=>I.byId[id]);
  const far=n=>n.type==='lagrange'||Math.hypot(n.x-b.x,n.y-b.y)>.6;
  const near=kids.filter(n=>!far(n)&&n.type!=='city'), lps=kids.filter(n=>far(n)&&n.type!=='city');
  const D=Math.max(...near.map(n=>Math.hypot(n.x-b.x,n.y-b.y)), 0.001);
  const br=Math.max(26, Math.min(64, R*.12*Math.pow(scmBodyR(b)/1000,.35)));
  const P=(n)=>{ const dx=n.x-b.x, dy=n.y-b.y, d=Math.hypot(dx,dy)||1e-9; const rr=br+18+(R*.8-br-18)*Math.pow(d/D,.7); return [cx+dx/d*rr, cy-dy/d*rr]; };
  L.push({kind:'body', n:b, x:cx, y:cy, r:br});
  const cities=kids.filter(n=>n.type==='city'), lon0=cities.length?(cities[0].lon||0):0;
  cities.forEach(n=>{
    // cities sit on the face of the globe, from their latitude and longitude; the globe faces the first city
    const lon=((n.lon||0)-lon0)*Math.PI/180, lat=(n.lat||0)*Math.PI/180;
    const fx=Math.cos(lat)*Math.sin(lon), fy=Math.sin(lat), fz=Math.cos(lat)*Math.cos(lon);
    L.push({kind:'node', n, x:cx+fx*br*.86, y:cy-fy*br*.86, r:4.5, back:fz<0}); });
  near.forEach(n=>{ const [x,y]=P(n); L.push({kind:'node', n, x, y,
    r: n.type==='moon'?Math.max(6,Math.min(15,scmBodyR(n)/32)):4.5}); });
  lps.forEach(n=>{ const dx=n.x-b.x, dy=n.y-b.y, d=Math.hypot(dx,dy)||1;
    L.push({kind:'node', n, x:cx+dx/d*R*1.02, y:cy-dy/d*R*1.02, r:4.5, ring:true, dist:d}); });
  SCM.bodyR=R; return L;
}

// ---- drawing
function scmFrame(t){
  const cv=$('#scmCv'); if(!cv){ SCM.raf=0; return; }
  const dpr=window.devicePixelRatio||1, w=cv.clientWidth, h=cv.clientHeight;
  if(cv.width!==Math.round(w*dpr)||cv.height!==Math.round(h*dpr)){ cv.width=Math.round(w*dpr); cv.height=Math.round(h*dpr); }
  const x=cv.getContext('2d'); x.setTransform(dpr,0,0,dpr,0,0); x.clearRect(0,0,w,h);
  const ph=((t-SCM.t0)/1600)%1, V=SCM.vis, I=scmIndex(), vw=SCM.view;
  const L=scmLayout(w,h); SCM.hits=L;
  const mono=s=>`${s} ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace`;
  const placed=[];
  // draw a label unless it would sit on one already drawn (callers go most important first)
  const label=(txt,px,py,col,font,al,force)=>{ x.font=font||mono('600 10px'); x.textAlign=al||'left';
    const tw=x.measureText(txt).width, ox=al==='center'?-tw/2:al==='right'?-tw:0, bx={l:px+ox-3,t:py-10,r:px+ox+tw+3,b:py+4};
    if(!force&&placed.some(q=>bx.l<q.r&&bx.r>q.l&&bx.t<q.b&&bx.b>q.t)) return false;
    placed.push(bx); x.fillStyle='rgba(2,6,10,.75)'; x.fillRect(bx.l,bx.t+1,bx.r-bx.l,13); x.fillStyle=col; x.fillText(txt,px,py); return true; };
  // grid rings
  x.strokeStyle='rgba(33,166,214,.07)'; x.lineWidth=1;
  for(let i=1;i<=4;i++){ x.beginPath(); x.arc(w/2+SCM.panX,h/2+SCM.panY,Math.min(w,h)*.11*i*SCM.zoom,0,7); x.stroke(); }
  if(vw.lvl==='galaxy'){
    const pos=Object.fromEntries(L.map(o=>[o.id,o]));
    SCMAP.links.forEach(([a,b])=>{ const A=pos[a], B=pos[b]; if(!A||!B) return;
      const closed=SCM_GAL[a].closed||SCM_GAL[b].closed;
      const used=SCMAP.nodes.some(n=>n.type==='gate'&&((n.sys===a&&n.to===b)||(n.sys===b&&n.to===a))&&V.node[n.id]);
      x.strokeStyle=closed?'rgba(110,130,140,.35)':used?'rgba(33,230,255,.85)':'rgba(33,166,214,.35)';
      x.lineWidth=used?2:1.2; x.setLineDash(closed?[3,5]:used?[]:[6,4]);
      if(used){ x.shadowColor='#21e6ff'; x.shadowBlur=10; }
      x.beginPath(); x.moveTo(A.x,A.y); x.lineTo(B.x,B.y); x.stroke(); x.setLineDash([]); x.shadowBlur=0;
      if(used&&!closed){ const k=(ph+(a.length%3)/3)%1; x.fillStyle='#bdf3ff'; x.beginPath();
        x.arc(A.x+(B.x-A.x)*k, A.y+(B.y-A.y)*k, 2.2, 0, 7); x.fill(); } });
    L.forEach(o=>{ const g=o.g, col=g.closed?'#5a6b73':o.n?'#21e6ff':'#5b9fbb';
      const gr=x.createRadialGradient(o.x,o.y,0,o.x,o.y,o.r*3.2); gr.addColorStop(0,g.closed?'rgba(90,107,115,.5)':'rgba(255,214,140,.95)');
      gr.addColorStop(.3,g.closed?'rgba(90,107,115,.2)':'rgba(255,160,60,.35)'); gr.addColorStop(1,'rgba(0,0,0,0)');
      x.fillStyle=gr; x.beginPath(); x.arc(o.x,o.y,o.r*3.2,0,7); x.fill();
      x.fillStyle=g.closed?'#7d8c93':'#fff3dc'; x.beginPath(); x.arc(o.x,o.y,o.r*.45,0,7); x.fill();
      if(o.n){ x.strokeStyle='rgba(33,230,255,'+(.6*(1-ph))+')'; x.lineWidth=1.3; x.beginPath(); x.arc(o.x,o.y,o.r+ph*16,0,7); x.stroke(); }
      if(SCM.hover===o){ x.strokeStyle='#dff9ff'; x.lineWidth=1; x.beginPath(); x.arc(o.x,o.y,o.r+6,0,7); x.stroke(); }
      label(g.name.toUpperCase(), o.x, o.y+o.r+22, col, mono('700 12px'), 'center');
      label(g.closed?g.sub.toUpperCase():(o.n?`${o.n} PLACES DOCKED`:'NO STOPS YET'), o.x, o.y+o.r+37, g.closed?'#5a6b73':o.n?'#7fdcff':'#4f7f93', mono('600 9.5px'), 'center'); });
  } else {
    const cxx=w/2+SCM.panX, cyy=h/2+SCM.panY;
    if(vw.lvl==='system'){
      const S=scmSys(vw.sys), P=SCM.sysProj;
      (S.rings||[]).forEach(r=>{ const [rx]=P.P(r.r,0), rr=rx-cxx, [ax]=P.P(r.r+r.w/2,0), [bx]=P.P(r.r-r.w/2,0);
        x.strokeStyle='rgba(150,190,210,.10)'; x.lineWidth=Math.max(2,ax-bx); x.beginPath(); x.arc(cxx,cyy,rr,0,7); x.stroke();
        const a=-Math.PI*.78; label(r.name.toUpperCase(), cxx+Math.cos(a)*rr, cyy+Math.sin(a)*rr+3, '#4f8aa1', mono('600 9px'), 'center'); });
      L.filter(o=>o.n.type==='planet').forEach(o=>{ x.strokeStyle='rgba(33,166,214,.18)'; x.lineWidth=1;
        x.beginPath(); x.arc(cxx,cyy,Math.hypot(o.x-cxx,o.y-cyy),0,7); x.stroke(); });
    } else {
      if(L.some(o=>o.ring)){ x.strokeStyle='rgba(33,166,214,.22)'; x.setLineDash([2,4]); x.beginPath(); x.arc(cxx,cyy,SCM.bodyR*1.02,0,7); x.stroke(); x.setLineDash([]);
        label('FAR STATIONS · DIRECTION ONLY', cxx, cyy-SCM.bodyR*1.02-8, '#3f6a7c', mono('600 9px'), 'center'); }
      L.filter(o=>o.n.type==='moon'||o.n.type==='station').forEach(o=>{ x.strokeStyle='rgba(33,166,214,.14)';
        x.beginPath(); x.arc(cxx,cyy,Math.hypot(o.x-cxx,o.y-cyy),0,7); x.stroke(); });
    }
    // markers
    const order={body:0, star:1, planet:2, moon:3, gate:4, lagrange:5, station:6, city:7}, labs=[];
    L.slice().sort((a,b)=>(order[a.kind==='body'?'body':a.n.type]||9)-(order[b.kind==='body'?'body':b.n.type]||9)).forEach(o=>{
      const n=o.n, v=V.node[n.id], home=SCM.vis.home===n.id, hit=scmMatch(n), sel=SCM.sel===n.id;
      const dim=SCM.svc.size && !hit && !['star','planet','moon'].includes(n.type);
      x.globalAlpha=dim?.22:1;
      if(n.type==='star'){
        const gr=x.createRadialGradient(o.x,o.y,0,o.x,o.y,o.r*3); gr.addColorStop(0,'rgba(255,230,170,1)'); gr.addColorStop(.25,'rgba(255,170,70,.55)'); gr.addColorStop(1,'rgba(0,0,0,0)');
        x.fillStyle=gr; x.beginPath(); x.arc(o.x,o.y,o.r*3,0,7); x.fill();
      } else if(o.kind==='body' || n.type==='planet' || n.type==='moon'){
        const big=o.kind==='body', r=o.r, rl=V.roll[n.id];
        const vv=v||rl, hm=SCM.vis.home&&(I.byId[SCM.vis.home].parent===n.id);
        if(vv&&!big){ x.strokeStyle=hm?'#ffb000':'#21e6ff'; x.globalAlpha=(1-ph)*.5; x.lineWidth=1.2; x.beginPath(); x.arc(o.x,o.y,r+3+ph*12,0,7); x.stroke(); x.globalAlpha=1; }
        if(!big&&scmDeep(n)){ x.strokeStyle='#ffb000'; x.lineWidth=1.2; x.beginPath(); x.arc(o.x,o.y,r+5,0,7); x.stroke(); }
        const gr=x.createRadialGradient(o.x-r*.35,o.y-r*.35,r*.1,o.x,o.y,r);
        gr.addColorStop(0, vv?'#6fd7ee':'#4a6b7a'); gr.addColorStop(1, vv?'#0b3a4c':'#122630');
        x.fillStyle=gr; x.beginPath(); x.arc(o.x,o.y,r,0,7); x.fill();
        x.strokeStyle=vv?'rgba(33,230,255,.8)':'rgba(91,159,187,.45)'; x.lineWidth=big?1.5:1; x.stroke();
        if(big){ // latitude lines for the globe feel
          x.strokeStyle='rgba(33,230,255,.12)'; for(let k=-2;k<=2;k++){ x.beginPath(); x.ellipse(o.x,o.y+k*r*.33,r*Math.sqrt(1-(k*.33)**2),r*.08,0,0,7); x.stroke(); }
          x.beginPath(); x.ellipse(o.x,o.y,r*.35,r,0,0,7); x.stroke(); }
      } else {
        const col=home?'#ffb000':v?'#21e6ff':'#5b9fbb', r=o.r;
        if(o.back) x.globalAlpha*=.35;
        x.fillStyle=v?col:'rgba(10,30,40,.9)'; x.strokeStyle=col; x.lineWidth=1.3;
        if(v){ x.shadowColor=col; x.shadowBlur=10; }
        x.beginPath();
        if(n.type==='gate'){ x.arc(o.x,o.y,r,0,7); x.stroke(); x.beginPath(); x.arc(o.x,o.y,r*.45,0,7); x.fill(); }
        else if(n.type==='lagrange'&&!n.kind){ x.moveTo(o.x,o.y-r); x.lineTo(o.x+r,o.y); x.lineTo(o.x,o.y+r); x.lineTo(o.x-r,o.y); x.closePath(); x.stroke(); }
        else if(n.type==='city'){ x.moveTo(o.x,o.y-r-1); x.lineTo(o.x+r,o.y+r); x.lineTo(o.x-r,o.y+r); x.closePath(); x.fill(); x.stroke(); }
        else { x.rect(o.x-r,o.y-r,r*2,r*2); x.fill(); x.stroke(); }
        x.shadowBlur=0;
        if(v){ const k=Math.min(1,.35+v.n/12); x.strokeStyle=col; x.globalAlpha*=(1-ph)*.7*k; x.lineWidth=1.2;
          x.beginPath(); x.arc(o.x,o.y,r+3+ph*(8+v.n),0,7); x.stroke(); x.globalAlpha=dim?.22:1; }
        if(SCM.svc.size&&hit){ x.strokeStyle='#ffb000'; x.lineWidth=1; x.beginPath(); x.arc(o.x,o.y,r+5,0,7); x.stroke(); }
      }
      if(sel||SCM.hover===o){ x.strokeStyle='#dff9ff'; x.lineWidth=1.2; x.setLineDash([3,3]); x.beginPath(); x.arc(o.x,o.y,o.r+8,0,7); x.stroke(); x.setLineDash([]); }
      x.globalAlpha=1;
      // labels: planets, moons, gates, cities and anything visited or selected always; the rest when zoomed or hovered
      const always=['planet','moon','gate','city','star'].includes(n.type)||o.kind==='body'||v||sel||SCM.hover===o||SCM.zoom>1.7||(SCM.svc.size&&hit)||o.ring||n.kind;
      if(always&&!dim&&!o.back){
        let nm=n.name||''; if(n.type==='lagrange'&&nm.length>18&&!sel&&SCM.hover!==o) nm=nm.split(' ')[0];
        if(o.ring&&!v&&!sel&&SCM.hover!==o&&nm.length>14) nm=nm.split(' ')[0];
        if(!sel&&SCM.hover!==o) nm=nm.replace(/^Wikelo Emporium (\w+) Station$/,'Wikelo $1');
        const col=n.type==='planet'||n.type==='moon'||o.kind==='body'?'#bdf3ff':home?'#ffb000':v?'#21e6ff':'#6aa9c2';
        const f=o.kind==='body'?mono('700 13px'):n.type==='planet'?mono('700 11px'):mono('600 9.5px');
        const pr=o.kind==='body'?0:(sel||SCM.hover===o)?1:n.type==='planet'?2:home?3:v?4:n.type==='moon'||n.type==='gate'?5:6;
        labs.push([pr,()=>{ if(o.kind==='body') return label(nm.toUpperCase(), o.x, o.y-o.r-12, col, f, 'center', true);
          // try right, then left, then below
          return label(nm, o.x+o.r+5, o.y+3.5, col, f, 'left', pr<=1) || label(nm, o.x-o.r-5, o.y+3.5, col, f, 'right') ||
                 label(nm, o.x, o.y+o.r+13, col, f, 'center'); }]);
      }
    });
    labs.sort((a,b)=>a[0]-b[0]).forEach(l=>l[1]());
  }
  scmHud(L);
  SCM.raf=requestAnimationFrame(scmFrame);
}

function scmHud(L){
  const vw=SCM.view, I=scmIndex(), V=SCM.vis;
  const set=(id,h)=>{ const e=$(id); if(e&&e._h!==h){ e.innerHTML=h; e._h=h; } };
  if(vw.lvl==='galaxy'){
    set('#scmTL','<b>KNOWN SPACE</b><span>Jump network</span>');
    set('#scmTR',`${Object.keys(V.node).length?new Set(Object.keys(V.node).map(id=>I.byId[id].sys)).size:0} / 3 systems visited`);
    set('#scmBL','<span><i style="background:#21e6ff;border-radius:50%"></i>lane you have used</span><span><i style="border-top:2px dashed #21a6d6;height:0;width:14px"></i>open lane</span><span><i style="border-top:2px dashed #5a6b73;height:0;width:14px"></i>not open yet</span>');
    set('#scmBR','Diagram · not the real starmap');
  } else {
    const sys=scmSys(vw.sys);
    if(vw.lvl==='system') set('#scmTL',`<b>${scmE(sys.name.toUpperCase())} SYSTEM</b><span>${scmE(sys.kind)}</span>`);
    else { const b=I.byId[vw.id]; set('#scmTL',`<b>${scmE(b.name.toUpperCase())}</b><span>${SCM_TYPE[b.type]} · ${scmE(sys.name)} · radius ${fmt(scmBodyR(b))} km</span>`); }
    const pts=scmPool(vw);
    set('#scmTR',`${pts.filter(n=>V.node[n.id]).length} / ${pts.length} places here visited`);
    set('#scmBL','<span><i style="background:#21e6ff;border-radius:50%"></i>visited</span><span><i style="background:#ffb000;border-radius:50%"></i>home base</span>'+
      '<span><i style="border:1.5px solid #5b9fbb"></i>station</span><span><i style="border:1.5px solid #5b9fbb;transform:rotate(45deg);width:7px;height:7px"></i>Lagrange point, nothing there</span>'+
      '<span><i style="border:1.5px solid #5b9fbb;border-radius:50%"></i>jump gate</span><span><i style="width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:9px solid #5b9fbb"></i>landing zone</span>');
    set('#scmBR', vw.lvl==='system'?'Real directions · distances compressed · scroll to zoom · drag to pan':'Real directions · distances compressed · click a moon to look closer');
  }
  set('#scmFoot',`<span>Positions: <b>Star Citizen game files</b></span><span>Services: <b>UEX Corp</b> · ${scmE(SCMAP.built)}</span><span>Visits: <b>your logs</b>, sessions with a stop</span>`);
}

// ---- side panels
function scmSvcHTML(n){
  const s=n.svc||{}, keys=SCM_SVC.map(x=>x[0]).filter(k=>s[k]);
  if(!keys.length) return '<div class="scm-empty">No services listed.</div>';
  let h='<div class="scm-svc">'+keys.map(k=>`<span><i style="background:${SCM_SVC_COL[k]}"></i>${SCM_SVC_LBL[k]}</span>`).join('')+'</div>';
  const sh=n.shops||{}; const rows=Object.keys(SCM_SHOP_LBL).filter(k=>sh[k]&&sh[k].length);
  if(rows.length) h+='<ul class="scm-shops">'+rows.map(k=>`<li><b>${SCM_SHOP_LBL[k]}:</b> ${sh[k].map(scmE).join(', ')}</li>`).join('')+'</ul>';
  return h;
}
function scmVisHTML(v){
  if(!v) return '<div class="scm-vis"><div><b style="color:var(--dim)">0</b><span>Sessions</span></div></div><div class="scm-empty">You haven’t docked or landed here in this scope.</div>';
  return `<div class="scm-vis"><div><b>${fmt(v.n)}</b><span>Sessions</span></div>${v.first?`<div><b style="font-size:14px">${ddmm(v.first)}</b><span>First stop</span></div>`:''}${v.last&&v.last!==v.first?`<div><b style="font-size:14px">${ddmm(v.last)}</b><span>Latest</span></div>`:''}</div>`;
}
function scmRow(n, extra){
  const v=SCM.vis.node[n.id], home=SCM.vis.home===n.id;
  return `<button type="button" data-id="${n.id}"><span class="dot ${home?'home':v?'on':''}"></span><span>${scmE(n.name)}${extra?`<span class="s">${extra}</span>`:''}</span><span class="c">${v?v.n:''}</span></button>`;
}
// the stops that belong to a view: a system's, or a body's and its moons'
function scmPool(vw){
  const I=scmIndex();
  let pool=SCMAP.nodes.filter(m=>!['star','planet','moon'].includes(m.type)&&m.name&&(m.kind||m.type!=='lagrange'));
  if(vw.sys) pool=pool.filter(m=>m.sys===vw.sys);
  if(vw.lvl==='body'){ const ids=new Set([vw.id,...(I.kids[vw.id]||[])]); pool=pool.filter(m=>ids.has(m.parent)); }
  return pool;
}
function scmSide(){
  const P=$('#scmPanel'), Q=$('#scmList2'); if(!P) return;
  const I=scmIndex(), V=SCM.vis, vw=SCM.view;
  const n=SCM.sel?I.byId[SCM.sel]:(vw.lvl==='body'?I.byId[vw.id]:null);
  if(n){
    const par=n.parent&&I.byId[n.parent];
    let h=`<div class="scm-kind">${n.kind&&n.type==='lagrange'?'Station · Lagrange point':SCM_TYPE[n.type]||''}${n.approx?' · position approximate':''}</div>
      <div class="scm-name">${scmE(n.name)}</div><div class="scm-sub">${scmE(scmSys(n.sys).name)}${par&&par.type!=='star'?' · '+scmE(par.name):''}${n.armistice?' · armistice zone':''}</div>`+
      ((n.type==='planet'||n.type==='moon') ? ((V.roll[n.id])?`<div class="scm-vis"><div><b>${V.roll[n.id].places}</b><span>Places visited</span></div><div><b>${fmt(V.roll[n.id].stops)}</b><span>Stops</span></div></div>`:'<div class="scm-empty" style="margin-top:12px">No stops logged on or around it.</div>') : scmVisHTML(V.node[n.id]));
    if(!['planet','moon','star'].includes(n.type)) h+=`<div class="scm-sec"><h4>Services</h4>${scmSvcHTML(n)}</div>`;
    if(n.type==='gate') h+=`<div class="scm-sec"><h4>Leads to</h4><div>${scmE((SCM_GAL[n.to]||{}).name||n.to)}${SCM_GAL[n.to]&&SCM_GAL[n.to].closed?' <span class="scm-sub">· not open yet</span>':''}</div></div>`;
    if(n.type==='planet'||n.type==='moon'){
      const surf=(V.surface[n.id]||[]).sort((a,b)=>b.n-a.n);
      h+=`<div class="scm-sec"><h4>Where you landed</h4>${surf.length?'<div class="scm-list">'+surf.map(r=>`<button type="button" disabled><span class="dot on"></span><span>${scmE(r.name)}<span class="s">${scmE(r.kind)}</span></span><span class="c">${r.n}</span></button>`).join('')+'</div>':'<div class="scm-empty">No surface stops logged.</div>'}</div>`;
      const op=(SCMAP.outposts||{})[n.id]||[];
      const show=op.filter(o=>!SCM.svc.size||[...SCM.svc].every(k=>o.svc&&o.svc[k]));
      if(op.length) h+=`<div class="scm-sec"><h4>Outposts listed by UEX · ${show.length}${SCM.svc.size?' match':''}</h4><div class="scm-list">`+
        show.map(o=>`<button type="button" disabled><span class="dot"></span><span>${scmE(o.name)}<span class="s">${Object.keys(o.svc||{}).map(k=>SCM_SVC_LBL[k]||'').filter(Boolean).join(' · ')||'no services'}</span></span><span class="c"></span></button>`).join('')+'</div>'+
        '<div class="scm-note">Outposts are listed, not pinned: the game files hold them as unnamed copies of the same building.</div></div>';
    }
    if(SCM.sel&&vw.lvl!=='body'&&(n.type==='planet'||n.type==='moon')) h+=`<div class="scm-sec"><button type="button" class="mbtn go" id="scmOpen">Open ${scmE(n.name)}</button></div>`;
    P.innerHTML=h;
    const ob=$('#scmOpen'); if(ob) ob.onclick=()=>scmGo({lvl:'body',sys:n.sys,id:n.id});
  } else {
    const where=vw.lvl==='galaxy'?'Known space':scmSys(vw.sys).name+' system';
    P.innerHTML=`<div class="scm-kind">${vw.lvl==='galaxy'?'Galaxy':'System'}</div><div class="scm-name">${scmE(where)}</div>
      <div class="scm-sub">Hover for details · click to select${vw.lvl==='galaxy'?' · click a system to open it':' · click a planet to open it'}</div>
      ${SCM.svc.size?`<div class="scm-note">Showing places with: <b>${[...SCM.svc].map(k=>SCM_SVC_LBL[k]).join(' + ')}</b>.</div>`:''}`;
  }
  let pool=scmPool(vw).filter(scmMatch).sort((a,b)=>((V.node[b.id]||{}).n||0)-((V.node[a.id]||{}).n||0)||a.name.localeCompare(b.name));
  const ttl=SCM.svc.size?`Places with ${[...SCM.svc].map(k=>SCM_SVC_LBL[k].toLowerCase()).join(' + ')}`:'Places here';
  Q.innerHTML=`<h3>${ttl} <span class="u">— ${pool.length}</span></h3><div class="scm-list">${pool.map(m=>{
      const p=m.parent&&I.byId[m.parent]; return scmRow(m, `${vw.sys?'':scmE(scmSys(m.sys).name)+' · '}${p&&p.type!=='star'?scmE(p.name):SCM_TYPE[m.type]}`); }).join('')||'<div class="scm-empty">Nothing matches.</div>'}</div>`+
    (vw.lvl==='galaxy'&&V.other.length?`<div class="scm-sec"><h4>Not on the map</h4><div class="scm-list">${V.other.map(r=>`<button type="button" disabled><span class="dot on"></span><span>${scmE(r.name)}</span><span class="c">${r.n}</span></button>`).join('')}</div></div>`:'');
  Q.querySelectorAll('button[data-id]').forEach(b=>b.onclick=()=>scmFocus(I.byId[b.dataset.id]));
}

// ---- input
function scmBind(){
  const cv=$('#scmCv'), tip=$('#scmTip'); let drag=null, moved=false;
  const at=e=>{ const r=cv.getBoundingClientRect(); return [e.clientX-r.left, e.clientY-r.top]; };
  const pick=(mx,my)=>{ let best=null, bd=1e9; for(const o of SCM.hits){ const d=Math.hypot(o.x-mx,o.y-my);
      if(d<Math.max(o.r+6,11)&&d<bd&&!o.back){ best=o; bd=d; } } return best; };
  cv.onmousemove=e=>{ const [mx,my]=at(e);
    if(drag){ SCM.panX=drag.px+mx-drag.x; SCM.panY=drag.py+my-drag.y; moved=moved||Math.hypot(mx-drag.x,my-drag.y)>4; tip.hidden=true; return; }
    const o=pick(mx,my); SCM.hover=o;
    if(!o){ tip.hidden=true; return; }
    tip.hidden=false; tip.style.left=mx+'px'; tip.style.top=my+'px'; tip.innerHTML=scmTip(o); };
  cv.onmouseleave=()=>{ SCM.hover=null; tip.hidden=true; drag=null; cv.classList.remove('drag'); };
  cv.onmousedown=e=>{ const [mx,my]=at(e); drag={x:mx,y:my,px:SCM.panX,py:SCM.panY}; moved=false; cv.classList.add('drag'); };
  cv.onmouseup=e=>{ cv.classList.remove('drag'); const wasDrag=moved; drag=null; if(wasDrag) return;
    const [mx,my]=at(e), o=pick(mx,my);
    if(!o){ SCM.sel=null; scmSide(); return; }
    if(o.kind==='sys'){ if(!o.g.closed) scmGo({lvl:'system',sys:o.id}); return; }
    const n=o.n;
    if(o.kind==='body'){ SCM.sel=null; scmSide(); return; }
    if((n.type==='planet'||n.type==='moon')&&(SCM.sel===n.id||SCM.view.lvl==='body')){ scmGo({lvl:'body',sys:n.sys,id:n.id}); return; }
    if(n.type==='star'){ SCM.sel=null; scmSide(); return; }
    SCM.sel=n.id; scmSide(); };
  cv.ondblclick=e=>{ const [mx,my]=at(e), o=pick(mx,my); if(o&&o.n&&(o.n.type==='planet'||o.n.type==='moon')) scmGo({lvl:'body',sys:o.n.sys,id:o.n.id}); };
  cv.onwheel=e=>{ if(SCM.view.lvl==='galaxy') return; e.preventDefault(); const [mx,my]=at(e);
    const z0=SCM.zoom, z1=Math.max(.6,Math.min(14,z0*(e.deltaY<0?1.18:1/1.18)));
    const w=cv.clientWidth, h=cv.clientHeight, ox=mx-w/2-SCM.panX, oy=my-h/2-SCM.panY;
    SCM.panX-=ox*(z1/z0-1); SCM.panY-=oy*(z1/z0-1); SCM.zoom=z1; };
  document.addEventListener('keydown', scmKey);
}
function scmKey(e){
  if(!$('#scmCv')){ document.removeEventListener('keydown', scmKey); return; }
  if(e.key!=='Escape'||e.target.matches('input,select,textarea')) return;
  const vw=SCM.view, I=scmIndex();
  if(SCM.sel){ SCM.sel=null; scmSide(); return; }
  if(vw.lvl==='body'){ const p=I.byId[I.byId[vw.id].parent]; scmGo(p&&p.type!=='star'?{lvl:'body',sys:vw.sys,id:p.id}:{lvl:'system',sys:vw.sys}); }
  else if(vw.lvl==='system') scmGo({lvl:'galaxy'});
}
function scmTip(o){
  if(o.kind==='sys'){ const g=o.g; return `<b>${scmE(g.name)}</b><br><span class="d">${scmE(g.sub)}</span>${g.closed?'':`<br><span class="v">${o.n} places docked</span><br><span class="d">Click to open</span>`}`; }
  const n=o.n, I=scmIndex(), v=SCM.vis.node[n.id], p=n.parent&&I.byId[n.parent];
  let h=`<b>${scmE(n.name)}</b><br><span class="d">${n.kind&&n.type==='lagrange'?'Station':SCM_TYPE[n.type]}${p&&p.type!=='star'?' · '+scmE(p.name):''}${o.dist?' · '+o.dist.toFixed(2)+' Gm away':''}</span>`;
  h+= v?`<br><span class="${SCM.vis.home===n.id?'h':'v'}">${v.surf?'Landed':'Docked'} in ${v.n} session${v.n>1?'s':''}${v.last?' · last '+ddmm(v.last):''}</span>`:(['star'].includes(n.type)?'':'<br><span class="d">No stops logged</span>');
  const s=Object.keys(n.svc||{}).filter(k=>SCM_SVC_LBL[k]);
  if(s.length) h+=`<br><span class="d">${s.map(k=>SCM_SVC_LBL[k]).join(' · ')}</span>`;
  if(n.type==='planet'||n.type==='moon'){ const op=((SCMAP.outposts||{})[n.id]||[]).length; h+=`<br><span class="d">${op?op+' outposts · ':''}click to open</span>`; }
  return h;
}
"""
