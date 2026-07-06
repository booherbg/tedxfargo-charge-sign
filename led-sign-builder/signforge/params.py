"""Parameter schema — the whole customization surface, CHARGE-validated defaults.

Every numeric default here has provenance in docs/LESSONS-FROM-CHARGE.md §C
(printed tests). Change defaults only with new evidence; users can override
anything per-build via params.json / the web UI.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = 1

# Effective printable envelope (x, y) in mm. For multi-material machines this
# is the multi-tool zone, not the sheet size (lesson 21: the real bed is
# smaller than the bed; H2D value was validated with a physical bedcheck part).
PRINTER_PRESETS: dict[str, tuple[float, float]] = {
    "bambu-h2d-dual": (316.0, 295.0),
    "bambu-x1c": (256.0, 256.0),
    "bambu-a1": (256.0, 256.0),
    "bambu-a1-mini": (180.0, 180.0),
    "prusa-mk4": (250.0, 210.0),
    "ender-3": (220.0, 220.0),
}


class ContentParams(BaseModel):
    mode: Literal["text", "art"] = "text"
    text: str = "GLOW"
    font_path: Optional[str] = None          # None -> bundled default
    cap_height_mm: float = Field(250.0, gt=10, le=2000)
    letter_spacing_mm: float = 0.0           # extra tracking on top of metrics
    line_spacing: float = 1.2                # multiple of cap height
    align: Literal["left", "center", "right"] = "center"
    art_path: Optional[str] = None
    art_target_height_mm: float = Field(250.0, gt=10, le=2000)
    trace_threshold: int = Field(128, ge=1, le=254)   # raster ingest ink cutoff
    trace_invert: bool = False

    @model_validator(mode="after")
    def _art_needs_path(self) -> "ContentParams":
        if self.mode == "art" and not self.art_path:
            raise ValueError("content.mode='art' requires content.art_path")
        return self


class NeonSection(BaseModel):
    """Faux-neon tube cross-section (CHARGE production values)."""

    channel_interior: float = Field(18.0, gt=4)   # fits Ø12 pixel + collar
    liner_wall: float = Field(0.8, gt=0)          # white reflector wall
    outer_wall: float = Field(1.2, gt=0)          # black structural wall
    plate_t: float = Field(2.0, gt=0)             # rear plate (== collar height)
    liner_floor_t: float = Field(0.4, gt=0)       # white floor lining
    wall_height: float = Field(19.0, gt=2)        # dome_clear 4 + air gap 15
    lens_t: float = Field(1.2, gt=0.3)
    # coverage QA severity: None = auto (strict for text/glyphs — the
    # A-amputation class; warn for arbitrary shapes, where skeleton neon is an
    # interpretation and sharp wedge tips always lose a little area)
    coverage_strict: Optional[bool] = None

    @property
    def band_outer(self) -> float:
        return self.channel_interior + 2 * (self.liner_wall + self.outer_wall)


class ChannelSection(BaseModel):
    """Classic filled channel letter."""

    plate_t: float = Field(2.4, gt=0)
    wall_t: float = Field(1.6, gt=0)
    wall_height: float = Field(30.0, gt=2)
    lens_t: float = Field(1.5, gt=0.3)
    lip_depth: float = Field(3.0, ge=0)
    lip_clear: float = -0.2       # interference; positive clearances fall out (lesson 1)
    counter_mode: Literal["glow", "open"] = "glow"


class StyleParams(BaseModel):
    kind: Literal["neon", "channel"] = "neon"
    backer: Literal["tile", "contour", "none"] = "tile"
    tile_margin_mm: float = Field(12.0, ge=0)
    contour_margin_mm: float = Field(8.0, ge=0)
    screw_holes: bool = True                      # anti-lift + mounting (Ø4.5 rail screws)
    screw_d_mm: float = Field(4.5, gt=0)
    screw_inset_mm: float = Field(12.0, gt=0)
    screw_midspan_mm: float = Field(160.0, gt=0)  # add mid-span screws past this
    neon: NeonSection = NeonSection()
    channel: ChannelSection = ChannelSection()


class LedParams(BaseModel):
    kind: Literal["bullet12", "none"] = "bullet12"
    pitch_mm: float = Field(17.0, gt=5)           # solid-tube glow (lesson: 8" native = sparse)
    min_chord_mm: float = Field(14.8, gt=1)       # chord-measured, not arc (lesson 18)
    flange_floor_mm: float = Field(14.5, gt=1)    # flange Ø13.6 + margin
    seam_keepout_mm: float = Field(12.5, ge=0)    # no collar straddles a joint
    bore_mm: float = Field(12.3, gt=1)            # plate through-hole (barrel Ø12.19)
    collar: bool = True
    collar_od_mm: float = Field(16.0, gt=1)
    collar_h_mm: float = Field(2.0, gt=0.2)
    dome_clear_mm: float = Field(4.0, ge=0)
    volts: float = Field(24.0, gt=0)
    watts_per_px: float = Field(0.25, gt=0)
    psu_headroom: float = Field(0.8, gt=0.1, le=1.0)   # cap PSUs at ~80%
    budget_px: Optional[int] = Field(None, ge=1)       # hard inventory cap (lesson 19)
    grid_pitch_mm: float = Field(40.0, gt=5)           # channel-style area fill


class TextureParams(BaseModel):
    mode: Literal["none", "random", "pyramid", "pyramid_jitter"] = "pyramid_jitter"
    cell_mm: float = Field(2.0, gt=0.2)     # V8 winner
    height_mm: float = Field(0.6, gt=0.02)
    seed: int = 7
    standoff_mm: float = Field(0.02, gt=0)  # never kiss the lens plane (lesson 9)
    sample_div: int = Field(3, ge=2, le=8)  # cell/3; S=4 doubled mesh for nothing


class FitParams(BaseModel):
    seam_clearance_mm: float = Field(0.06, ge=0)   # per face (0.12/joint)
    fuse_mm: float = Field(0.1, gt=0)              # weld overlap between stacked bodies
    min_feature_mm: float = Field(0.8, gt=0)       # 2 extrusion widths


class PrinterParams(BaseModel):
    preset: str = "bambu-h2d-dual"
    bed_x_mm: Optional[float] = Field(None, gt=50)
    bed_y_mm: Optional[float] = Field(None, gt=50)

    @model_validator(mode="after")
    def _known_preset(self) -> "PrinterParams":
        if self.preset not in PRINTER_PRESETS and not (self.bed_x_mm and self.bed_y_mm):
            raise ValueError(
                f"unknown printer preset {self.preset!r}; known: {sorted(PRINTER_PRESETS)} "
                "(or set bed_x_mm/bed_y_mm)"
            )
        return self

    @property
    def bed(self) -> tuple[float, float]:
        if self.bed_x_mm and self.bed_y_mm:
            return (self.bed_x_mm, self.bed_y_mm)
        return PRINTER_PRESETS[self.preset]


class ColorParams(BaseModel):
    # body name -> 1-based extruder/filament slot (Bambu semantics, lesson 20)
    extruders: dict[str, int] = {"shell": 1, "liner": 2, "lens": 3}
    preview: dict[str, str] = {
        "shell": "#141414",
        "liner": "#f2f2f2",
        "lens": "#7ec8ff",
        "pixel": "#ffd24d",
        "seam": "#ff5470",
    }


class OutputParams(BaseModel):
    stl: bool = True
    threemf: bool = True
    preview: bool = True
    bom: bool = True
    debug_overlays: bool = True   # always eyeball it (lesson 14)


class SignParams(BaseModel):
    schema_version: int = SCHEMA_VERSION
    name: str = "sign"
    content: ContentParams = ContentParams()
    style: StyleParams = StyleParams()
    leds: LedParams = LedParams()
    texture: TextureParams = TextureParams()
    fit: FitParams = FitParams()
    printer: PrinterParams = PrinterParams()
    colors: ColorParams = ColorParams()
    output: OutputParams = OutputParams()

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> "SignParams":
        return cls.model_validate_json(text)


def preset_params(name: str) -> SignParams:
    if name not in PRESET_PARAMS:
        raise KeyError(f"unknown preset {name!r}; known: {sorted(PRESET_PARAMS)}")
    return SignParams.model_validate(PRESET_PARAMS[name])


PRESET_PARAMS: dict[str, dict] = {
    # The CHARGE look: tube sign, jittered facet lens, bullet pixels.
    "neon-classic": {
        "name": "neon-classic",
        "style": {"kind": "neon", "backer": "tile"},
    },
    # Filled letters, face-lit, no pixel grid by default (strip/none wiring).
    "channel-bold": {
        "name": "channel-bold",
        "style": {"kind": "channel", "backer": "none"},
        "texture": {"mode": "random", "cell_mm": 1.5, "height_mm": 0.8},
    },
    # Desk-sized demo that prints on small beds fast.
    "mini-desk": {
        "name": "mini-desk",
        "content": {"cap_height_mm": 60.0},
        "style": {"kind": "neon", "backer": "contour"},
        "leds": {"kind": "none"},
        "printer": {"preset": "bambu-a1-mini"},
    },
}
