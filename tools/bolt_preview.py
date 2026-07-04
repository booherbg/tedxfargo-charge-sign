#!/usr/bin/env python3
"""Raster preview for bolt-board compositions (pure stdlib -> PPM).
Draws 22mm bands for path groups (yellow/red), optional seams, pixels, face rect.
Usage (as a library):
    from bolt_preview import render
    render("out.ppm", face=(424,590), groups=[(paths_y, (240,200,40)), ...],
           seams_x=[212], seams_y=[295], px=[(x,y),...], flip_y=False)
"""
import math

def _stamp(img, W, H, x, y, r, col):
    x0, x1 = max(0, int(x - r)), min(W - 1, int(x + r) + 1)
    y0, y1 = max(0, int(y - r)), min(H - 1, int(y + r) + 1)
    r2 = r * r
    for yy in range(y0, y1 + 1):
        dy2 = (yy - y) * (yy - y)
        for xx in range(x0, x1 + 1):
            if (xx - x) * (xx - x) + dy2 <= r2:
                img[yy * W + xx] = col

def _line(img, W, H, a, b, w, col):
    L = math.dist(a, b)
    n = max(1, int(L * 2))
    for i in range(n + 1):
        t = i / n
        _stamp(img, W, H, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, w / 2, col)

def render(out, face, groups, seams_x=(), seams_y=(), px=(), flip_y=False,
           scale=2.0, band=22.0, bg=(24, 24, 24), face_col=(46, 46, 46)):
    W, H = int(face[0] * scale) + 20, int(face[1] * scale) + 20
    img = [bg] * (W * H)
    def T(q):
        x = q[0] * scale + 10
        y = (face[1] - q[1] if flip_y else q[1]) * scale + 10
        return (x, y)
    for yy in range(10, H - 10):
        for xx in range(10, W - 10):
            img[yy * W + xx] = face_col
    for paths, col in groups:
        for p in paths:
            for i in range(len(p) - 1):
                _line(img, W, H, T(p[i]), T(p[i + 1]), band * scale, col)
    for sx in seams_x:
        for yy in range(10, H - 10):
            x = int(sx * scale) + 10
            img[yy * W + x] = (255, 255, 255)
    for sy in seams_y:
        yv = int((face[1] - sy if flip_y else sy) * scale) + 10
        for xx in range(10, W - 10):
            img[yv * W + xx] = (255, 255, 255)
    for q in px:
        x, y = T(q)
        _stamp(img, W, H, x, y, 2.5, (30, 30, 200))
    with open(out, "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (W, H))
        f.write(bytes(v for c in img for v in c))
    return out

if __name__ == "__main__":
    import sys, re, json
    txt = open(sys.argv[1]).read()
    name = re.search(r"^(\w+)_paths", txt, re.M).group(1)
    paths = json.loads(re.search(name + r"_paths\s*=\s*(.*?);", txt, re.S).group(1))
    xs = [q[0] for p in paths for q in p]; ys = [q[1] for p in paths for q in p]
    face = (max(xs) + 15, max(ys) + 15)
    flip = "--flip" in sys.argv
    render(sys.argv[2], face, [(paths, (235, 200, 60))], flip_y=flip)
    print("wrote", sys.argv[2], "flip_y=", flip)
