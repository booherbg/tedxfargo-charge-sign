#!/usr/bin/env python3
"""Simulates WLED v16.0.1 ledmap parsing against the emitted wled/*/ledmap.json.

Ported from WS2812FX::deserializeMap (wled/WLED @ v16.0.1, wled00/FX_fcn.cpp).
The parser is ASYMMETRIC and that asymmetry is the whole reason this file exists:

  width/height -> readObjectFromFile() + ArduinoJSON filter  (real parse, whitespace-OK)
  map array    -> f.find("\"map\":[")                        (RAW BYTE SEARCH, no space!)

So `json.dump(d, fp)` -- which writes `"map": [` with a space -- loads width/height
fine (isMatrix=true, maxWidth/maxHeight set) but ZERO map entries. WLED then falls
back to identity mapping and crams the chain row-major into the top rows: the sign
lights up with plausible colors that look nothing like the design. It does not fail
loudly. Dump ledmaps with separators=(",", ":") or this comes back.

Run: python3 tools/test_wled_ledmap.py
"""
import json, sys

GAP = 0xFFFF  # WLED's internal "no LED here"


def _atoi(b: bytes) -> int:
    """C atoi(): optional sign, leading digits, stop at first non-digit."""
    s, i = b.lstrip(b" \t\n\r"), 0
    sign = 1
    if i < len(s) and s[i:i + 1] in (b"-", b"+"):
        sign = -1 if s[i:i + 1] == b"-" else 1
        i += 1
    n = 0
    while i < len(s) and 48 <= s[i] <= 57:
        n = n * 10 + (s[i] - 48)
        i += 1
    return sign * n


def deserialize_map(raw: bytes):
    """Returns (maxWidth, maxHeight, isMatrix, customMappingTable).
    Faithful to the v16.0.1 control flow, including the byte search."""
    root = json.loads(raw)

    # --- width/height: StaticJsonDocument filter + readObjectFromFile -> real parse
    maxW = maxH = None
    is_matrix = False
    if root.get("width") is not None or root.get("height") is not None:
        maxW = min(max(int(root.get("width", 1)), 1), 255)
        maxH = min(max(int(root.get("height", 1)), 1), 255)
        is_matrix = True

    # getLengthTotal() == maxWidth*maxHeight once isMatrix
    length_total = (maxW * maxH) if is_matrix else 0

    # --- map: File f; f.find("\"map\":["); while (f.available()) ...
    table = []
    pos = raw.find(b'"map":[')
    if pos < 0:
        # Stream::find() consumed the file to EOF -> f.available()==false ->
        # the read loop never runs -> customMappingSize stays 0. Silent.
        return maxW, maxH, is_matrix, table

    stream = raw[pos + len(b'"map":['):]
    while stream:                                    # while (f.available())
        chunk, sep, rest = stream.partition(b",")    # readBytesUntil(',', number, 31)
        number = chunk[:31]
        stream = rest if sep else b""
        if len(number) == 0:
            break                                    # nothing to read, stop
        end = number.find(b"]")
        found_digit = end == -1
        if end != -1:
            i = 0
            while i < 32:
                if i < len(number) and 48 <= number[i] <= 57:
                    found_digit = True
                if found_digit or i == end:
                    break
                i += 1
        if not found_digit:
            break
        index = _atoi(number)
        if index < 0 or index > 65535:
            index = GAP                              # -1 gaps land here
        table.append(index)
        if end != -1:
            break                                    # closing ']' seen
        if len(table) >= length_total:
            break
    return maxW, maxH, is_matrix, table


def check(path: str) -> bool:
    raw = open(path, "rb").read()
    src = json.loads(raw)
    W, H = src["width"], src["height"]
    grid = src["map"]
    expect = [GAP if v < 0 else v for v in grid]
    real_px = sum(1 for v in grid if v >= 0)

    maxW, maxH, is_matrix, table = deserialize_map(raw)
    ok = True

    def t(cond, label, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print("  %s %s%s" % ("PASS" if cond else "FAIL", label,
                             "" if cond else "  <-- " + detail))

    print("%s  (%dx%d, %d real pixels)" % (path, W, H, real_px))
    t(b'"map":[' in raw, 'byte-exact \'"map":[\' present',
      "spaced '\"map\": [' -> f.find() misses -> 0 entries loaded, silently")
    t(is_matrix and (maxW, maxH) == (W, H), "isMatrix + %dx%d from ledmap" % (W, H),
      "got %sx%s" % (maxW, maxH))
    t(len(table) == W * H, "loaded %d/%d cells" % (len(table), W * H),
      "customMappingSize=%d -> identity map -> chain crammed into top rows"
      % len(table))
    t(table == expect, "map values round-trip (-1 -> 0xFFFF)")
    if len(table) == W * H:
        lit = [v for v in table if v != GAP]
        t(len(lit) == real_px, "%d lit cells == %d physical pixels" % (len(lit), real_px))
        t(len(set(lit)) == len(lit), "no duplicate LED index")
        t(sorted(set(lit)) == list(range(real_px)), "chain indices are contiguous 0..%d" % (real_px - 1))
    t(maxW is not None and maxW <= 255 and maxH <= 255, "dims within WLED's 255 clamp",
      "min(max(v,1),255) would silently truncate")
    return ok


if __name__ == "__main__":
    files = sys.argv[1:] or ["wled/board-controller/ledmap.json",
                             "wled/word-controller/ledmap.json"]
    good = all([check(f) for f in files])
    print("\n%s" % ("ALL PASS" if good else "FAILURES -- see above"))
    sys.exit(0 if good else 1)
