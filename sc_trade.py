"""Trade runs section (fork addition): cargo bought and sold, matched into runs with profit.

The log has every commodity buy and sell with its price, quantity and resource GUID, but
no wallet. So profit is worked out here: each sale is matched to the purchases it came
from, oldest first (FIFO), and a run ends when the hold is empty again.

sc_stats.py calls three things:
  session_fields(path)   per log, stored in the session archive so trades outlive the logs
  payload(sessions, ...) the data embedded in the page
  live_json(...)         /api/trade, which the page polls while the Trade section is open
  mark_lost(...)         /api/trade/lost, the hold's "Mark as lost" button
"""
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

VERSION = 2   # bump when scan() changes, so archived sessions get re-read
STORE_DIR = None   # set by sc_stats (app_dir) so lost-cargo marks live next to the archive
LOST_FILE = "csr_trade_lost.json"

BUY = re.compile(r"SendCommodityBuyRequest> .*?shopName\[([^\]]*)\].*?price\[([\d.]+)\]"
                 r".*?resourceGUID\[([0-9a-f-]+)\].*?quantity\[([\d.]+) cSCU\]")
SELL = re.compile(r"SendCommoditySellRequest> .*?shopName\[([^\]]*)\].*?amount\[([\d.]+)\]"
                  r".*?resourceGUID\[([0-9a-f-]+)\].*?quantity\[(\d+)\]")
LOC_INV = re.compile(r"requested inventory for Location\[([^\]]+)\]")
QT_PICK = re.compile(r"Player has selected point (\S+) as their destination")
QT_ARRIVED = "Quantum Drive Arrived - Arrived at Final Destination"
CARGO_SHIP = re.compile(r"VehicleCargoDataRequest for vehicleEntityId\[(\d+)\]")
FAILED = re.compile(r"Commodity Transaction Response Error .*?result\[([^\]]*)\] type\[(Buying|Selling)\]")
TS = re.compile(r"^<(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?Z>")
KEYS = ("SendCommodity", "requested inventory for Location", "selected point", QT_ARRIVED,
        "VehicleCargoDataRequest", "<Join PU>", "Commodity Transaction Response Error")
EPS = 1e-9


# --------------------------------------------------------------------------- #
#  Reading one log
# --------------------------------------------------------------------------- #

_scan_cache = {}   # path -> ((size, mtime), result)


def scan(path):
    """(first timestamp, [trade events]) for one log. Events are compact dicts:
    k b/s, t UTC time, g resource GUID, q SCU, a aUEC, w location code, s ship class."""
    try:
        st = os.stat(path)
    except OSError:
        return None, []
    sig = (st.st_size, int(st.st_mtime))
    hit = _scan_cache.get(path)
    if hit and hit[0] == sig:
        return hit[1]
    events, where, picked, ship_id, first = [], None, None, None, None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None, []
    for line in text.splitlines():
        if first is None:
            m = TS.match(line)
            if m:
                first = m.group(1)
        if not any(k in line for k in KEYS):
            continue
        m = TS.match(line)
        if not m:
            continue
        t = m.group(1)
        if (x := LOC_INV.search(line)):
            where = x.group(1)
        elif (x := QT_PICK.search(line)):
            picked = x.group(1)
        elif QT_ARRIVED in line and picked:
            where = picked
        elif "<Join PU>" in line:
            picked = where = None
        elif (x := FAILED.search(line)):
            # the game refused the last request of that kind (e.g. AutoLoadStartFailed,
            # CargoRemovalFailed): nothing was bought or sold, so drop it
            kind = "b" if x.group(2) == "Buying" else "s"
            for i in range(len(events) - 1, -1, -1):
                if events[i]["k"] == kind:
                    del events[i]
                    break
        elif (x := CARGO_SHIP.search(line)):
            ship_id = x.group(1)
        elif (x := BUY.search(line)):
            _shop, price, guid, cscu = x.groups()
            events.append({"k": "b", "t": t, "g": guid, "q": float(cscu) / 100, "a": float(price),
                           "w": where, "_sid": ship_id})
        elif (x := SELL.search(line)):
            _shop, amount, guid, scu = x.groups()
            events.append({"k": "s", "t": t, "g": guid, "q": float(scu), "a": float(amount),
                           "w": where, "_sid": ship_id})
    # The cargo ship shows up elsewhere in the log as CLASS_<entity id>.
    names = {}
    for ev in events:
        sid = ev.pop("_sid")
        if sid and sid not in names:
            m = re.search(r"\b([A-Z]{2,5}_[A-Za-z0-9_]+?)_" + sid + r"\b", text)
            names[sid] = m.group(1) if m else None
        if sid and names.get(sid):
            ev["s"] = names[sid]
    result = (first, events)
    _scan_cache[path] = (sig, result)
    return result


def session_fields(path):
    """Extra keys for scan_log()'s session dict."""
    _first, events = scan(path)
    return {"trade": events, "_tv": VERSION}


# --------------------------------------------------------------------------- #
#  Names
# --------------------------------------------------------------------------- #

def _resource_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


_commodities = None


def commodity(guid):
    """Name for a resource GUID, from sc_commodities.json (tools/build_commodities.py)."""
    global _commodities
    if _commodities is None:
        try:
            with open(os.path.join(_resource_dir(), "sc_commodities.json"), encoding="utf-8") as f:
                _commodities = json.load(f)
        except (OSError, ValueError):
            _commodities = {}
    raw = _commodities.get(guid)
    if not raw:
        return f"Unknown #{guid[:8]}"
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw).replace("_", " ")


_PLANET = {"1": "HUR", "2": "CRU", "3": "ARC", "4": "MIC"}
_JP = {"stan-magnus": "RR_JP_StantonMagnus", "nyx-castra": "RR_JP_NyxCastra", "stan-pyro": "RR_JP_StantonPyro",
       "pyro-stan": "RR_JP_PyroStanton", "pyro-nyx": "RR_JP_PyroNyx", "nyx-pyro": "RR_JP_NyxPyro"}
_CITIES = [("levski", "Levski"), ("grimhex", "GrimHEX"), ("lorville", "Lorville"), ("area18", "Area18"),
           ("newbabbage", "New Babbage"), ("orison", "Orison")]


def _normalize(code):
    """Turn the other spellings of a place into the RR_ codes CSR already names."""
    c = re.sub(r"^LOC_", "", code)
    m = re.match(r"RR_S(\d)_(L\d|LEO)$", c)
    if m and m.group(1) in _PLANET:
        return f"RR_{_PLANET[m.group(1)]}_{m.group(2)}"
    m = re.match(r"rs_ext_(hur|cru|arc|mic)-leo\d*$", c, re.I)
    if m:
        return f"RR_{m.group(1).upper()}_LEO"
    m = re.match(r"rs_ext_pyro(\d)_leo$", c, re.I)
    if m:
        return f"RR_P{m.group(1)}_LEO"
    m = re.match(r"rs_ext_([a-z]+-[a-z]+)_jp\d*$", c, re.I)
    if m and m.group(1).lower() in _JP:
        return _JP[m.group(1).lower()]
    return c


def place(code, namer):
    if not code:
        return "Unknown"
    c = _normalize(code)
    m = re.match(r"rs_ext_([a-z]{3})-l\d+$", c, re.I)
    if m:   # quantum markers don't number L-points the way the stations do
        return f"{m.group(1).upper()} Lagrange point"
    try:
        name, system, kind = namer(c)
    except Exception:
        name, system, kind = c, "Unknown", "Other"
    if kind == "Other" and system == "Unknown":
        low = c.lower().replace("_", "")
        for key, nm in _CITIES:
            if key in low:
                return nm
    return name


# --------------------------------------------------------------------------- #
#  Matching buys to sells
# --------------------------------------------------------------------------- #

def _dt(t):
    return datetime.fromisoformat(t).replace(tzinfo=timezone.utc)


def _local_day(t):
    return _dt(t).astimezone().date().isoformat()


def compute(events, latest_session, place_of, ship_of, now=None):
    """Runs, legs, the hold and totals for one account. `events` are sorted dicts with
    the archive keys plus 'sid' (session start). `latest_session` is that account's
    newest session start, for the "this session" totals."""
    now = now or datetime.now(timezone.utc)
    lots = defaultdict(list)          # guid -> lots still in the hold, oldest first
    legs, runs, run = [], [], None

    def held():
        return sum(l["scu"] for q in lots.values() for l in q)

    for ev in events:
        name = commodity(ev["g"])
        if ev["k"] == "l":
            # cargo you marked as lost: the rest of that purchase leaves the hold for 0 aUEC
            q = lots[ev["g"]]
            lot = next((l for l in q if l["t"] == ev["lot"]), None)
            if not lot or run is None:
                continue
            q.remove(lot)
            run["end"] = ev["t"]
            leg = {"t": ev["t"], "day": _local_day(ev["t"]), "sid": ev["sid"], "commodity": name, "scu": lot["scu"],
                   "unmatched": 0.0, "cost": lot["scu"] * lot["per"], "revenue": 0.0, "free": 0.0,
                   "profit": -lot["scu"] * lot["per"], "buy_per": lot["per"], "sell_per": 0.0, "from": lot["where"],
                   "to": "Lost", "ship": None, "lost": True, "lot": lot["t"], "g": ev["g"],
                   "held_min": (_dt(ev["t"]) - _dt(lot["t"])).total_seconds() / 60}
            legs.append(leg)
            run["sells"].append(leg)
            if held() <= EPS:
                runs.append(run)
                run = None
            continue
        where = place_of(ev.get("w"))
        ship = ship_of(ev["s"]) if ev.get("s") else None
        if run is None:
            run = {"start": ev["t"], "end": ev["t"], "buys": [], "sells": [], "ships": [], "stops": [],
                   "sid": ev["sid"]}
        run["end"] = ev["t"]
        if ship and ship not in run["ships"]:
            run["ships"].append(ship)
        if not run["stops"] or run["stops"][-1] != where:
            run["stops"].append(where)
        if ev["k"] == "b":
            per = ev["a"] / ev["q"] if ev["q"] else 0
            lots[ev["g"]].append({"scu": ev["q"], "per": per, "t": ev["t"], "where": where, "commodity": name,
                                  "g": ev["g"]})
            run["buys"].append({"t": ev["t"], "commodity": name, "scu": ev["q"], "aUEC": ev["a"], "per": per,
                                "where": where})
            continue
        need, cost, bought_at, first_t = ev["q"], 0.0, [], None
        q = lots[ev["g"]]
        while need > EPS and q:
            lot = q[0]
            take = min(need, lot["scu"])
            cost += take * lot["per"]
            lot["scu"] -= take
            need -= take
            if lot["where"] not in bought_at:
                bought_at.append(lot["where"])
            first_t = first_t or lot["t"]
            if lot["scu"] <= EPS:
                q.pop(0)
        matched = ev["q"] - need
        # cargo sold with no purchase in the logs (picked up, or bought before the oldest
        # log) is real money, so it counts, but it's kept apart so it can't inflate margins
        revenue = ev["a"]
        free = ev["a"] * (need / ev["q"]) if ev["q"] else 0
        leg = {"t": ev["t"], "day": _local_day(ev["t"]), "sid": ev["sid"], "commodity": name, "scu": ev["q"],
               "unmatched": need, "cost": cost, "revenue": revenue, "free": free, "profit": revenue - cost,
               "buy_per": cost / matched if matched > EPS else None, "sell_per": ev["a"] / ev["q"] if ev["q"] else 0,
               "from": ", ".join(bought_at) or "No purchase found", "to": where, "ship": ship,
               "held_min": (_dt(ev["t"]) - _dt(first_t)).total_seconds() / 60 if first_t else None}
        legs.append(leg)
        run["sells"].append(leg)
        if held() <= EPS:
            runs.append(run)
            run = None
    open_run = run
    if run:
        runs.append(run)

    out_runs = []
    for r in runs:
        minutes = (_dt(r["end"]) - _dt(r["start"])).total_seconds() / 60
        cost = sum(l["cost"] for l in r["sells"])
        rev = sum(l["revenue"] for l in r["sells"])
        free = sum(l["free"] for l in r["sells"])
        is_open = r is open_run
        out_runs.append({
            "start": r["start"], "end": r["end"], "day": _local_day(r["start"]), "sid": r["sid"], "open": is_open,
            "minutes": minutes, "ships": r["ships"], "stops": r["stops"],
            "spent": sum(b["aUEC"] for b in r["buys"]), "cost": cost, "revenue": rev, "profit": rev - cost,
            "free": free, "margin": (rev - free - cost) / cost * 100 if cost else None,
            "per_hour": (rev - cost) / (minutes / 60) if minutes >= 1 and not is_open else None,
            "scu": sum(l["scu"] for l in r["sells"]), "buys": r["buys"], "sells": r["sells"]})

    hold = [{**l, "cost": l["scu"] * l["per"], "age_min": (now - _dt(l["t"])).total_seconds() / 60}
            for q in lots.values() for l in q if l["scu"] > EPS]
    hold.sort(key=lambda l: l["t"])

    def block(sel_legs, sel_runs):
        cost = sum(l["cost"] for l in sel_legs)
        rev = sum(l["revenue"] for l in sel_legs)
        free = sum(l["free"] for l in sel_legs)
        scu = sum(l["scu"] for l in sel_legs)
        hours = sum(r["minutes"] for r in sel_runs if not r["open"]) / 60
        return {"profit": rev - cost, "revenue": rev, "cost": cost, "free": free, "scu": scu, "legs": len(sel_legs),
                "runs": sum(1 for r in sel_runs if not r["open"]),
                "margin": (rev - free - cost) / cost * 100 if cost else None,
                "per_hour": (rev - cost) / hours if hours >= 1 / 60 else None}

    today = now.astimezone().date().isoformat()
    by_comm = defaultdict(lambda: [0.0, 0.0, 0.0, 0, [], 0.0])        # scu, cost, revenue, legs, -, free
    by_route = defaultdict(lambda: [0.0, 0.0, 0.0, 0, [], 0.0])   # minutes held in [4]
    for l in legs:
        for d in (by_comm[l["commodity"]], by_route[(l["from"], l["to"], l["commodity"])]):
            d[0] += l["scu"]; d[1] += l["cost"]; d[2] += l["revenue"]; d[3] += 1; d[5] += l["free"]
        if l["held_min"] is not None:
            by_route[(l["from"], l["to"], l["commodity"])][4].append(l["held_min"])

    def row(d):
        p = d[2] - d[1]
        return {"scu": d[0], "cost": d[1], "revenue": d[2], "profit": p, "legs": d[3], "free": d[5],
                "margin": (p - d[5]) / d[1] * 100 if d[1] else None, "per_scu": p / d[0] if d[0] else None}

    cum, total = [], 0.0
    for l in legs:
        total += l["profit"]
        cum.append([l["t"], round(total)])

    return {
        "totals": {
            "session": block([l for l in legs if l["sid"] == latest_session],
                             [r for r in out_runs if r["sid"] == latest_session]),
            "today": block([l for l in legs if l["day"] == today], [r for r in out_runs if r["day"] == today]),
            "all": block(legs, out_runs)},
        "hold": hold, "hold_cost": sum(l["cost"] for l in hold), "hold_scu": sum(l["scu"] for l in hold),
        "runs": list(reversed(out_runs)),
        "commodities": sorted(({"commodity": k, **row(v)} for k, v in by_comm.items()), key=lambda r: -r["profit"]),
        "routes": sorted(({"from": k[0], "to": k[1], "commodity": k[2], **row(v),
                           "avg_min": sum(v[4]) / len(v[4]) if v[4] else None}
                          for k, v in by_route.items()), key=lambda r: -r["profit"])[:40],
        "cumulative": cum,
        "unmatched_scu": sum(l["unmatched"] for l in legs),
        "free": sum(l["free"] for l in legs),
        "last_trade": events[-1]["t"] if events else None,
    }


def _account_key(s):
    return f"{s.get('channel') or 'LIVE'}|{s.get('handle')}"


def _session_start(s):
    fp = s.get("fp") or (None,)
    return fp[0] if isinstance(fp, (list, tuple)) else None


def payload(sessions, place_namer, ship_namer, live=()):
    """{channel|handle: trade state} for every account with trades. `live` adds
    (channel, handle, first, events) for a log that isn't in the archive yet."""
    per_acct, latest = defaultdict(dict), {}
    rows = [(_account_key(s), _session_start(s), s.get("trade") or []) for s in sessions if s.get("handle")]
    rows += [(f"{ch}|{h}", first, ev) for ch, h, first, ev in live]
    for key, sid, evs in rows:
        if sid and sid > latest.get(key, ""):
            latest[key] = sid
        for e in evs:
            # the same trade can arrive from the archive and from a fresh read of the log
            per_acct[key][(e["t"], e["k"], e["g"], e["q"], e["a"])] = {**e, "sid": sid}
    names = {}

    def place_of(code):
        if code not in names:
            names[code] = place(code, place_namer)
        return names[code]

    for key, marks in load_lost().items():
        for m in marks:
            if key in per_acct:
                per_acct[key][("lost", m["lot"], m["g"])] = {"k": "l", "t": m["t"], "g": m["g"], "lot": m["lot"],
                                                             "sid": latest.get(key)}
    out = {}
    for key, evs in per_acct.items():
        evs = sorted(evs.values(), key=lambda e: (e["t"], e["k"] != "b"))
        if evs:
            out[key] = compute(evs, latest.get(key), place_of, ship_namer)
    return out


# --------------------------------------------------------------------------- #
#  Lost cargo: marks you add when cargo vanished without a sale in the log
# --------------------------------------------------------------------------- #

def _lost_path():
    return os.path.join(STORE_DIR or _resource_dir(), LOST_FILE)


def load_lost():
    """{channel|handle: [{lot: buy time, g: GUID, t: when marked}]}"""
    try:
        with open(_lost_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def mark_lost(body):
    """POST /api/trade/lost {key, lot, g, undo}: add or remove one mark."""
    try:
        req = json.loads(body or "{}")
        key, lot, g = str(req["key"]), str(req["lot"]), str(req["g"])
    except (ValueError, KeyError, TypeError):
        return {"ok": False, "error": "bad request"}
    data = load_lost()
    marks = [m for m in data.get(key, []) if not (m["lot"] == lot and m["g"] == g)]
    if not req.get("undo"):
        marks.append({"lot": lot, "g": g, "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")})
    if marks:
        data[key] = marks
    else:
        data.pop(key, None)
    tmp = _lost_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _lost_path())
    return {"ok": True}


# --------------------------------------------------------------------------- #
#  /api/trade
# --------------------------------------------------------------------------- #

def live_json(sessions, channels, place_namer, ship_namer):
    """Fresh trade state: the archive plus a re-read of each channel's live Game.log."""
    live = []
    by_start = {(s.get("channel"), _session_start(s)): s.get("handle") for s in sessions}
    newest = {}
    for s in sessions:
        ch, st = s.get("channel"), _session_start(s)
        if s.get("handle") and st and st > newest.get(ch, ("", None))[0]:
            newest[ch] = (st, s.get("handle"))
    age = None
    for ch in channels:
        label, live_path = ch[0], ch[2]
        if not live_path:
            continue
        first, events = scan(live_path)
        if not first:
            continue
        # a session CSR hasn't refreshed yet belongs to whoever played last on this channel
        handle = by_start.get((label, first)) or newest.get(label, ("", None))[1]
        if handle:
            live.append((label, handle, first, events))
        try:
            a = time.time() - os.stat(live_path).st_mtime
            age = a if age is None else min(age, a)
        except OSError:
            pass
    return json.dumps({"trade": payload(sessions, place_namer, ship_namer, live), "game_log_age_s": age,
                       "generated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                      separators=(",", ":"))


# --------------------------------------------------------------------------- #
#  Page parts (injected by render_html next to the Starmap's)
# --------------------------------------------------------------------------- #

NAV = '<a data-sec="trade" data-label="Trade Runs"><span>📦</span> Trade Runs</a>'

ICON = ("trade:_SVG('<path d=\"M3 7h11l-3-3M21 17H10l3 3\"/><path d=\"M14 7l7 0M3 17h7\" opacity=\".45\"/>'),")

CSS = r"""
/* ---- Trade runs (fork addition) ---- */
.sct-live{display:inline-flex;align-items:center;gap:7px;font:600 11px var(--font-mono);letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
.sct-live i{width:8px;height:8px;border-radius:50%;background:var(--dim)}
.sct-live.on{color:var(--green);border-color:rgba(74,222,128,.4)}
.sct-live.on i{background:var(--green);box-shadow:0 0 10px var(--green);animation:sctp 2s infinite}
@keyframes sctp{50%{box-shadow:0 0 2px var(--green)}}
.sct-head{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 14px;color:var(--muted);font-size:13px}
.sct-pos{color:var(--green)} .sct-neg{color:var(--red)}
.sct-lost{font:600 11px var(--font-mono);color:var(--muted);background:transparent;border:1px solid var(--line);
  border-radius:6px;padding:3px 8px;cursor:pointer;white-space:nowrap}
.sct-lost:hover{color:var(--red);border-color:var(--red)}
.sct-t{width:100%;border-collapse:collapse;font-size:13px}
.sct-t th{text-align:left;font:600 10.5px var(--font-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--dim);
  padding:0 10px 8px;border-bottom:1px solid var(--line)}
.sct-t td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.sct-t tr:last-child td{border-bottom:0}
.sct-t td.n,.sct-t th.n{text-align:right;font-family:var(--font-mono);white-space:nowrap}
.sct-t .sub{color:var(--dim);font-size:11.5px}
.sct-runs{display:flex;flex-direction:column;gap:10px}
.sct-run{border:1px solid var(--line);border-radius:var(--r-md,14px);background:var(--panel2);overflow:hidden}
.sct-run.open{border-color:rgba(244,169,42,.45)}
.sct-run summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:150px minmax(0,1fr) auto;gap:14px;
  align-items:center;padding:12px 16px}
.sct-run summary::-webkit-details-marker{display:none}
.sct-run summary:hover{background:var(--hover-tint,rgba(255,255,255,.04))}
.sct-when{font-family:var(--font-mono);font-size:12px;color:var(--muted)}
.sct-when b{display:block;color:var(--txt);font-size:13px;font-weight:500}
.sct-route{display:flex;flex-wrap:wrap;gap:4px 6px;align-items:center;font-size:13px}
.sct-route span{background:var(--tile);border:1px solid var(--line);border-radius:6px;padding:1px 8px}
.sct-route em{color:var(--dim);font-style:normal}
.sct-ships{color:var(--dim);font-size:11.5px;margin-top:4px}
.sct-pl{text-align:right;font-family:var(--font-mono)}
.sct-pl b{font-size:18px;display:block}
.sct-pl small{color:var(--dim);font-size:11.5px}
.sct-body{padding:4px 16px 14px;border-top:1px solid var(--line)}
.sct-chart{width:100%;height:220px;display:block}
.sct-chart .ln{fill:none;stroke:var(--cyan);stroke-width:2}
.sct-chart .ar{fill:var(--tint-cyan,rgba(91,209,230,.1))}
.sct-chart .ax{stroke:var(--line);stroke-width:1}
.sct-chart text{fill:var(--dim);font:11px var(--font-mono)}
@media (max-width:820px){.sct-run summary{grid-template-columns:1fr}.sct-pl{text-align:left}}
"""

JS = r"""
// ==== Trade runs (fork addition) ==========================================
// Buys and sells from the log, matched oldest-first into runs. Live while served.
let SCT_LIVE=null, SCT_LAST='', SCT_TIMER=0, SCT_OPENED=new Set();
const sctE = s => String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sctA = n => n==null ? '—' : (n<0?'−':'')+auec(Math.round(Math.abs(n)));
const sctP = n => n==null ? '—' : `<span class="${n<0?'sct-neg':'sct-pos'}">${n<0?'−':'+'}${auec(Math.round(Math.abs(n)))}</span>`;
const sctPct = n => n==null ? '—' : (n>=0?'+':'')+n.toFixed(0)+'%';
const sctMin = m => m==null ? '—' : m<60 ? Math.round(m)+' min' : (m/60).toFixed(1)+' h';
const sctTime = t => { const d=new Date(t+'Z'); return d.toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}); };
const sctAgo = t => { const s=(Date.now()-new Date(t+'Z'))/1000; return s<90?'just now':s<5400?Math.round(s/60)+' min ago':s<172800?Math.round(s/3600)+' h ago':Math.round(s/86400)+' days ago'; };
function sctData(){
  const k=currentChannel+'|'+currentAccount, src=(SCT_LIVE&&SCT_LIVE.trade)||DATA.trade||{};
  return src[k]||null;
}
function sctPoll(){
  if(!/^https?:/.test(location.protocol)) return;
  clearTimeout(SCT_TIMER);
  SCT_TIMER=setTimeout(()=>{
    if(section!=='trade') return;
    trmPoll();   // terminal advice (sc_market)
    fetch('/api/trade',{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(j=>{
      const str=JSON.stringify(j.trade), changed=str!==SCT_LAST;
      SCT_LIVE=j; SCT_LAST=str;
      if(section!=='trade') return;
      if(changed) return secTrade();
      const b=$('#content .sct-live'); if(b) b.outerHTML=sctBadge();
      sctPoll();
    }).catch(()=>{ if(section==='trade') sctPoll(); });
  }, SCT_LIVE?5000:50);
}
function sctChart(cum){
  if(cum.length<2) return '<div class="empty">Sell a few loads and your profit line shows up here.</div>';
  const W=900,H=220,P=46, ys=cum.map(c=>c[1]), lo=Math.min(0,...ys), hi=Math.max(0,...ys)||1;
  const x=i=>P+(W-P-10)*i/(cum.length-1), y=v=>10+(H-40)*(1-(v-lo)/((hi-lo)||1));
  const pts=cum.map((c,i)=>x(i).toFixed(1)+','+y(c[1]).toFixed(1)).join(' ');
  return `<svg class="sct-chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`+
    `<line class="ax" x1="${P}" x2="${W-10}" y1="${y(0)}" y2="${y(0)}"/>`+
    `<polygon class="ar" points="${x(0)},${y(0)} ${pts} ${x(cum.length-1)},${y(0)}"/>`+
    `<polyline class="ln" points="${pts}"/>`+
    `<text x="4" y="${y(hi)+4}">${sctA(hi)}</text><text x="4" y="${y(0)+4}">0</text>`+
    (lo<0?`<text x="4" y="${y(lo)}">${sctA(lo)}</text>`:'')+
    `<text x="${P}" y="${H-6}">${sctTime(cum[0][0])}</text>`+
    `<text x="${W-10}" y="${H-6}" text-anchor="end">${sctTime(cum[cum.length-1][0])}</text></svg>`;
}
function sctRun(r){
  const stops=r.stops.map(s=>`<span>${sctE(s)}</span>`).join('<em>→</em>');
  const legs=r.sells.map(l=>`<tr><td>${sctE(l.commodity)}<div class="sub">${sctE(l.from)} → ${sctE(l.to)}</div></td>`+
    `<td class="n">${fmt(+l.scu.toFixed(2))}</td><td class="n">${l.buy_per==null?'—':fmt(Math.round(l.buy_per))}</td>`+
    `<td class="n">${l.lost?'lost':fmt(Math.round(l.sell_per))}</td><td class="n">${sctP(l.profit)}${l.lost&&/^https?:/.test(location.protocol)?`<div class="sub"><button class="sct-lost" data-undo="1" data-lot="${sctE(l.lot)}" data-g="${sctE(l.g)}">Undo lost</button></div>`:''}${l.unmatched>1e-6?`<div class="sub">${fmt(+l.unmatched.toFixed(2))} SCU not bought · free cargo</div>`:''}</td></tr>`).join('');
  const buys=r.buys.map(b=>`<tr><td>${sctE(b.commodity)}<div class="sub">at ${sctE(b.where)} · ${sctTime(b.t)}</div></td>`+
    `<td class="n">${fmt(+b.scu.toFixed(2))}</td><td class="n">${fmt(Math.round(b.per))}</td><td class="n">${sctA(b.aUEC)}</td></tr>`).join('');
  const key=r.start, open=SCT_OPENED.has(key)?' open':'';
  return `<details class="sct-run${r.open?' open':''}" data-run="${sctE(key)}"${open}><summary>`+
    `<div class="sct-when"><b>${sctTime(r.start)}</b>${r.open?'in progress':sctMin(r.minutes)}</div>`+
    `<div><div class="sct-route">${stops}</div><div class="sct-ships">${r.ships.length?sctE(r.ships.join(', '))+' · ':''}${fmt(Math.round(r.scu))} SCU sold · spent ${sctA(r.spent)}</div></div>`+
    `<div class="sct-pl"><b>${sctP(r.profit)}</b><small>${sctPct(r.margin)}${r.per_hour!=null?' · '+sctA(r.per_hour)+'/h':''}${r.free>1?'<br>'+sctA(r.free)+' from free cargo':''}</small></div></summary>`+
    `<div class="sct-body">`+
    (r.sells.length?`<table class="sct-t"><thead><tr><th>Sold</th><th class="n">SCU</th><th class="n">Paid/SCU</th><th class="n">Got/SCU</th><th class="n">Profit</th></tr></thead><tbody>${legs}</tbody></table>`:'')+
    (r.buys.length?`<table class="sct-t" style="margin-top:12px"><thead><tr><th>Bought</th><th class="n">SCU</th><th class="n">Per SCU</th><th class="n">Paid</th></tr></thead><tbody>${buys}</tbody></table>`:'')+
    `</div></details>`;
}
function sctBadge(){
  if(!/^https?:/.test(location.protocol)) return '';
  const age=SCT_LIVE?SCT_LIVE.game_log_age_s:null, playing=age!=null&&age<120;
  return `<span class="sct-live${playing?' on':''}"><i></i>${playing?'Live · game running':SCT_LIVE?'Live · game not running':'Connecting…'}</span>`;
}
function sctLostWire(){
  $('#content').querySelectorAll('.sct-lost').forEach(b=>b.onclick=ev=>{
    ev.preventDefault(); ev.stopPropagation();
    const undo=!!b.dataset.undo;
    if(!undo && !confirm(`Mark ${b.dataset.what} as lost?\n\nIt leaves your hold and counts as sold for 0 aUEC, so its run closes at a loss. You can undo this from the run.`)) return;
    b.disabled=true;
    fetch('/api/trade/lost',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({key:currentChannel+'|'+currentAccount, lot:b.dataset.lot, g:b.dataset.g, undo})})
      .then(r=>r.json()).then(()=>{ SCT_LIVE=null; SCT_LAST=''; sctPoll(); }).catch(()=>{ b.disabled=false; });
  });
}
function secTrade(){
  const d=sctData(), served=/^https?:/.test(location.protocol), badge=sctBadge(), g=served?1:0;   // g: the terminal card takes section 01
  if(!d){
    $('#content').innerHTML=`<div class="sct-head">${badge}</div>`+trmCard()+group(1+g,'cargo','Trade runs','Buy cargo, sell it somewhere else, see what you made',
      `<div class="empty">No commodity trades found for ${sctE(currentAccount||'this account')} yet. Buy cargo at a trade terminal and it shows up here${served?' while you play':' after a refresh'}.</div>`);
    trmWire(); sctLostWire(); sctPoll(); return;
  }
  const T=d.totals, S=T.session, D=T.today, AL=T.all;
  const K=kpiRow([
    [icon('credits'), sctP(S.profit), 'This session', `${S.runs} run${S.runs===1?'':'s'}${S.per_hour!=null?' · '+sctA(S.per_hour)+'/h':''}`],
    [icon('calendar'), sctP(D.profit), 'Today', `${fmt(Math.round(D.scu))} SCU sold${D.margin!=null?' · '+sctPct(D.margin):''}`],
    [icon('spend'), sctP(AL.profit), 'All time', `${AL.runs} runs${AL.per_hour!=null?' · '+sctA(AL.per_hour)+'/h':''}${AL.free>1?' · '+sctA(AL.free)+' from free cargo':''}`],
    d.hold.length ? [icon('cargo'), fmt(+d.hold_scu.toFixed(1)), 'SCU in your hold', `${sctA(d.hold_cost)} paid, not sold yet`]
                  : [icon('cargo'), '0', 'SCU in your hold', 'hold is empty', 'na'],
  ]);
  const hold=d.hold.length?`<table class="sct-t"><thead><tr><th>Commodity</th><th>Bought at</th><th class="n">SCU</th><th class="n">Paid/SCU</th><th class="n">Paid</th><th class="n">Held</th>${served?'<th>Best place to sell</th><th></th>':''}</tr></thead><tbody>`+
    d.hold.map(l=>`<tr><td>${sctE(l.commodity)}</td><td>${sctE(l.where)}</td><td class="n">${fmt(+l.scu.toFixed(2))}</td><td class="n">${fmt(Math.round(l.per))}</td><td class="n">${sctA(l.cost)}</td><td class="n">${sctMin(l.age_min)}</td>${served?`<td>${trmHold(l.commodity,l.scu,l.per)}</td><td class="n"><button class="sct-lost" data-lot="${sctE(l.t)}" data-g="${sctE(l.g)}" data-what="${sctE(fmt(+l.scu.toFixed(2))+' SCU '+l.commodity)}" title="The cargo is gone but the log never showed it leaving (ship lost, a game bug). Counts it as sold for 0.">Mark as lost</button></td>`:''}</tr>`).join('')+`</tbody></table>`
    :'<div class="empty">Nothing in the hold. Everything you bought has been sold.</div>';
  const routes=d.routes.length?`<table class="sct-t"><thead><tr><th>Route</th><th class="n">Sales</th><th class="n">Profit</th><th class="n">Per SCU</th><th class="n">Margin</th></tr></thead><tbody>`+
    d.routes.slice(0,12).map(r=>`<tr><td>${sctE(r.commodity)}<div class="sub">${sctE(r.from)} → ${sctE(r.to)}${r.avg_min!=null?' · '+sctMin(r.avg_min)+' held':''}</div></td><td class="n">${r.legs}</td><td class="n">${sctP(r.profit)}</td><td class="n">${r.per_scu==null?'—':sctA(r.per_scu)}</td><td class="n">${sctPct(r.margin)}</td></tr>`).join('')+`</tbody></table>`
    :'<div class="empty">No sales yet.</div>';
  const last=d.last_trade?`last trade ${sctAgo(d.last_trade)}`:'';
  $('#content').innerHTML=`<div class="sct-head">${badge}<span>${sctE(currentAccount||'')} · ${AL.legs} sales · ${last}</span></div>`+trmCard()+K+
    group(1+g,'cargo','In your hold','Bought and not sold yet'+(served?' · updates while you play':''), `<div class="card">${hold}</div>`)+
    group(2+g,'trade','Trade runs','A run starts with a purchase and ends when the hold is empty again · newest first',
      `<div class="sct-runs">${d.runs.slice(0,30).map(sctRun).join('')}</div>`)+
    group(3+g,'space','Routes &amp; commodities','Where you bought, where you sold, and what paid',
      `<div class="grid2"><div class="card"><h3>Best routes <span class="u">— by profit</span></h3>${routes}</div>`+
      barsCard('Profit by commodity','aUEC','sctComm')+`</div>`)+
    group(4+g,'time','Profit over time','Running total, one point per sale', `<div class="card">${sctChart(d.cumulative)}</div>`)+
    noteFold(`Profit is worked out from your log: each sale is matched to the purchases it came from, oldest first.`,
      `The game logs every commodity buy and sell with its price, but not your wallet, fees or losses, so these are trade margins rather than bank balance. `+
      `A run ends when everything you bought has been sold. `+
      (d.unmatched_scu>1e-6?`${fmt(+d.unmatched_scu.toFixed(1))} SCU was sold with no purchase in your logs (picked up, or bought before your oldest log). That money counts toward profit as free cargo, but margins only use cargo you paid for. `:'')+
      `Commodity names come from the game files; after a big patch a new one can show as "Unknown" until the list is rebuilt.`);
  hbars($('#sctComm'), d.commodities.filter(c=>c.profit>0).map(c=>({label:c.commodity, value:c.profit,
    disp:sctA(c.profit)+' · '+fmt(Math.round(c.scu))+' SCU', sub:`${c.legs} sale${c.legs===1?'':'s'} · ${sctPct(c.margin)} margin`})));
  $('#content').querySelectorAll('.sct-run').forEach(el=>el.addEventListener('toggle',()=>{
    el.open?SCT_OPENED.add(el.dataset.run):SCT_OPENED.delete(el.dataset.run); }));
  trmWire(); sctLostWire(); sctPoll();
}
"""
