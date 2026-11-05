#!/usr/bin/env python3
"""Rebuild ../sc_commodities.json (resource GUID -> commodity name) from Data.p4k.

Fork addition, for the Trade runs section. Run after a big game patch if trades
start showing "Unknown #xxxx":  python3 tools/build_commodities.py [path/to/Data.p4k]
Needs the zstandard package (pip install zstandard).
Pulls Data/Game2.dcb out of Data.p4k (into /tmp, ~340 MB), finds the record
table by a known commodity GUID, and reads every ResourceType.* record name.
Assumes DataCore v8 records: name u32, 3 x u32, GUID (16 bytes), 2 x u16 = 36 bytes.
"""
import json, re, struct, sys, tempfile, uuid
from pathlib import Path

from p4k_extract import get

HERE = Path(__file__).resolve().parent.parent
LIVE = Path.home() / "Games/star-citizen/drive_c/Program Files/Roberts Space Industries/StarCitizen/LIVE"

KNOWN = uuid.UUID("d5506a24-5729-4354-81fb-0959173357c4")  # Medical Supplies
SZ = 36

def enc(u):
    b = u.bytes
    return b[0:8][::-1] + b[8:16][::-1]

def main():
    with tempfile.TemporaryDirectory() as td:
        dcb = Path(td) / "Game.dcb"
        get(sys.argv[1] if len(sys.argv) > 1 else str(LIVE / "Data.p4k"), "Data/Game2.dcb", str(dcb))
        d = dcb.read_bytes()
    def rec(p):
        name, _, _, st = struct.unpack("<IIII", d[p:p + 16])
        g = d[p + 16:p + 32]
        return name, st, uuid.UUID(bytes=g[0:8][::-1] + g[8:16][::-1])
    nstruct = struct.unpack("<I", d[16:20])[0]
    ok = lambda p: 0 <= p and rec(p)[1] < nstruct and rec(p)[0] < 50_000_000
    hit = None
    for m in re.finditer(re.escape(enc(KNOWN)), d):
        p = m.start() - 16
        if ok(p) and ok(p - SZ) and ok(p + SZ) and rec(p - SZ)[1] == rec(p)[1]:
            hit = p
            break
    if hit is None:
        sys.exit("Couldn't find the record table; the file format probably changed.")
    near = [rec(hit + SZ * i) for i in range(-3, 4)]
    base = None
    for m in re.finditer(rb"ResourceType\.", d):
        b = m.start() - near[3][0]
        if b >= 0 and all(d[b + r[0]:b + r[0] + 13] == b"ResourceType." for r in near):
            base = b
            break
    if base is None:
        sys.exit("Couldn't find the name strings.")
    start = hit
    while ok(start - SZ):
        start -= SZ
    out, p = {}, start
    while ok(p):
        name, _, gid = rec(p)
        e = d.find(b"\0", base + name)
        n = d[base + name:e]
        if n.startswith(b"ResourceType."):
            out[str(gid)] = n[13:].decode("utf-8", "replace")
        p += SZ
    (HERE / "sc_commodities.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(f"Wrote {len(out)} commodities to {HERE / 'sc_commodities.json'}")

if __name__ == "__main__":
    main()
