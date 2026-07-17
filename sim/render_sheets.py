#!/usr/bin/env python3
"""Render simdump.json into per-effect contact-sheet PNGs (pure stdlib).
Each sheet: 8 frames stacked vertically, LEDs drawn as glowing discs at their
true wired positions. Usage: python3 sim/render_sheets.py <dumpdir> [outdir]"""
import json, math, os, struct, sys, zlib

dumpdir = sys.argv[1]
outdir = sys.argv[2] if len(sys.argv) > 2 else dumpdir
dump = json.load(open(os.path.join(dumpdir, "simdump.json")))
px = json.load(open("src/parts/word_pixmap.json"))["pixels"]
N = dump["N"]
assert len(px) == N

xs = [p["x"] for p in px]; ys = [p["y"] for p in px]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
SCALE = 0.33
PAD = 12
FW = int((x1 - x0) * SCALE) + 2 * PAD          # frame width
FH = int((y1 - y0) * SCALE) + 2 * PAD          # frame height
GAP = 3

# precompute LED positions in frame coords (y flipped: physical y is up)
pos = [(PAD + (p["x"] - x0) * SCALE, PAD + (y1 - p["y"]) * SCALE) for p in px]

# glow kernel: radius R, weight (1 - d/R)^2
R = 4.2
kern = []
for dy in range(-5, 6):
    for dx in range(-5, 6):
        d = math.hypot(dx, dy)
        if d <= R:
            kern.append((dx, dy, (1 - d / R) ** 2))

def write_png(path, w, h, buf):               # buf = bytearray of RGB rows
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    raw = b"".join(b"\x00" + bytes(buf[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)

for eff in dump["effects"]:
    frames = eff["samples"]
    SW, SH = FW, (FH + GAP) * len(frames)
    acc = [[0.0] * (SW * 3) for _ in range(SH)]
    for fi, fr in enumerate(frames):
        oy = fi * (FH + GAP)
        # frame background (very dark blue-gray) + divider
        for y in range(FH):
            row = acc[oy + y]
            for x in range(SW):
                row[x * 3 + 0] += 8; row[x * 3 + 1] += 9; row[x * 3 + 2] += 12
        # timestamp ticks: fi+1 dots at top-left
        for d in range(fi + 1):
            for yy in range(2):
                row = acc[oy + 2 + yy]
                for xx in range(2):
                    ix = (4 + d * 4 + xx) * 3
                    row[ix] += 120; row[ix + 1] += 120; row[ix + 2] += 120
        for i, c in enumerate(fr["rgb"]):
            r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
            X, Y = pos[i]
            if r | g | b:
                for dx, dy, w in kern:
                    xi, yi = int(X + dx), int(Y + dy)
                    if 0 <= xi < SW and 0 <= yi < FH:
                        row = acc[oy + yi]
                        row[xi * 3] += r * w; row[xi * 3 + 1] += g * w; row[xi * 3 + 2] += b * w
            else:                              # unlit LED: faint dot for context
                xi, yi = int(X), int(Y)
                if 0 <= xi < SW and 0 <= yi < FH:
                    row = acc[oy + yi]
                    row[xi * 3] += 26; row[xi * 3 + 1] += 28; row[xi * 3 + 2] += 32
    buf = bytearray(SW * SH * 3)
    for y in range(SH):
        row = acc[y]
        for x in range(SW * 3):
            v = row[x]
            buf[y * SW * 3 + x] = 255 if v > 255 else int(v)
    name = eff["name"].replace(" ", "_").replace("/", "-")
    out = os.path.join(outdir, f"sheet_{name}.png")
    write_png(out, SW, SH, buf)
    print("wrote", out)
