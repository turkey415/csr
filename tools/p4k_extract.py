#!/usr/bin/env python3
"""List or extract files from Star Citizen's Data.p4k.

It's a zip64 archive with custom extra fields that Python's zipfile rejects,
so the central directory is read by hand. Method 100 = zstd.
Usage: p4k_extract.py Data.p4k list <substring>
       p4k_extract.py Data.p4k get <exact name> <out file>
"""
import struct, sys, zstandard

def entries(p4k):
    with open(p4k, "rb") as f:
        f.seek(0, 2); size = f.tell()
        f.seek(size - 65536 - 22); tail = f.read()
        loc = tail.rfind(b"PK\x06\x07")
        eocd64 = struct.unpack("<Q", tail[loc + 8:loc + 16])[0]
        f.seek(eocd64); z = f.read(56)
        count, cd_size, cd_off = struct.unpack("<QQQ", z[32:56])
        f.seek(cd_off); cd = f.read(cd_size)
    p = 0
    for _ in range(count):
        (sig, _, _, flags, method, _, _, crc, csize, usize, nlen, elen, clen, _, _, _, hoff) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + elen]
        q = 0
        while q + 4 <= len(extra):
            tag, ln = struct.unpack("<HH", extra[q:q + 4])
            if tag == 1:
                vals = extra[q + 4:q + 4 + ln]; i = 0
                if usize == 0xFFFFFFFF: usize = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                if csize == 0xFFFFFFFF: csize = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                if hoff == 0xFFFFFFFF: hoff = struct.unpack("<Q", vals[i:i + 8])[0]; i += 8
                break
            q += 4 + ln
        yield name, method, csize, usize, hoff
        p += 46 + nlen + elen + clen

def get(p4k, name, out):
    for n, method, csize, usize, hoff in entries(p4k):
        if n.replace("\\", "/").lower() == name.lower():
            with open(p4k, "rb") as f:
                f.seek(hoff); h = f.read(30)
                nl, el = struct.unpack("<HH", h[26:30])
                f.seek(hoff + 30 + nl + el); raw = f.read(csize)
            data = raw if method == 0 else zstandard.ZstdDecompressor().decompress(raw, max_output_size=usize)
            open(out, "wb").write(data)
            print(f"{n}: method {method}, {len(data)} bytes -> {out}")
            return
    sys.exit("not found")

if __name__ == "__main__":
    p4k, cmd = sys.argv[1:3]
    if cmd == "list":
        for n, *_ in entries(p4k):
            if sys.argv[3].lower() in n.lower(): print(n)
    else:
        get(p4k, sys.argv[3], sys.argv[4])
