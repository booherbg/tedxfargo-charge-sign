from signforge.ingest.fonts import text_to_artwork


def test_hello_glyphs_and_counters(bungee):
    art = text_to_artwork(bungee, "HELLO", cap_height_mm=100)
    assert [g.char for g in art.glyphs] == list("HELLO")
    o_glyph = art.glyphs[-1]
    assert any(len(p.interiors) >= 1 for p in o_glyph.fills.geoms)  # 'O' counter
    assert art.fills is not None and art.fills.area > 0


def test_cap_height_scaling(bungee):
    art = text_to_artwork(bungee, "H", cap_height_mm=100)
    _, y0, _, y1 = art.glyphs[0].bbox
    assert abs((y1 - y0) - 100) < 5.0


def test_multiline_and_center_align(bungee):
    one = text_to_artwork(bungee, "HI", cap_height_mm=50)
    two = text_to_artwork(bungee, "HI\nWIDER", cap_height_mm=50, align="center")
    _, sy0, _, sy1 = one.bbox()
    _, ty0, _, ty1 = two.bbox()
    assert (ty1 - ty0) > (sy1 - sy0) * 1.8   # second line stacked below
    hi_line = two.glyphs[:2]        # glyph order is line-by-line
    wider_line = two.glyphs[2:]
    hi_cx = (min(g.bbox[0] for g in hi_line) + max(g.bbox[2] for g in hi_line)) / 2
    wd_cx = (min(g.bbox[0] for g in wider_line) + max(g.bbox[2] for g in wider_line)) / 2
    assert abs(hi_cx - wd_cx) < 2.0          # centered on each other


def test_letter_spacing_widens(bungee):
    tight = text_to_artwork(bungee, "AB", cap_height_mm=50)
    loose = text_to_artwork(bungee, "AB", cap_height_mm=50, letter_spacing_mm=10)
    tw = tight.bbox()[2] - tight.bbox()[0]
    lw = loose.bbox()[2] - loose.bbox()[0]
    assert abs((lw - tw) - 10) < 1.0


def test_script_font_overlaps_weld(pacifico):
    art = text_to_artwork(pacifico, "el", cap_height_mm=60)
    assert art.fills is not None and art.fills.is_valid


def test_space_and_missing_glyphs(bungee):
    art = text_to_artwork(bungee, "A B", cap_height_mm=50)
    assert len(art.glyphs) == 2
    gap = art.glyphs[1].bbox[0] - art.glyphs[0].bbox[2]
    assert gap > 5   # space produced a real gap
