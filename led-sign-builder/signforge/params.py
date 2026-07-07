"""Parameter schema — the whole customization surface, CHARGE-validated defaults.

Every numeric default here has provenance in docs/LESSONS-FROM-CHARGE.md §C
(printed tests). Change defaults only with new evidence; users can override
anything per-build via params.json / the web UI.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = 1

# Effective printable envelope (x, y) in mm plus bridging capability. The
# envelope is the multi-tool zone, not the sheet size (lesson 21: the real bed
# is smaller than the bed; H2D value was validated with a physical bedcheck
# part). "weak" bridging auto-enables internal support ribs in neon channels.
PRINTER_PRESETS: dict[str, dict] = {
    "bambu-h2d-dual": {"bed": (316.0, 295.0), "bridging": "good"},
    "bambu-x1c": {"bed": (256.0, 256.0), "bridging": "good"},
    "bambu-a1": {"bed": (256.0, 256.0), "bridging": "good"},
    "bambu-a1-mini": {"bed": (180.0, 180.0), "bridging": "weak"},
    "prusa-mk4": {"bed": (250.0, 210.0), "bridging": "good"},
    "ender-3": {"bed": (220.0, 220.0), "bridging": "weak"},
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

    # where tube centerlines come from for FILLED art:
    #   auto     → letters use skeletons; shape art traces the OUTLINE
    #   skeleton → medial-axis spine (the letterform treatment)
    #   outline  → silhouette tube inset half a band (the neon-shop treatment
    #              for blobs: pins, bolts, mascots)
    source: Literal["auto", "skeleton", "outline"] = "auto"
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


class HaloSection(BaseModel):
    """Halo/backlit letters: opaque face, LEDs fire backward at the wall."""

    face_t: float = Field(2.4, gt=0)
    wall_t: float = Field(1.6, gt=0)
    depth: float = Field(35.0, gt=5)            # face -> wall plane (halo throw)
    flange_w: float = Field(16.0, gt=6)         # rear ring carrying the pixels
    flange_t: float = Field(2.0, gt=0.5)        # == collar height (flush seat)
    back_mode: Literal["open", "diffuser"] = "open"
    diffuser_t: float = Field(1.5, gt=0.3)
    standoff_d: float = Field(10.0, gt=3)       # wall-standoff boss diameter
    standoff_len: float = Field(12.0, ge=0)     # boss height past the flange
    standoff_bore: float = Field(4.2, gt=0.5)   # M4 clearance


class StyleParams(BaseModel):
    kind: Literal["neon", "channel", "halo"] = "neon"
    backer: Literal["tile", "contour", "none"] = "tile"
    backer_shape: Literal["rect", "rounded", "oval", "shield", "starburst", "scallop"] = "rect"
    plaque_corner_radius_mm: float = Field(12.0, gt=0)
    plaque_rays: int = Field(16, ge=8, le=48)
    tile_margin_mm: float = Field(12.0, ge=0)
    contour_margin_mm: float = Field(8.0, ge=0)
    # internal support ribs for weak-bridging printers: thin white ribs from
    # channel floor to lens underside — PERMANENT (removable supports inside a
    # sealed cavity are unprintable; CHARGE optics-matrix lesson)
    support_ribs: Literal["auto", "on", "off"] = "auto"
    rib_spacing_mm: float = Field(28.0, gt=8)
    rib_t_mm: float = Field(0.9, gt=0.3)
    screw_holes: bool = True                      # anti-lift + mounting (Ø4.5 rail screws)
    screw_d_mm: float = Field(4.5, gt=0)
    screw_inset_mm: float = Field(12.0, gt=0)
    screw_midspan_mm: float = Field(160.0, gt=0)  # add mid-span screws past this
    neon: NeonSection = NeonSection()
    channel: ChannelSection = ChannelSection()
    halo: HaloSection = HaloSection()


class LedParams(BaseModel):
    kind: Literal["bullet12", "strip", "none"] = "bullet12"
    watts_per_m: float = Field(14.4, gt=0)        # strip mode (60/m 5050 class)
    pitch_mm: float = Field(17.0, ge=13.0)        # flange floor is 13 — tighter is physically impossible
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
    # which surfaces get the fuzzy layer: the lens top, the visible backer
    # field around the tubes/letters, or both
    targets: list[Literal["lens", "backer"]] = ["lens"]
    cell_mm: float = Field(2.0, gt=0.2)     # V8 winner
    height_mm: float = Field(0.6, gt=0.02)
    backer_cell_mm: float = Field(3.0, gt=0.2)   # coarser field texture reads better
    backer_height_mm: float = Field(0.5, gt=0.02)
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
        return PRINTER_PRESETS[self.preset]["bed"]

    @property
    def bridging(self) -> str:
        if self.preset in PRINTER_PRESETS:
            return PRINTER_PRESETS[self.preset]["bridging"]
        return "good"


PALETTES: dict[str, dict[str, str]] = {
    "charge-classic": {"shell": "#141414", "liner": "#f2f2f2", "lens": "#7ec8ff",
                       "pixel": "#ffd24d", "seam": "#ff5470"},
    "porcelain-diner": {"shell": "#f2ebdc", "liner": "#ffffff", "lens": "#7fd4c1",
                        "pixel": "#ffd24d", "seam": "#c24e33"},
    "gas-station": {"shell": "#26221b", "liner": "#f2f2f2", "lens": "#ff5a4e",
                    "pixel": "#ffd24d", "seam": "#7fa3a1"},
    "atomic-lounge": {"shell": "#2e5f5c", "liner": "#f2ebdc", "lens": "#e8b33c",
                      "pixel": "#fff1c9", "seam": "#c24e33"},
    "bakelite-brass": {"shell": "#3b3630", "liner": "#ede4d3", "lens": "#c99b3f",
                       "pixel": "#ffe9b0", "seam": "#7fa3a1"},
}


class ColorParams(BaseModel):
    # body name -> 1-based extruder/filament slot (Bambu semantics, lesson 20)
    extruders: dict[str, int] = {"shell": 1, "liner": 2, "lens": 3}
    palette: Optional[str] = None            # named palette applies to preview
    preview: dict[str, str] = dict(PALETTES["charge-classic"])

    @model_validator(mode="after")
    def _apply_palette(self) -> "ColorParams":
        if self.palette:
            if self.palette not in PALETTES:
                raise ValueError(f"unknown palette {self.palette!r}; known: {sorted(PALETTES)}")
            self.preview = dict(PALETTES[self.palette])   # named palette wins
        return self


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
    # Wall-glow letters: opaque face, backward-firing pixels, standoffs.
    "halo-backlit": {
        "name": "halo-backlit",
        "style": {"kind": "halo", "backer": "none"},
        "texture": {"mode": "none"},
    },
}
