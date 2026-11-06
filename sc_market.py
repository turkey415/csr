"""Terminal trade advice (fork addition): what the terminal you just opened sells, and
the best place to sell each item.

When you open a commodity terminal, the game logs what it sells and the box sizes, but
not prices. Prices come from UEX Corp's public API (api.uexcorp.space), which players
keep current by reporting what terminals show. This only reads Game.log and downloads
public price lists; it never touches the game.

sc_stats.py calls one thing:
  live_json(channels, place_namer, cache_dir, query)   for /api/market
The page part (JS/CSS) is used by sc_trade's section, which shows the card.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

import sc_trade

API = "https://api.uexcorp.space/2.0/"
# How long each download is kept. Prices change as players report them.
TTL = {"commodities_prices_all": 15 * 60, "terminals": 24 * 3600, "commodities": 24 * 3600}
AGENT = "CSR fork (Star Citizen career stats)"
TOP = 6   # places to sell kept per commodity, per filter

BOX = re.compile(r"AddingCommodityBox - .*?shopId\[(\d+)\].*?commodityName\[ResourceType\.([^\]]+)\]"
                 r".*?Available Box Sizes:(.*?)\[Team")
TS = sc_trade.TS

# Game names that don't match UEX names once spaces and case are ignored.
ALIASES = {"Flourine": "Fluorine", "PlasmaFuel": "Hydrogen Fuel",
           "ShipCountermeasuresDecoy": "Ship Decoy Countermeasures",
           "ShipCountermeasuresNoise": "Ship Noise Countermeasures"}
for _n in range(1, 13):
    ALIASES[f"ShipAmmoSize{_n}"] = f"Ship Ammunition - Size {_n}"


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# --------------------------------------------------------------------------- #
#  UEX downloads (cached on disk; the last good copy is used if the site is down)
# --------------------------------------------------------------------------- #

_lock = threading.Lock()
_mem = {}     # name -> (mtime, data)
_error = [None]


def _uex(name, cache_dir):
    path = os.path.join(cache_dir, f"uex_{name}.json")
    with _lock:
        try:
            age = time.time() - os.stat(path).st_mtime
        except OSError:
            age = None
        if age is None or age > TTL[name]:
            try:
                with urlopen(Request(API + name, headers={"User-Agent": AGENT}), timeout=30) as r:
                    body = json.loads(r.read())
                if body.get("status") != "ok":
                    raise ValueError(body.get("message") or body.get("status"))
                os.makedirs(cache_dir, exist_ok=True)
                with open(path + ".tmp", "w", encoding="utf-8") as f:
                    json.dump(body["data"], f)
                os.replace(path + ".tmp", path)
                _error[0] = None
            except Exception as e:
                _error[0] = f"Couldn't download UEX prices ({e}); showing the last copy."
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            return [], None
        hit = _mem.get(name)
        if not hit or hit[0] != mtime:
            with open(path, encoding="utf-8") as f:
                hit = _mem[name] = (mtime, json.load(f))
        return hit[1], mtime


# --------------------------------------------------------------------------- #
#  The last terminal opened, from the live log
# --------------------------------------------------------------------------- #

_open_cache = {}   # path -> ((size, mtime), opening)


def last_opening(path):
    """{t, where (code), items: {game name: [box sizes]}} for the newest terminal opening."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    sig = (st.st_size, int(st.st_mtime))
    hit = _open_cache.get(path)
    if hit and hit[0] == sig:
        return hit[1]
    where = picked = opening = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "AddingCommodityBox" in line:
                m, t = BOX.search(line), TS.match(line)
                if not m or not t:
                    continue
                shop, raw, sizes = m.groups()
                t = t.group(1)
                # a new opening starts when the shop changes or a few seconds pass
                if not opening or opening["shop"] != shop or \
                        (sc_trade._dt(t) - sc_trade._dt(opening["t"])).total_seconds() > 5:
                    opening = {"t": t, "shop": shop, "where": where, "items": {}}
                opening["t"] = t
                opening["items"][raw] = [int(x) for x in re.findall(r"boxSize\[(\d+)\]", sizes)]
            elif (x := sc_trade.LOC_INV.search(line)):
                where = x.group(1)
            elif (x := sc_trade.QT_PICK.search(line)):
                picked = x.group(1)
            elif sc_trade.QT_ARRIVED in line and picked:
                where = picked
            elif "<Join PU>" in line:
                where = picked = None
    _open_cache[path] = (sig, opening)
    return opening


# --------------------------------------------------------------------------- #
#  Advice
# --------------------------------------------------------------------------- #

def _match_terminal(where_name, listed, commodity_terminals, rows_by_terminal):
    """The UEX terminal you're at: right location first, then the best overlap with
    what the log listed (every terminal has the same shop name in the log)."""
    w = _norm(where_name)
    near = [t for t in commodity_terminals if len(w) > 2 and w in _norm(" ".join(
        str(t.get(k) or "") for k in ("name", "nickname", "space_station_name", "city_name", "outpost_name", "code")))]

    def score(t):
        sold = {r["commodity_name"] for r in rows_by_terminal.get(t["id"], ()) if r["price_buy"]}
        return (len(sold & listed) / len(sold | listed), t["name"].startswith("Admin")) if sold else (0, False)
    best = max(near or commodity_terminals, key=score, default=None)
    return (best, bool(near)) if best and score(best)[0] > 0 else (None, False)


def advise(live_path, place_namer, cache_dir, hold_names=()):
    terminals, _ = _uex("terminals", cache_dir)
    commodities, _ = _uex("commodities", cache_dir)
    prices, prices_mtime = _uex("commodities_prices_all", cache_dir)
    out = {"prices_age_s": time.time() - prices_mtime if prices_mtime else None, "error": _error[0],
           "opening": None, "items": [], "hold": {}}
    if not prices or not terminals:
        out["error"] = out["error"] or "No UEX price data yet."
        return out

    now = time.time()
    term = {t["id"]: t for t in terminals}
    by_term, by_comm = {}, {}
    for r in prices:
        by_term.setdefault(r["id_terminal"], []).append(r)
        by_comm.setdefault(r["id_commodity"], []).append(r)
    cidx = {}
    for c in commodities:
        for k in (c["name"], c.get("code"), c.get("slug")):
            if k:
                cidx.setdefault(_norm(k), c)

    def lookup(raw):
        return cidx.get(_norm(ALIASES.get(raw, raw))) or cidx.get(_norm(raw))

    def sellers(cid, exclude, system):
        """Best places to sell, kept for both 'this system only' and 'anywhere'."""
        rows = sorted((r for r in by_comm.get(cid, ()) if r["price_sell"] and r["id_terminal"] != exclude),
                      key=lambda r: -r["price_sell"])
        same = [r for r in rows if system and term.get(r["id_terminal"], {}).get("star_system_name") == system]
        keep = {id(r) for r in rows[:TOP] + same[:TOP]}
        res = []
        for r in rows:
            if id(r) not in keep:
                continue
            t = term.get(r["id_terminal"], {})
            res.append({"terminal": t.get("name") or r["terminal_name"], "system": t.get("star_system_name"),
                        "price": r["price_sell"], "demand": r.get("scu_sell_stock"),
                        "boxes": [int(x) for x in (r.get("container_sizes") or "").split(",") if x.strip().isdigit()],
                        "age_s": now - (r.get("date_modified") or now),
                        "same": bool(system) and t.get("star_system_name") == system})
        return res

    here, system = None, None
    op = last_opening(live_path) if live_path else None
    if op:
        where_name = sc_trade.place(op["where"], place_namer) if op["where"] else None
        listed = {c["name"] for raw in op["items"] if (c := lookup(raw))}
        commodity_terms = [t for t in terminals if t.get("type") == "commodity"]
        here, by_loc = _match_terminal(where_name, listed, commodity_terms, by_term)
        system = here.get("star_system_name") if here else None
        if not system and op["where"]:
            try:
                system = place_namer(sc_trade._normalize(op["where"]))[1]
            except Exception:
                pass
        here_rows = {r["id_commodity"]: r for r in by_term.get(here["id"], ())} if here else {}
        out["opening"] = {"t": op["t"], "where": where_name, "terminal": here and here["name"], "system": system,
                          "matched_by": "location" if by_loc else "listing" if here else None}
        for raw, boxes in op["items"].items():
            c = lookup(raw)
            row = here_rows.get(c["id"]) if c else None
            buy = row["price_buy"] if row and row["price_buy"] else None
            sells = sellers(c["id"], here and here["id"], system) if c else []
            for s in sells:
                s["profit"] = s["price"] - buy if buy else None
                s["margin"] = (s["price"] - buy) / buy * 100 if buy else None
            out["items"].append({"name": c["name"] if c else re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw),
                                 "boxes": boxes, "buy": buy, "stock": row.get("scu_buy") if row else None,
                                 "illegal": bool(c and c.get("is_illegal")), "sells": sells})

    for name in hold_names:
        c = cidx.get(_norm(name))
        if not c:
            continue
        here_row = next((r for r in by_term.get(here["id"], ()) if r["id_commodity"] == c["id"]), None) if here else None
        out["hold"][name] = {"here": here_row["price_sell"] if here_row and here_row["price_sell"] else None,
                             "sells": sellers(c["id"], None, system)}
    return out


def live_json(channels, place_namer, cache_dir, query=""):
    """/api/market?ch=LIVE&hold=Titanium,Scrap"""
    q = parse_qs(query)
    want = (q.get("ch") or [""])[0]
    hold = [h for h in (q.get("hold") or [""])[0].split(",") if h][:40]
    live = next((ch[2] for ch in channels if ch[0] == want and ch[2]), None) or \
        next((ch[2] for ch in channels if ch[2]), None)
    data = advise(live, place_namer, cache_dir, hold)
    data["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return json.dumps(data, separators=(",", ":"))


# --------------------------------------------------------------------------- #
#  Page parts (appended after sc_trade's)
# --------------------------------------------------------------------------- #

CSS = r"""
/* ---- Terminal trade advice (fork addition) ---- */
.trm-top{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;margin:0 0 10px;color:var(--muted);font-size:13px}
.trm-top b{color:var(--txt);font-weight:600}
.trm-top label{margin-left:auto;cursor:pointer;user-select:none}
.trm-alt{color:var(--dim);font-size:11.5px}
.trm-tag{display:inline-block;font:600 10px var(--font-mono);letter-spacing:.08em;text-transform:uppercase;
  border:1px solid var(--line);border-radius:4px;padding:0 5px;margin-left:4px;color:var(--muted)}
.trm-old{color:var(--red)}
"""

JS = r"""
// ==== Terminal trade advice (fork addition) ===============================
// What the last terminal you opened sells, ranked by the best place to sell it (UEX prices).
let TRM=null, TRM_LAST='', TRM_SAME=localStorage.getItem('trm-same')!=='0';
const trmAgo = s => s==null?'—':s<3600?Math.max(1,Math.round(s/60))+' min':s<86400?Math.round(s/3600)+' h':Math.round(s/86400)+' d';
const trmPlace = x => sctE(x.terminal)+(x.same?'':`<span class="trm-tag">${sctE(x.system||'?')}</span>`);
const trmS = n => n==null?'—':`<span class="${n<0?'sct-neg':'sct-pos'}">${n<0?'−':'+'}${fmt(Math.round(Math.abs(n)))}</span>`;   // exact, not 2k
const trmPick = list => (list||[]).filter(x=>!TRM_SAME||x.same);
// the buyer has to take at least the smallest box this terminal sells
const trmFits = (it,x) => !x.boxes.length || !it.boxes.length || Math.min(...it.boxes)<=Math.max(...x.boxes);
function trmPoll(){
  if(!/^https?:/.test(location.protocol)) return;
  const d=sctData(), hold=d?[...new Set(d.hold.map(l=>l.commodity))].join(','):'';
  fetch(`/api/market?ch=${encodeURIComponent(currentChannel||'')}&hold=${encodeURIComponent(hold)}`,{cache:'no-store'})
    .then(r=>r.ok?r.json():Promise.reject()).then(j=>{
      const s=JSON.stringify([j.opening,j.items,j.hold,j.error,Math.round((j.prices_age_s||0)/600)]);
      TRM=j; if(s!==TRM_LAST){ TRM_LAST=s; if(section==='trade') secTrade(); }
    }).catch(()=>{});
}
function trmCard(){
  if(!/^https?:/.test(location.protocol)) return '';
  if(!TRM) return group(1,'trade','This terminal','Loading prices…','<div class="card"><div class="empty">Loading…</div></div>');
  const o=TRM.opening;
  const note=`Prices from <a href="https://uexcorp.space" target="_blank" rel="noopener">UEX Corp</a>, reported by players, so check the terminal before you buy. `+
    `Downloaded ${trmAgo(TRM.prices_age_s)} ago. “They want” is how much the buyer was taking at the last report; places that can't take this terminal's smallest box are left out.`+
    (TRM.error?` <span class="trm-old">${sctE(TRM.error)}</span>`:'');
  if(!o) return group(1,'trade','This terminal','Open a commodity terminal in game',
    `<div class="card"><div class="empty">Open a commodity terminal and what it sells shows up here, ranked by where it sells for the most.</div><p class="sub">${note}</p></div>`);
  const rows=TRM.items.map(it=>{ const opts=trmPick(it.sells).filter(x=>trmFits(it,x));
    return {it,opts,best:it.buy!=null&&opts.length?opts[0]:null}; });
  const good=rows.filter(r=>r.best&&r.best.profit>0).sort((a,b)=>b.best.profit-a.best.profit);
  const rest=rows.filter(r=>!good.includes(r));
  const body=good.map(({it,opts,best})=>`<tr><td><b>${sctE(it.name)}</b>${it.illegal?'<span class="trm-tag trm-old">illegal</span>':''}<div class="sub">boxes ${it.boxes.join(', ')} SCU</div></td>`+
    `<td class="n">${fmt(Math.round(it.buy))}</td><td class="n">${it.stock==null?'—':fmt(Math.round(it.stock))}</td>`+
    `<td>${trmPlace(best)}${opts.slice(1).filter(x=>x.profit>0).slice(0,2).map(x=>`<div class="trm-alt">or ${trmPlace(x)} · ${fmt(x.price)} (${trmS(x.profit)})</div>`).join('')}</td>`+
    `<td class="n">${fmt(best.price)}</td><td class="n">${trmS(best.profit)}</td><td class="n">${sctPct(best.margin)}</td>`+
    `<td class="n">${best.demand==null?'—':fmt(best.demand)+' SCU'}</td><td class="n ${best.age_s>3*86400?'trm-old':'sub'}">${trmAgo(best.age_s)} ago</td></tr>`).join('');
  const table=`<table class="sct-t"><thead><tr><th>Commodity</th><th class="n">Buy here</th><th class="n">In stock</th><th>Best place to sell</th>`+
    `<th class="n">Sells for</th><th class="n">Profit/SCU</th><th class="n">Margin</th><th class="n">They want</th><th class="n">Reported</th></tr></thead><tbody>`+
    (body||`<tr><td colspan="9"><div class="empty">Nothing here sells for a profit${TRM_SAME?' in this system. Untick the box to include other systems.':'.'}</div></td></tr>`)+`</tbody></table>`;
  const skip=rest.length?`<p class="sub">Not worth hauling: ${rest.map(({it,best})=>sctE(it.name)+(it.buy==null?' (no price reported here)':best?` (best ${trmS(best.profit)}/SCU)`:' (no known buyer)')).join(', ')}.</p>`:'';
  const top=`<div class="trm-top"><span><b>${sctE(o.terminal||'Terminal not recognised')}</b> · ${sctE(o.where||'location unknown')} · opened ${sctAgo(o.t)}</span>`+
    `<label><input type="checkbox" id="trmSame"${TRM_SAME?' checked':''}> Only sell in ${sctE(o.system||'this system')}</label></div>`;
  return group(1,'trade','This terminal','What the last terminal you opened sells, best profit first',`<div class="card">${top}${table}${skip}<p class="sub">${note}</p></div>`);
}
function trmHold(name, qty, paid){
  const h=TRM&&TRM.hold&&TRM.hold[name]; if(!h) return '<span class="sub">—</span>';
  const opts=trmPick(h.sells), x=opts.find(o=>o.demand>=qty)||opts[0];   // prefer a buyer that takes the whole lot
  return (x?`${trmPlace(x)} · ${fmt(x.price)} ${trmS(x.price-paid)}/SCU<div class="${x.demand<qty?'trm-old':'sub'}">wants ${x.demand==null?'?':fmt(x.demand)} SCU · reported ${trmAgo(x.age_s)} ago</div>`:'<span class="sub">no known buyer</span>')+
    (h.here?`<div class="sub">here: ${fmt(h.here)} (${trmS(h.here-paid)})</div>`:'');
}
function trmWire(){
  const c=$('#trmSame'); if(c) c.onchange=()=>{ TRM_SAME=c.checked; localStorage.setItem('trm-same',TRM_SAME?'1':'0'); secTrade(); };
}
"""
