from signforge.coupons import fit_ladder
from signforge.params import SignParams
from signforge.solids import mesh_of
from signforge.verify import gated_mesh


def test_fit_ladder_bodies_gate_clean():
    bodies, notes = fit_ladder(SignParams(), [0.0, -0.2])
    assert [b.name for b in bodies] == ["shell", "lens"]
    for b in bodies:
        v, t = mesh_of(b.man)
        gated_mesh(v, t, b.name)
    assert "0.0" in notes[0] and "-0.2" in notes[0]


def test_plug_interference_grows_volume():
    loose, _ = fit_ladder(SignParams(), [0.2])
    tight, _ = fit_ladder(SignParams(), [-0.3])
    lens_loose = next(b for b in loose if b.name == "lens").man.volume()
    lens_tight = next(b for b in tight if b.name == "lens").man.volume()
    assert lens_tight > lens_loose


def test_cli_coupon(tmp_path):
    from signforge.cli import main

    rc = main(["coupon", "--values", "0.0,-0.2", "-o", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "fit_ladder_shell.stl").exists()
    assert (tmp_path / "fit_ladder.3mf").exists()
