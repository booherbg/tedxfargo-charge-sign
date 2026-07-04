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
    verts, tris, vmap, cur = [], [], {}, []
    with open(path) as f:
        for line in f:
            s = line.split()
            if len(s) == 4 and s[0] == "vertex":
                key = (s[1], s[2], s[3])
                idx = vmap.get(key)
                if idx is None:
                    idx = len(verts); vmap[key] = idx; verts.append(key)
                cur.append(idx)
                if len(cur) == 3:
                    tris.append(tuple(cur)); cur = []
    audit_manifold(path, tris)
    return verts, tris

def audit_manifold(path, tris):
    """Every edge of a closed manifold mesh is shared by exactly 2 triangles.
    Slicers tolerate small violations, but flag them here so defects are caught
    at build time, not on the printer's machine (learned via fuzz pinch edges)."""
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
        print("WARNING: %s: %d non-manifold edge(s), %d degenerate tri(s)"
              % (path, bad, degen))

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
