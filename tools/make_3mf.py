#!/usr/bin/env python3
"""Combine two co-registered ASCII STLs into one Bambu Studio TWO-FILAMENT .3mf.

Usage: make_3mf.py white.stl clear.stl out.3mf

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
import sys, zipfile

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
    return verts, tris

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
    white_stl, clear_stl, out = sys.argv[1], sys.argv[2], sys.argv[3]
    wv, wt = parse_stl(white_stl)
    cv, ct = parse_stl(clear_stl)

    model = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<model unit="millimeter" xml:lang="en-US" '
      'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n'
      '<metadata name="Application">BambuStudio-02.00.00.00</metadata>\n'
      '<metadata name="BambuStudio:3mfVersion">1</metadata>\n'
      '<resources>\n'
      '<object id="1" type="model">%s</object>\n'
      '<object id="2" type="model">%s</object>\n'
      '<object id="3" type="model"><components>'
      '<component objectid="1" transform="%s"/>'
      '<component objectid="2" transform="%s"/>'
      '</components></object>\n'
      '</resources>\n'
      '<build><item objectid="3" transform="%s" printable="1"/></build>\n'
      '</model>\n'
    ) % (mesh_xml(wv, wt), mesh_xml(cv, ct), ID12, ID12, ID12)

    cfg = (
      '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<config>\n'
      '  <object id="3">\n'
      '    <metadata key="name" value="lens_matrix"/>\n'
      '    <metadata key="extruder" value="1"/>\n'
      '    <part id="1" subtype="normal_part">\n'
      '      <metadata key="name" value="white_body"/>\n'
      '      <metadata key="matrix" value="%s"/>\n'
      '      <metadata key="extruder" value="1"/>\n'
      '    </part>\n'
      '    <part id="2" subtype="normal_part">\n'
      '      <metadata key="name" value="clear_optic"/>\n'
      '      <metadata key="matrix" value="%s"/>\n'
      '      <metadata key="extruder" value="2"/>\n'
      '    </part>\n'
      '  </object>\n'
      '</config>\n'
    ) % (ID16, ID16)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", cfg)
    print("wrote %s  (white: %d tris -> extruder 1, clear: %d tris -> extruder 2)"
          % (out, len(wt), len(ct)))

if __name__ == "__main__":
    main()
