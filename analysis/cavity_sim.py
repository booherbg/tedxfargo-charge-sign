#!/usr/bin/env python3
"""2D Monte-Carlo light sim for the approach-A masked reflector cavity.

Cross-section model (mm), z=0 at the back-plate top:
  - white diffuse side walls at x = +/-15, z in [0, face_z]   (Lambertian, reflectance R)
  - white diffuse back plate at z=0                            (Lambertian, reflectance R)
  - LED: Lambertian line source near the dome tip
  - perforated white mask: horizontal segment at z=mask_z, |x|<=mask_d/2,
        fraction `open` transmits, the rest diffuse-reflects (recycles), R loss
  - exit/measurement plane (diffuser face) at z=face_z: ray leaves, record x

Reports per config: efficiency (rays out the face), peak/mean (hotspot ratio,
1.0 = perfectly flat), CoV %, and an ASCII illuminance profile across the face.
Idealized (2D, no Fresnel/refraction at the face) -> read it for TRENDS &
ranking, not absolute photometry.
"""
import math, random

random.seed(12345)            # deterministic
HALF_W   = 15.0               # cell half-width (30mm cell)
R_WALL   = 0.92              # white PETG diffuse reflectance (~92%)
R_MASK   = 0.92
DOME     = 4.0               # LED tip height above plate
NB_MAX   = 60                # bounce cap
NBINS    = 15

def emit():
    # Lambertian upward from a small source near the dome tip
    x = random.uniform(-3.0, 3.0)
    z = DOME * 0.6
    phi = math.asin(2*random.random()-1)   # 2D cosine-weighted about +z
    return x, z, math.sin(phi), math.cos(phi)

def diffuse(nx, nz):
    # cosine-weighted direction about inward normal (nx,nz) in 2D
    phi = math.asin(2*random.random()-1)
    c, s = math.cos(phi), math.sin(phi)
    # rotate (s along tangent, c along normal) into world: normal=(nx,nz), tangent=(nz,-nx)
    dx = c*nx + s*nz
    dz = c*nz - s*nx
    return dx, dz

def run(face_z, mask_d, mask_z, open_frac, N=120000):
    bins = [0.0]*NBINS
    out = 0
    for _ in range(N):
        x, z, dx, dz = emit()
        for _ in range(NB_MAX):
            # candidate distances to each surface along (dx,dz)
            t = math.inf; hit = None
            if dz > 1e-9:
                tt = (face_z - z)/dz
                if 0 < tt < t: t, hit = tt, 'face'
            if dz < -1e-9:
                tt = (0.0 - z)/dz
                if 0 < tt < t: t, hit = tt, 'plate'
            if dx > 1e-9:
                tt = (HALF_W - x)/dx
                if 0 < tt < t: t, hit = tt, 'wall+'
            if dx < -1e-9:
                tt = (-HALF_W - x)/dx
                if 0 < tt < t: t, hit = tt, 'wall-'
            # mask plane crossing (thin, double-sided)
            if mask_d > 0 and abs(dz) > 1e-9:
                tt = (mask_z - z)/dz
                if 0 < tt < t:
                    xm = x + tt*dx
                    if abs(xm) <= mask_d/2:
                        t, hit = tt, 'mask'
            if hit is None: break
            x += t*dx; z += t*dz
            if hit == 'face':
                b = min(NBINS-1, max(0, int((x+HALF_W)/(2*HALF_W)*NBINS)))
                bins[b] += 1; out += 1; break
            elif hit == 'plate':
                if random.random() > R_WALL: break
                dx, dz = diffuse(0, 1)
            elif hit == 'wall+':
                if random.random() > R_WALL: break
                dx, dz = diffuse(-1, 0)
            elif hit == 'wall-':
                if random.random() > R_WALL: break
                dx, dz = diffuse(1, 0)
            elif hit == 'mask':
                if random.random() < open_frac:
                    z += 1e-6*(1 if dz>0 else -1)        # pass through
                else:
                    if random.random() > R_MASK: break
                    dx, dz = diffuse(0, -1 if dz>0 else 1)  # reflect back to source side
    mean = sum(bins)/NBINS
    if mean == 0: return None
    peak = max(bins); cov = (sum((b-mean)**2 for b in bins)/NBINS)**0.5/mean
    return dict(eff=out/N, peak_mean=peak/mean, cov=cov, bins=bins)

def bar(bins):
    m = max(bins)
    return "\n".join(
        f"   x={(-HALF_W + (i+0.5)*2*HALF_W/NBINS):+5.1f}mm |"
        + "#"*int(40*b/m) for i, b in enumerate(bins))

CONFIGS = [
    ("A0  no mask,      gap15", 19.0, 0,   0.0, 0.0),
    ("A1  dot d14 @5mm, gap15", 19.0, 14,  9.0, 0.43),
    ("A2  dot d16 @5mm, gap15", 19.0, 16,  9.0, 0.43),
    ("A3  dot d14 @6mm, gap18", 22.0, 14, 10.0, 0.43),
    ("A1-solid (opaque dot, for contrast)", 19.0, 14, 9.0, 0.0),
]
print("="*64)
print("2D Monte-Carlo cavity sim  (R_wall=0.92, 120k rays each)")
print("peak/mean: 1.00=flat, higher=hotspot | CoV: lower=more even")
print("="*64)
for name, fz, md, mz, op in CONFIGS:
    r = run(fz, md, mz, op)
    print(f"\n{name}")
    print(f"   efficiency={r['eff']*100:4.1f}%   peak/mean={r['peak_mean']:.2f}   CoV={r['cov']*100:4.1f}%")
    print(bar(r['bins']))
