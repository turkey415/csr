#!/usr/bin/env python3
"""Build sc_map.json, the data behind the Starmap section.

Two sources:
  * Star Citizen's own Data.p4k: the system object containers hold the real position
    of every planet, moon, Lagrange station, orbital station and jump gate, and each
    planet's container gives its radius. Standard library only: the containers we
    need are stored uncompressed in the p4k, and are plain zips inside.
  * UEX Corp's public API (api.uexcorp.space): what each place offers. Refuel, ship
    dealers, rentals, ship parts, FPS arms and armour, repair, medical, trade,
    refinery. Also the outposts on each body, which the game files only hold as
    unnamed prefabs.

Usage: python tools/build_map.py "<...>/StarCitizen/LIVE/Data.p4k" [--uex-cache DIR]
Writes sc_map.json next to sc_stats.py. Rerun after a patch moves things.
"""
import argparse, io, json, math, os, re, struct, sys, time, urllib.request, zipfile, zlib
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "sc_map.json")
UEX = "https://api.uexcorp.space/2.0/"
UA = "CSR-starmap-builder"


# ---------------------------------------------------------------- p4k reading
def p4k_index(path):
    """{lower-case name: (method, csize, usize, header offset)} from the zip64 directory."""
    with open(path, "rb") as f:
        f.seek(0, 2); size = f.tell()
        f.seek(size - 65536 - 22); tail = f.read()
        loc = tail.rfind(b"PK\x06\x07")
        eocd64 = struct.unpack("<Q", tail[loc + 8:loc + 16])[0]
        f.seek(eocd64); z = f.read(56)
        count, cd_size, cd_off = struct.unpack("<QQQ", z[32:56])
        f.seek(cd_off); cd = f.read(cd_size)
    out, p = {}, 0
    for _ in range(count):
        (_, _, _, _, method, _, _, _, csize, usize, nlen, elen, clen, _, _, _, hoff) = \
            struct.unpack("<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + elen]
        q = 0
        while q + 4 <= len(extra):
            tag, ln = struct.unpack("<HH", extra[q:q + 4])
            if tag == 1:
                vals, i = extra[q + 4:q + 4 + ln], 0
                if usize == 0xFFFFFFFF: usize = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                if csize == 0xFFFFFFFF: csize = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                if hoff == 0xFFFFFFFF: hoff = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                break
            q += 4 + ln
        out[name.replace("\\", "/").lower()] = (method, csize, usize, hoff)
        p += 46 + nlen + elen + clen
    return out


def p4k_read(path, idx, name):
    method, csize, usize, hoff = idx[name.lower()]
    with open(path, "rb") as f:
        f.seek(hoff); h = f.read(30)
        nl, el = struct.unpack("<HH", h[26:30])
        f.seek(hoff + 30 + nl + el); raw = f.read(csize)
    if method == 0:
        return raw
    if method == 8:
        return zlib.decompressobj(-15).decompress(raw)
    try:
        import zstandard   # only needed if CIG ever compresses the containers
    except ImportError:
        sys.exit(f"{name} is zstd-compressed; pip install zstandard")
    return zstandard.ZstdDecompressor().decompress(raw, max_output_size=usize)


def socpak_xml(blob, inner):
    """The main XML inside a socpak. Its local headers use backslashes, which zipfile
    rejects as a name mismatch, so entries are read from their offsets directly."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    for i in z.infolist():
        if i.filename.replace("\\", "/").lower() == inner.lower():
            b = io.BytesIO(blob); b.seek(i.header_offset); h = b.read(30)
            nl, el = struct.unpack("<HH", h[26:30])
            b.seek(i.header_offset + 30 + nl + el); raw = b.read(i.compress_size)
            data = raw if i.compress_type == 0 else zlib.decompressobj(-15).decompress(raw)
            return ET.fromstring(data)
    return None


def container(p4k, idx, rel):
    name = f"data/objectcontainers/pu/system/{rel}.socpak"
    if name not in idx:
        return None
    return socpak_xml(p4k_read(p4k, idx, name), os.path.basename(rel) + ".xml")


def vec(el):
    return [float(v) for v in (el.get("pos") or "0,0,0").split(",")]


def walk(root, ox=0.0, oy=0.0, oz=0.0, depth=0):
    """(entityName, absolute x, y, z, depth) for every child container, in metres."""
    for c in root.findall("./ChildObjectContainers/Child"):
        p = vec(c)
        ax, ay, az = ox + p[0], oy + p[1], oz + p[2]
        yield c.get("entityName") or "", ax, ay, az, depth
        yield from walk(c, ax, ay, az, depth + 1)


# ---------------------------------------------------------------- UEX
def uex(endpoint, cache):
    path = os.path.join(cache, endpoint + ".json") if cache else None
    if path and os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))["data"]
    req = urllib.request.Request(UEX + endpoint, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=60).read()
    if path:
        os.makedirs(cache, exist_ok=True)
        open(path, "wb").write(raw)
    return json.loads(raw)["data"]


# ---------------------------------------------------------------- the systems
# Body ids follow the game's container names. Names are the in-game ones.
STANTON = {
    "stanton1": ("Hurston", "HUR"), "stanton2": ("Crusader", "CRU"),
    "stanton3": ("ArcCorp", "ARC"), "stanton4": ("microTech", "MIC"),
}
MOONS = {
    "stanton1a": "Arial", "stanton1b": "Aberdeen", "stanton1c": "Magda", "stanton1d": "Ita",
    "stanton2a": "Cellin", "stanton2b": "Daymar", "stanton2c": "Yela",
    "stanton3a": "Lyria", "stanton3b": "Wala",
    "stanton4a": "Calliope", "stanton4b": "Clio", "stanton4c": "Euterpe",
    "pyro5a": "Ignis", "pyro5b": "Vatra", "pyro5c": "Adir", "pyro5d": "Fairo",
    "pyro5e": "Fuego", "pyro5f": "Vuur",
}
PYRO = {"pyro1": "Pyro I", "pyro2": "Monox", "pyro3": "Bloom", "pyro4": "Pyro IV",
        "pyro5": "Pyro V", "pyro6": "Terminus"}
NYX = {"nyx1": "Nyx I", "nyx2": "Nyx II", "nyx3": "Nyx III"}
# how UEX spells a body, when it differs from ours
UEX_BODY = {"MicroTech": "microTech", "Pyro VI": "Terminus"}
# gates: (our id, system, game container name, CSR location code, display name, leads to)
GATES = [
    ("jp_stanton_pyro", "stanton", "OOC_JumpPoint_stanton_pyro", "RR_JP_StantonPyro", "Pyro Gateway", "pyro"),
    ("jp_stanton_nyx", "stanton", "OOC_JumpPoint_stanton_magnus", "RR_JP_StantonMagnus", "Nyx Gateway", "nyx"),
    ("jp_stanton_terra", "stanton", "OOC_JumpPoint_stanton_terra", "RR_JP_StantonTerra", "Terra Gateway", "terra"),
    ("jp_pyro_stanton", "pyro", "jumppoint_pyro_stanton", "RR_JP_PyroStanton", "Stanton Gateway", "stanton"),
    ("jp_pyro_nyx", "pyro", "jumppoint_pyro_nyx", "RR_JP_PyroNyx", "Nyx Gateway", "nyx"),
    ("jp_nyx_pyro", "nyx", "jumppoint_nyx_pyro", "RR_JP_NyxPyro", "Pyro Gateway", "pyro"),
    ("jp_nyx_stanton", "nyx", "jumppoint_nyx_castra", "RR_JP_NyxCastra", "Stanton Gateway", "stanton"),
]
# UEX station / city name -> our node id, where the name alone decides it
UEX_STATION = {
    "Everus Harbor": "leo_stanton1", "Seraphim Station": "leo_stanton2",
    "Baijini Point": "leo_stanton3", "Port Tressler": "leo_stanton4",
    "Orbituary": "leo_pyro3", "Ruin Station": "leo_pyro6",
    "Green Imperial Housing Exchange": "grimhex",
    "Wikelo Emporium Dasi Station": "wikelo_stanton1", "Wikelo Emporium Selo Station": "wikelo_stanton2",
    "Wikelo Emporium Kinga Station": "wikelo_stanton4",
    "Pyro Gateway (Stanton)": "jp_stanton_pyro", "Nyx Gateway (Stanton)": "jp_stanton_nyx",
    "Terra Gateway (Stanton)": "jp_stanton_terra", "Stanton Gateway (Pyro)": "jp_pyro_stanton",
    "Nyx Gateway (Pyro)": "jp_pyro_nyx", "Pyro Gateway (Nyx)": "jp_nyx_pyro",
    "Stanton Gateway (Nyx)": "jp_nyx_stanton",
}
UEX_CITY = {"Lorville": "city_lorville", "Orison": "city_orison", "Area 18": "city_area18",
            "New Babbage": "city_newbabbage", "Levski": "city_levski"}


def gm(v):
    return round(v / 1e9, 5)          # metres -> gigametres, which is what the page draws in


def build(p4k):
    idx = p4k_index(p4k)
    nodes, systems = {}, {}

    def add(nid, **kw):
        kw.setdefault("codes", [])
        nodes[nid] = dict(id=nid, **kw)
        return nodes[nid]

    def radius(rel):
        """Median distance of a body's own surface children: its radius in km."""
        root = container(p4k, idx, rel)
        if root is None:
            return None, []
        rs, kids = [], []
        for c in root.findall("./ChildObjectContainers/Child"):
            p = vec(c); r = math.sqrt(sum(v * v for v in p))
            kids.append((c.get("entityName") or "", p, r))
            if r > 1000:
                rs.append(r)
        rs.sort()
        return (round(rs[len(rs) // 2] / 1000) if rs else None), kids

    # --- Stanton
    root = container(p4k, idx, "stanton/stantonsystem")
    systems["stanton"] = {"id": "stanton", "name": "Stanton", "star": "Stanton", "kind": "UEE"}
    add("star_stanton", sys="stanton", type="star", name="Stanton", x=0, y=0, r_km=696000)
    for name, x, y, z, d in walk(root):
        m = re.match(r"OOC_Stanton_(\d)([a-d]?)_", name)
        if m:
            pid = "stanton" + m.group(1)
            bid = pid + m.group(2)
            if m.group(2):
                add(bid, sys="stanton", type="moon", name=MOONS[bid], parent=pid, x=gm(x), y=gm(y))
            else:
                add(bid, sys="stanton", type="planet", name=STANTON[bid][0], parent="star_stanton", x=gm(x), y=gm(y))
            continue
        m = re.match(r"OOC_Stanton(\d)_L(\d)$", name)
        if m:
            pid, n = "stanton" + m.group(1), m.group(2)
            code = f"{STANTON[pid][1]}-L{n}"
            add(f"l_{pid}_{n}", sys="stanton", type="lagrange", name=code, parent=pid, x=gm(x), y=gm(y),
                codes=[f"RR_{STANTON[pid][1]}_L{n}"], lpoint=int(n))
            continue
        m = re.match(r"ab_collector_gas_Stanton(\d)$", name)
        if m:
            add(f"wikelo_stanton{m.group(1)}", sys="stanton", type="station", name="Wikelo Emporium",
                parent="stanton" + m.group(1), x=gm(x), y=gm(y), codes=[f"TheCollectorAsteroid_Stanton{m.group(1)}"])
            continue
        if name == "OOC_AaronHalo":
            continue
    # --- Pyro
    root = container(p4k, idx, "pyro/pyrosystem")
    systems["pyro"] = {"id": "pyro", "name": "Pyro", "star": "Pyro", "kind": "Unclaimed"}
    add("star_pyro", sys="pyro", type="star", name="Pyro", x=0, y=0, r_km=550000)
    for name, x, y, z, d in walk(root):
        if re.match(r"pyro\d$", name):
            add(name, sys="pyro", type="planet", name=PYRO[name], parent="star_pyro", x=gm(x), y=gm(y))
        elif re.match(r"pyro5[a-f]$", name):
            add(name, sys="pyro", type="moon", name=MOONS[name], parent="pyro5", x=gm(x), y=gm(y))
        else:
            m = re.match(r"P(\d)_L(\d)$", name)
            if m:
                pid = "pyro" + m.group(1)
                add(f"l_{pid}_{m.group(2)}", sys="pyro", type="lagrange", name=f"{PYRO[pid]} L{m.group(2)}",
                    parent=pid, x=gm(x), y=gm(y), codes=[f"RR_P{m.group(1)}_L{m.group(2)}"], lpoint=int(m.group(2)))
    # Pyro IV sits in Pyro V's container in the game files; it is a planet of its own
    if "pyro4" in nodes:
        nodes["pyro4"]["parent"] = "star_pyro"
    # --- Nyx
    root = container(p4k, idx, "nyx/nyxsystem")
    systems["nyx"] = {"id": "nyx", "name": "Nyx", "star": "Nyx", "kind": "Unclaimed",
                      "rings": [{"name": "Glaciem Ring", "r": 15.0, "w": 1.4}, {"name": "Keeger Belt", "r": 48.0, "w": 2.6}]}
    add("star_nyx", sys="nyx", type="star", name="Nyx", x=0, y=0, r_km=600000)
    for name, x, y, z, d in walk(root):
        if re.match(r"Nyx\d$", name):
            nid = name.lower()
            add(nid, sys="nyx", type="planet", name=NYX[nid], parent="star_nyx", x=gm(x), y=gm(y))
        elif name == "glaciemring_segment_levski":
            add("delamar", sys="nyx", type="moon", name="Delamar", parent="star_nyx", x=gm(x), y=gm(y), r_km=21)
            add("city_levski", sys="nyx", type="city", name="Levski", parent="delamar", x=gm(x), y=gm(y),
                codes=["Nyx_Levski"])
        else:
            m = re.match(r"keeger_segment_social_00(\d)$", name)
            if m:
                add(f"keeger_{m.group(1)}", sys="nyx", type="station", name=f"Keeger Belt {m.group(1)}",
                    parent="star_nyx", x=gm(x), y=gm(y), codes=[f"AsteroidClusterBase_Nyx_Social_Keeger_00{m.group(1)}"])
    # --- gates
    sysroots = {"stanton": "stanton/stantonsystem", "pyro": "pyro/pyrosystem", "nyx": "nyx/nyxsystem"}
    gate_pos = {}
    for s, rel in sysroots.items():
        for name, x, y, z, d in walk(container(p4k, idx, rel)):
            gate_pos[(s, name)] = (gm(x), gm(y))
    links = []
    for gid, s, cname, code, label, to in GATES:
        if (s, cname) in gate_pos:
            x, y = gate_pos[(s, cname)]
            add(gid, sys=s, type="gate", name=label, parent=f"star_{s}", x=x, y=y, codes=[code], to=to)
        if (to, s) not in [(a, b) for a, b in links]:
            links.append((s, to))
    # --- planet and moon radii; orbital stations and cities inside each body
    for bid, n in list(nodes.items()):
        if n["type"] not in ("planet", "moon") or n.get("r_km"):
            continue
        sysn = n["sys"]
        r, kids = radius(f"{sysn}/{bid}")
        n["r_km"] = r
        for kname, p, kr in kids:
            px, py = n["x"] + gm(p[0]), n["y"] + gm(p[1])
            lat = round(math.degrees(math.asin(p[2] / kr)), 2) if kr else 0
            lon = round(math.degrees(math.atan2(p[1], p[0])), 2)
            if re.match(r"(ObjectContainer_RestStop|rs_ext_.*leo)", kname, re.I):
                add(f"leo_{bid}", sys=sysn, type="station", name="", parent=bid, x=px, y=py, alt_km=round((kr / 1000) - (r or 0)))
            city = {"ObjectContainer_Lorville_City": ("city_lorville", "Lorville", "Stanton1_Lorville"),
                    "Orison_LOC": ("city_orison", "Orison", "Stanton2_Orison"),
                    "Area18_City_objectContainer": ("city_area18", "Area18", "Stanton3_Area18"),
                    "NewBabbage_LOC": ("city_newbabbage", "New Babbage", "Stanton4_NewBabbage")}.get(kname)
            if city:
                add(city[0], sys=sysn, type="city", name=city[1], parent=bid, x=px, y=py, lat=lat, lon=lon, codes=[city[2]])
    leo_names = {"leo_stanton1": ("Everus Harbor", "RR_HUR_LEO"), "leo_stanton2": ("Seraphim Station", "RR_CRU_LEO"),
                 "leo_stanton3": ("Baijini Point", "RR_ARC_LEO"), "leo_stanton4": ("Port Tressler", "RR_MIC_LEO"),
                 "leo_pyro3": ("Orbituary", "RR_P3_LEO"), "leo_pyro6": ("Ruin Station", "RR_P6_LEO")}
    for nid, (nm, code) in leo_names.items():
        if nid in nodes:
            nodes[nid].update(name=nm, codes=[code])
    # Grim HEX's container is not in the moon file we read; it orbits Yela close in
    if "stanton2c" in nodes and "grimhex" not in nodes:
        y = nodes["stanton2c"]
        add("grimhex", sys="stanton", type="station", name="Grim HEX", parent="stanton2c",
            x=round(y["x"] + 0.0006, 5), y=round(y["y"] + 0.0004, 5), codes=["GrimHEX"], approx=True)
    return nodes, systems, links


def services(nodes, cache):
    """Attach UEX services to nodes, and list outposts per body."""
    st = uex("space_stations", cache); ci = uex("cities", cache)
    op = uex("outposts", cache); te = uex("terminals", cache)
    by_name = {}
    for n in nodes.values():
        by_name.setdefault((n["sys"], n["name"].lower()), n["id"])

    def lagrange_id(orbit):
        m = re.match(r"(.+?) Lagrange Point (\d)$", orbit or "")
        if not m:
            return None
        body = UEX_BODY.get(m.group(1), m.group(1))
        for bid, nm in list(STANTON.items()) + [(k, v) for k, v in PYRO.items()]:
            nm = nm[0] if isinstance(nm, tuple) else nm
            if nm.lower() == body.lower():
                return f"l_{bid}_{m.group(2)}"
        return None

    def body_id(name):
        name = UEX_BODY.get(name, name)
        for n in nodes.values():
            if n["type"] in ("planet", "moon") and n["name"].lower() == (name or "").lower():
                return n["id"]
        return None

    uex_to_node = {}
    for s in st:
        if not s.get("is_available_live"):
            continue
        nid = UEX_STATION.get(s["name"]) or lagrange_id(s.get("orbit_name"))
        if nid in nodes and nodes[nid].get("kind"):
            continue                     # INS Jericho shares MIC-L1 with Shallow Frontier; first one wins
        if nid in nodes:
            n = nodes[nid]
            if n["type"] == "lagrange" or not n["name"] or n["name"].startswith("Wikelo"):
                n["name"] = s["name"]
            n["kind"] = "Station"
            n["svc"] = {k: 1 for k in ("refuel", "repair", "clinic", "habitation", "trade_terminal", "refinery",
                                        "cargo_center") if s.get("has_" + k)}
            n["armistice"] = bool(s.get("is_armistice"))
            uex_to_node[("station", s["id"])] = nid
        else:
            print("  unplaced station:", s["star_system_name"], s["name"], s.get("orbit_name"))
    for c in ci:
        nid = UEX_CITY.get(c["name"])
        if nid in nodes:
            n = nodes[nid]
            n["svc"] = {k: 1 for k in ("refuel", "repair", "clinic", "habitation", "trade_terminal", "refinery",
                                        "cargo_center") if c.get("has_" + k)}
            n["armistice"] = bool(c.get("is_armistice"))
            uex_to_node[("city", c["id"])] = nid
    outposts = {}
    for o in op:
        if not o.get("is_available_live"):
            continue
        bid = body_id(o.get("moon_name") or o.get("planet_name"))
        if not bid:
            print("  outpost with no body:", o["name"], o.get("moon_name"), o.get("planet_name"))
            continue
        rec = {"name": o["name"], "svc": {k: 1 for k in ("refuel", "repair", "clinic", "habitation", "trade_terminal",
                                                           "refinery") if o.get("has_" + k)}}
        outposts.setdefault(bid, []).append(rec)
        uex_to_node[("outpost", o["id"])] = (bid, rec)
    # terminals: what can be bought where
    for t in te:
        if not t.get("is_available_live") and not t.get("is_available"):
            continue
        key = (("station", t["id_space_station"]) if t.get("id_space_station") else
               ("city", t["id_city"]) if t.get("id_city") else
               ("outpost", t["id_outpost"]) if t.get("id_outpost") else None)
        tgt = uex_to_node.get(key)
        if tgt is None:
            continue
        rec = tgt[1] if isinstance(tgt, tuple) else nodes[tgt]
        svc = rec.setdefault("svc", {})
        shops = rec.setdefault("shops", {})
        label = (t.get("name") or "").split(" - ")[0].strip()
        kind = {"vehicle_buy": "ships", "vehicle_rent": "rental", "fuel": "refuel", "refinery": "refinery",
                "commodity": "trade_terminal", "commodity_raw": "trade_terminal"}.get(t["type"])
        if t["type"] == "item":
            kind = "fps" if t.get("is_shop_fps") else "parts" if t.get("is_shop_vehicle") else "shop"
        if not kind:
            continue
        svc[kind] = 1
        if kind in ("ships", "rental", "fps", "parts", "shop"):
            lst = shops.setdefault(kind, [])
            if label and label not in lst:
                lst.append(label)
    return outposts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("p4k", help="path to LIVE/Data.p4k")
    ap.add_argument("--uex-cache", help="read/write UEX responses here instead of always fetching")
    a = ap.parse_args()
    nodes, systems, links = build(a.p4k)
    outposts = services(nodes, a.uex_cache)
    for n in nodes.values():
        for k in ("svc", "shops"):
            if not n.get(k):
                n.pop(k, None)
    data = {"built": time.strftime("%Y-%m-%d"), "source": {"positions": "Star Citizen Data.p4k",
            "services": "UEX Corp (uexcorp.space)"},
            "systems": systems, "links": links, "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "outposts": outposts}
    json.dump(data, open(OUT, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    kinds = {}
    for n in nodes.values():
        kinds[n["type"]] = kinds.get(n["type"], 0) + 1
    print(f"wrote {OUT}: {len(nodes)} nodes {kinds}, {sum(map(len, outposts.values()))} outposts, "
          f"{os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
