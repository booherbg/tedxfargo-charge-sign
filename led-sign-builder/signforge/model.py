"""Shared pipeline data types (pure data; geometry logic lives elsewhere)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import manifold3d
    from shapely.geometry import MultiPolygon, Polygon

Point2 = tuple[float, float]


@dataclass
class Stroke:
    """An open or closed centerline polyline; width=None means 'use style width'."""

    pts: list[Point2]
    width: Optional[float] = None
    closed: bool = False

    def length(self) -> float:
        import math

        pts = self.pts + ([self.pts[0]] if self.closed else [])
        return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


@dataclass
class GlyphBox:
    char: str
    fills: "MultiPolygon"
    bbox: tuple[float, float, float, float]


@dataclass
class Artwork:
    """Normalized 2D art in mm: filled regions and/or stroked centerlines."""

    fills: Optional["MultiPolygon"]
    strokes: list[Stroke] = field(default_factory=list)
    glyphs: list[GlyphBox] = field(default_factory=list)
    source: str = ""

    def bbox(self) -> tuple[float, float, float, float]:
        xs: list[float] = []
        ys: list[float] = []
        if self.fills is not None and not self.fills.is_empty:
            b = self.fills.bounds
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        for s in self.strokes:
            xs += [p[0] for p in s.pts]
            ys += [p[1] for p in s.pts]
        if not xs:
            return (0.0, 0.0, 0.0, 0.0)
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class Layout:
    """Artwork placed in sign coordinates, plus the backer footprint."""

    fills: Optional["MultiPolygon"]
    strokes: list[Stroke]
    glyphs: list[GlyphBox]
    backer: Optional["Polygon"]          # tile rect / contour plate / None
    bbox: tuple[float, float, float, float]


@dataclass
class Body:
    """One printable color body of one piece."""

    name: str                            # "shell" | "liner" | "lens"
    man: "manifold3d.Manifold"
    extruder: int
    color: str
    plate: str = "main"                  # co-printed bodies share a plate/3MF


@dataclass
class Piece:
    """One printer-bed-sized region of the sign."""

    name: str
    label: str
    mask: "Polygon"                      # sign-coordinate clip region (viewer space)
    rotated: bool = False                # rotate-to-fit applied at export
    screws: list[Point2] = field(default_factory=list)
    pixel_idx: list[int] = field(default_factory=list)
    clip_mask: Optional["Polygon"] = None  # print-space override (mirrored styles)


@dataclass
class PowerPlan:
    count: int
    watts: float
    amps: float
    psu_watts: int
    strings: int
    budget_px: Optional[int] = None

    @property
    def over_budget(self) -> bool:
        return self.budget_px is not None and self.count > self.budget_px


@dataclass
class LedPlan:
    pixels: list[Point2]
    per_stroke: list[list[int]]
    power: PowerPlan
    audits: list[str] = field(default_factory=list)   # human-readable findings
    snug_pairs: list[tuple[int, int, float]] = field(default_factory=list)
    worst_chord: Optional[float] = None


@dataclass
class BuildResult:
    outdir: str
    files: list[str]
    stats: dict
    warnings: list[str]
    pieces: list[Piece] = field(default_factory=list)
