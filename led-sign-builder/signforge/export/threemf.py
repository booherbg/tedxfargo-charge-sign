"""Bambu Studio multi-filament 3MF writer (port of CHARGE tools/make_3mf.py).

Bambu ignores standard 3MF <basematerials> for filament assignment: the
part->filament map lives in Metadata/model_settings.config as
<metadata key="extruder" value="N"/> (1-based). Meshes are co-registered
sibling <object>s grouped under a parent via <components>, so the file loads
as ONE object with N parts. Verified against BambuStudio bbs_3mf.cpp by the
CHARGE project. Load with File→Import (Open resets project settings).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np

CT = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Default Extension="gcode" ContentType="text/x.gcode"/>'
    "</Types>"
)

RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel-1" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    "</Relationships>"
)

ID12 = "1 0 0 0 1 0 0 0 1 0 0 0"            # 3dmodel transform (12, column-major)
ID16 = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"    # config matrix (16, row-major)


def _mesh_xml(verts: np.ndarray, tris: np.ndarray) -> str:
    v = "".join(
        '<vertex x="%s" y="%s" z="%s"/>' % ("%.6g" % p[0], "%.6g" % p[1], "%.6g" % p[2])
        for p in verts
    )
    t = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(tr) for tr in tris)
    return "<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh>" % (v, t)


def write_3mf(
    path: str | Path, parts: list[tuple[str, np.ndarray, np.ndarray, int]]
) -> None:
    """parts: [(name, verts, tris, extruder_1based), ...] — co-registered,
    already gated (verify.gated_mesh) upstream."""
    if not parts:
        raise ValueError("write_3mf: no parts")
    gid = len(parts) + 1

    objs = "".join(
        '<object id="%d" type="model">%s</object>\n' % (i + 1, _mesh_xml(v, t))
        for i, (_, v, t, _e) in enumerate(parts)
    )
    comps = "".join(
        '<component objectid="%d" transform="%s"/>' % (i + 1, ID12)
        for i in range(len(parts))
    )
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n'
        "<metadata name=\"Application\">BambuStudio-02.00.00.00</metadata>\n"
        "<metadata name=\"BambuStudio:3mfVersion\">1</metadata>\n"
        "<resources>\n%s"
        '<object id="%d" type="model"><components>%s</components></object>\n'
        "</resources>\n"
        '<build><item objectid="%d" transform="%s" printable="1"/></build>\n'
        "</model>\n"
    ) % (objs, gid, comps, gid, ID12)

    cfg_parts = "".join(
        '    <part id="%d" subtype="normal_part">\n'
        '      <metadata key="name" value="%s"/>\n'
        '      <metadata key="matrix" value="%s"/>\n'
        '      <metadata key="extruder" value="%d"/>\n'
        "    </part>\n" % (i + 1, name, ID16, extruder)
        for i, (name, _v, _t, extruder) in enumerate(parts)
    )
    cfg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<config>\n"
        '  <object id="%d">\n'
        '    <metadata key="name" value="%s"/>\n'
        '    <metadata key="extruder" value="1"/>\n'
        "%s"
        "  </object>\n"
        "</config>\n"
    ) % (gid, Path(path).stem, cfg_parts)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", cfg)
