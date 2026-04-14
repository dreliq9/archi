import pytest


def test_parametric_sofa():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("sofa", width=84.0, depth=36.0, height=34.0)
    assert result.ok
    assert result.volume > 0
    assert "clearance" in result.diagnostics


def test_parametric_bed_queen():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("bed_queen", width=60.0, depth=80.0, height=24.0)
    assert result.ok
    assert result.volume > 0


def test_parametric_dining_table():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("dining_table", width=72.0, depth=36.0, height=30.0)
    assert result.ok
    assert result.diagnostics["clearance"]["front"] == 36.0
    assert result.diagnostics["clearance"]["sides"] == 36.0


def test_parametric_toilet():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("toilet", width=18.0, depth=28.0, height=16.0)
    assert result.ok
    assert result.diagnostics["clearance"]["front"] == 21.0


def test_unknown_type_uses_box():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("unknown_thing", width=24.0, depth=24.0, height=24.0)
    assert result.ok
    assert result.volume > 0


def test_invalid_dimensions():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("sofa", width=0.0, depth=36.0, height=34.0)
    assert not result.ok


def test_default_dimensions():
    from archi.kernel.furniture import FURNITURE_DEFAULTS
    assert "sofa" in FURNITURE_DEFAULTS
    assert "bed_queen" in FURNITURE_DEFAULTS
    d = FURNITURE_DEFAULTS["sofa"]
    assert d["width"] > 0 and d["depth"] > 0 and d["height"] > 0
