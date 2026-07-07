"""Regressions from the example-art visual sweep (docs/gallery/examples)."""

from pathlib import Path

import pytest

from signforge.ingest.art import art_to_artwork
from signforge.layout import build_layout
from signforge.params import SignParams
from signforge.tubes import plan_tubes

ART = Path(__file__).parent.parent / "examples" / "art"


def _plan(name, **style):
    p = SignParams.model_validate(
        {"style": {"kind": "neon", **style}, "texture": {"mode": "none"}}
    )
    art = art_to_artwork(str(ART / f"{name}.svg"), 200)
    lay = build_layout(art, p)
    return plan_tubes(lay, p)


def test_atom_three_distinct_orbits_plus_nucleus():
    """SVG transform baking: rotated ellipses must differ (abs() fix)."""
    strokes, lay, meta, warns = _plan("atom")
    closed = [s for s in strokes if s.closed]
    assert len(closed) >= 4                      # 3 orbits + nucleus ring
    boxes = set()
    for s in closed:
        xs = [p[0] for p in s.pts]
        ys = [p[1] for p in s.pts]
        boxes.add((round(max(xs) - min(xs), -1), round(max(ys) - min(ys), -1)))
    assert len(boxes) >= 3                       # orbits are NOT copies


def test_martini_mixed_art_keeps_the_olive():
    strokes, lay, meta, warns = _plan("martini")
    assert "strokes" in meta["source"]           # drawn tubes kept
    assert any(s.closed for s in strokes)        # the olive ring survived


def test_coffee_handle_spine_fallback():
    strokes, lay, meta, warns = _plan("coffee")
    assert meta["source"].startswith("outline")
    assert any("spine" in w or "thinner than" in w for w in warns)
    assert len(strokes) >= 4                     # cup ring + handle + 2 steam


def test_boomerang_builds_as_outline():
    """Was a hard failure (blob skeleton fully pruned) before outline mode."""
    strokes, lay, meta, warns = _plan("boomerang")
    assert strokes and meta["source"].startswith("outline")


def test_skeleton_mode_still_available():
    strokes, lay, meta, warns = _plan("bowling", neon={"source": "skeleton"})
    assert meta["source"].startswith("skeleton")


@pytest.mark.slow
@pytest.mark.parametrize("name", [p.stem for p in sorted(ART.glob("*.svg"))])
def test_every_example_art_builds(name, tmp_path):
    from signforge.pipeline import build

    p = SignParams.model_validate(
        {
            "name": name,
            "content": {"mode": "art", "art_path": str(ART / f"{name}.svg"),
                        "art_target_height_mm": 200},
            "texture": {"mode": "none"},
        }
    )
    r = build(p, tmp_path / name)
    assert r.stats["total_grams_petg"] > 1
