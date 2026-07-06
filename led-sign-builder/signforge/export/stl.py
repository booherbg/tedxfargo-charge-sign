"""Binary STL read/write + the gated export path (audit before every write)."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from ..solids import mesh_of
from ..verify import gated_mesh


def write_stl(path: str | Path, verts: np.ndarray, tris: np.ndarray) -> None:
    v = np.asarray(verts, dtype=np.float32)
    t = np.asarray(tris, dtype=np.int64)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    lens = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, lens, out=np.zeros_like(n), where=lens > 0)

    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])
    rec["n"] = n
    rec["v"][:, 0], rec["v"][:, 1], rec["v"][:, 2] = p0, p1, p2
    with open(path, "wb") as f:
        f.write(b"signforge".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(t)))
        f.write(rec.tobytes())


def read_stl(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Read binary or ASCII STL into (verts, tris) — verts NOT welded."""
    data = Path(path).read_bytes()
    if data[:5].lower() == b"solid" and b"facet" in data[:400]:
        verts = []
        for line in data.decode(errors="replace").splitlines():
            s = line.split()
            if len(s) == 4 and s[0] == "vertex":
                verts.append([float(s[1]), float(s[2]), float(s[3])])
        v = np.asarray(verts, dtype=np.float64)
    else:
        (ntri,) = struct.unpack_from("<I", data, 80)
        rec = np.frombuffer(
            data,
            dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")],
            count=ntri,
            offset=84,
        )
        v = rec["v"].reshape(-1, 3).astype(np.float64)
    tris = np.arange(len(v), dtype=np.int64).reshape(-1, 3)
    return v, tris


def export_mesh(path: str | Path, man, name: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Manifold -> audit gate (+pinch heal) -> binary STL. Returns export mesh."""
    verts, tris = mesh_of(man)
    verts, tris, notes = gated_mesh(verts, tris, name)
    write_stl(path, verts, tris)
    return verts, tris, notes
