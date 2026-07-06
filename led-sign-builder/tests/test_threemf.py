import xml.etree.ElementTree as ET
import zipfile

from signforge.export.threemf import write_3mf
from signforge.geom2d import bbox_polygon, heal
from signforge.solids import mesh_of, prism


def test_bambu_3mf_structure(tmp_path):
    a = prism(heal(bbox_polygon(0, 0, 10, 10)), 0, 2)
    b = prism(heal(bbox_polygon(0, 0, 10, 10)), 1.9, 4)  # co-registered, fused
    parts = [
        ("shell", *mesh_of(a), 1),
        ("lens", *mesh_of(b), 3),
    ]
    path = tmp_path / "piece.3mf"
    write_3mf(path, parts)

    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model",
                "Metadata/model_settings.config"} <= names
        model = ET.fromstring(z.read("3D/3dmodel.model"))
        cfg = ET.fromstring(z.read("Metadata/model_settings.config"))

    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    objects = model.findall(".//m:object", ns)
    assert len(objects) == 3                       # 2 meshes + 1 parent group
    comps = model.findall(".//m:component", ns)
    assert len(comps) == 2

    extruders = [
        md.get("value")
        for part in cfg.findall(".//part")
        for md in part.findall("metadata")
        if md.get("key") == "extruder"
    ]
    assert extruders == ["1", "3"]                 # Bambu filament mapping intact
