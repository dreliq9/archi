import pytest
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


def _volume(shape) -> float:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def test_make_wall_returns_build_result():
    from archi.kernel.primitives import make_wall
    from archi.kernel.result import BuildResult
    from archi.kernel.vector import Vector

    r = make_wall(
        start=Vector(0, 0, 0),
        end=Vector(120, 0, 0),
        height=108.0,
        thickness=5.5,
    )
    assert isinstance(r, BuildResult)
    assert r.ok is True
    assert r.volume is not None
    assert r.volume == pytest.approx(71280.0, rel=0.02)


def test_make_wall_zero_length_fails():
    from archi.kernel.primitives import make_wall
    from archi.kernel.vector import Vector

    r = make_wall(start=Vector(0, 0, 0), end=Vector(0, 0, 0), height=108.0, thickness=5.5)
    assert r.ok is False
    assert "same point" in r.diagnostics.get("reason", "").lower() or \
           "zero" in r.diagnostics.get("reason", "").lower()


def test_make_wall_negative_height_fails():
    from archi.kernel.primitives import make_wall
    from archi.kernel.vector import Vector

    r = make_wall(start=Vector(0, 0, 0), end=Vector(120, 0, 0), height=-10.0, thickness=5.5)
    assert r.ok is False


def test_make_slab_returns_build_result():
    from archi.kernel.primitives import make_floor_slab
    from archi.kernel.result import BuildResult
    from archi.kernel.vector import Vector

    r = make_floor_slab(
        boundary=[Vector(0, 0, 0), Vector(240, 0, 0), Vector(240, 360, 0), Vector(0, 360, 0)],
        thickness=6.0,
    )
    assert isinstance(r, BuildResult)
    assert r.ok is True
    assert r.volume == pytest.approx(518400.0, rel=0.02)


def test_make_floor_slab_too_few_points():
    from archi.kernel.primitives import make_floor_slab
    from archi.kernel.vector import Vector

    r = make_floor_slab(boundary=[Vector(0, 0, 0), Vector(10, 0, 0)], thickness=6.0)
    assert r.ok is False
    assert "3" in r.diagnostics.get("reason", "")


def test_make_opening_in_wall():
    from archi.kernel.primitives import make_opening, make_wall
    from archi.kernel.vector import Vector

    wall = make_wall(start=Vector(0, 0, 0), end=Vector(120, 0, 0), height=108.0, thickness=5.5)
    assert wall.ok

    result = make_opening(wall_result=wall, position=Vector(60, 0, 0), width=36.0, height=80.0)
    assert result.ok is True
    assert result.volume < wall.volume


def test_make_foundation_slab():
    from archi.kernel.primitives import make_foundation_slab
    from archi.kernel.vector import Vector

    r = make_foundation_slab(
        boundary=[Vector(0, 0, 0), Vector(480, 0, 0), Vector(480, 600, 0), Vector(0, 600, 0)],
        thickness=4.0,
        depth=12.0,
    )
    assert r.ok is True
    assert r.shape is not None
    assert r.volume == pytest.approx(1152000.0, rel=0.02)


def test_make_roof_gable():
    from archi.kernel.primitives import make_roof
    from archi.kernel.vector import Vector

    r = make_roof(
        footprint=[Vector(0, 0, 108), Vector(360, 0, 108), Vector(360, 480, 108), Vector(0, 480, 108)],
        profile="gable",
        pitch=6.0,
    )
    assert r.ok is True
    assert r.volume is not None
    assert r.volume > 0


def test_make_stair():
    from archi.kernel.primitives import make_stair
    from archi.kernel.vector import Vector

    r = make_stair(
        start=Vector(0, 0, 0),
        direction=Vector(1, 0, 0),
        run=10.0,
        rise=7.5,
        width=36.0,
        n_steps=14,
    )
    assert r.ok is True
    assert r.volume is not None
    assert r.volume > 0
