#!/usr/bin/env python3
"""Combine N co-registered ASCII STLs into one Bambu Studio MULTI-FILAMENT .3mf.

Usage: make_3mf.py part1.stl [part2.stl ...] out.3mf   (part i -> extruder/filament i)

Writes Bambu's native project format: the part->filament map lives in
Metadata/model_settings.config as <metadata key="extruder" value="N"/> (1-based),
NOT the standard 3MF <basematerials> (which Bambu ignores for filament assignment).
Each mesh is its own <object>, grouped under a parent <object> via <components> so
it loads as ONE object with two parts:
    part 1 (white body)  -> filament/extruder 1
    part 2 (clear optic) -> filament/extruder 2
Swatch colors come from the two filaments loaded in your Bambu project (set slot 1
= white, slot 2 = clear). Format verified vs BambuStudio src/libslic3r/Format/bbs_3mf.cpp.
"""
import os, sys, zipfile

def parse_stl(path):
    """Read an ASCII STL and build an edge-manifold indexed mesh.

    Vertices are welded through GLUED EDGES, not by raw position: each directed
    edge side is paired with exactly one opposite-orientation side at the same
    position. Where a position-edge has >2 sides (two solids of a CGAL union
    touching along a line, e.g. V8 facet-field tangencies), the extra pair keeps
    its own duplicate vertices — the sheets separate topologically while every
    written coordinate stays identical, so the sliced result is unchanged but
    Bambu's non-manifold-edge check passes."""
    corners, cur = [], []          # position strings, 3 per triangle
    with open(path) as f:
        for line in f:
            s = line.split()
            if len(s) == 4 and s[0] == "vertex":
                cur.append((s[1], s[2], s[3]))
                if len(cur) == 3:
                    if cur[0] != cur[1] and cur[1] != cur[2] and cur[0] != cur[2]:
                        corners.extend(cur)          # drop degenerate tris
                    cur = []
    ntri = len(corners) // 3

    parent = list(range(len(corners)))               # union-find over corners
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra

    from collections import defaultdict
    sides = defaultdict(list)                        # pos-edge -> [(corner_u, corner_v)]
    for t in range(ntri):
        for s in range(3):
            cu, cv = 3 * t + s, 3 * t + (s + 1) % 3
            u, v = corners[cu], corners[cv]
            side = (cu, cv) if u < v else (cv, cu)   # corners in key order
            sides[min(u, v), max(u, v)].append(side)
    # Weld only through clean 2-side edges. Pinch edges (>2 sides: one self-tangent
    # CGAL surface crossing itself along a line) get NO welds — each wing's corners
    # then unify around the vertex umbrellas via its own sheet's clean edges, so the
    # sheets come out with separate indices at the seam and every edge ends up 2-sided.
    pinch_edges = []
    for key, ss in sides.items():
        if len(ss) == 2:
            union(ss[0][0], ss[1][0]); union(ss[0][1], ss[1][1])
        elif len(ss) > 2:
            pinch_edges.append(ss)
    if pinch_edges:
        # Pair the wings sheet-by-sheet: two sides belong to the same sheet iff
        # their corners already share a class at one endpoint (welded around the
        # seam-endpoint umbrellas). Weld the paired sides' other corners, and
        # iterate so the pairing propagates inward along pinch CHAINS (a chain-
        # interior vertex has no umbrella path that avoids the seam).
        changed = True
        while changed:
            changed = False
            for ss in pinch_edges:
                for slot in (0, 1):
                    groups = defaultdict(list)
                    for side in ss:
                        groups[find(side[slot])].append(side)
                    for g in groups.values():
                        if len(g) == 2:
                            oa, ob = g[0][1 - slot], g[1][1 - slot]
                            if find(oa) != find(ob):
                                union(oa, ob); changed = True
        print("healed %s: %d pinch edge(s) fan-split (geometry unchanged)"
              % (os.path.basename(path), len(pinch_edges)))

    verts, vid, tris = [], {}, []
    for t in range(ntri):
        idx = []
        for s in range(3):
            r = find(3 * t + s)
            i = vid.get(r)
            if i is None:
                i = len(verts); vid[r] = i; verts.append(corners[3 * t + s])
            idx.append(i)
        tris.append(tuple(idx))
    audit_manifold(path, tris)
    return verts, tris

def audit_manifold(path, tris):
    """Every edge of a closed manifold mesh is shared by exactly 2 triangles.
    Hard gate: a violation here is exactly what Bambu will flag on the object
    (learned via fuzz pinch edges — and warn-only let V8 facet pinches ship)."""
    from collections import Counter
    edges, degen = Counter(), 0
    for a, b, c in tris:
        if a == b or b == c or a == c:
            degen += 1
            continue
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
    bad = sum(1 for n in edges.values() if n != 2)
    if bad or degen:
        raise SystemExit("FAIL: %s: %d non-manifold edge(s), %d degenerate tri(s) "
                         "after heal — fix the geometry, do not ship" % (path, bad, degen))

def mesh_xml(verts, tris):
    v = "".join('<vertex x="%s" y="%s" z="%s"/>' % t for t in verts)
    t = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tr for tr in tris)
    return "<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh>" % (v, t)

CT = ('<?xml version="1.0" encoding="UTF-8"?>\n'
 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
 '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
 '<Default Extension="png" ContentType="image/png"/>'
 '<Default Extension="gcode" ContentType="text/x.gcode"/>'
 '</Types>')

RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
 '<Relationship Target="/3D/3dmodel.model" Id="rel-1" '
 'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
 '</Relationships>')

ID12 = "1 0 0 0 1 0 0 0 1 0 0 0"            # 3dmodel transform (12, column-major)
ID16 = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"    # config matrix (16, row-major)

def main():
    stls, out = sys.argv[1:-1], sys.argv[-1]   # N part STLs (extruder 1..N) + out.3mf
    meshes = [parse_stl(p) for p in stls]
    names = [os.path.splitext(os.path.basename(p))[0] for p in stls]
    gid = len(stls) + 1                        # parent/group object id

    objs = "".join('<object id="%d" type="model">%s</object>\n' % (i + 1, mesh_xml(v, t))
                   for i, (v, t) in enumerate(meshes))
    comps = "".join('<component objectid="%d" transform="%s"/>' % (i + 1, ID12)
                    for i in range(len(meshes)))
    model = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<model unit="millimeter" xml:lang="en-US" '
      'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n'
      '<metadata name="Application">BambuStudio-02.00.00.00</metadata>\n'
      '<metadata name="BambuStudio:3mfVersion">1</metadata>\n'
      '<resources>\n'
      '%s'
      '<object id="%d" type="model"><components>%s</components></object>\n'
      '</resources>\n'
      '<build><item objectid="%d" transform="%s" printable="1"/></build>\n'
      '</model>\n'
    ) % (objs, gid, comps, gid, ID12)

    parts = "".join(
      '    <part id="%d" subtype="normal_part">\n'
      '      <metadata key="name" value="%s"/>\n'
      '      <metadata key="matrix" value="%s"/>\n'
      '      <metadata key="extruder" value="%d"/>\n'
      '    </part>\n' % (i + 1, names[i], ID16, i + 1) for i in range(len(meshes)))
    cfg = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<config>\n'
      '  <object id="%d">\n'
      '    <metadata key="name" value="%s"/>\n'
      '    <metadata key="extruder" value="1"/>\n'
      '%s'
      '  </object>\n'
      '</config>\n'
    ) % (gid, os.path.splitext(os.path.basename(out))[0], parts)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", cfg)
    print("wrote %s  (%s)" % (out, ", ".join(
        "%s: %d tris -> extruder %d" % (names[i], len(meshes[i][1]), i + 1)
        for i in range(len(meshes)))))

if __name__ == "__main__":
    main()
