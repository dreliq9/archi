import pytest


def test_safe_boolean_cut_succeeds():
    from archi.kernel.isolation import safe_boolean_cut
    from archi.kernel.primitives import make_floor_slab
    from archi.kernel.vector import Vector

    slab = make_floor_slab(
        boundary=[Vector(0, 0, 0), Vector(120, 0, 0), Vector(120, 120, 0), Vector(0, 120, 0)],
        thickness=10.0,
    )
    tool = make_floor_slab(
        boundary=[Vector(30, 30, 0), Vector(90, 30, 0), Vector(90, 90, 0), Vector(30, 90, 0)],
        thickness=10.0,
    )
    assert slab.ok and tool.ok

    result = safe_boolean_cut(slab.shape, tool.shape)
    assert result.ok is True
    assert result.volume == pytest.approx(108000.0, rel=0.05)


def test_safe_boolean_union_succeeds():
    from archi.kernel.isolation import safe_boolean_union
    from archi.kernel.primitives import make_floor_slab
    from archi.kernel.vector import Vector

    a = make_floor_slab(
        boundary=[Vector(0, 0, 0), Vector(100, 0, 0), Vector(100, 100, 0), Vector(0, 100, 0)],
        thickness=5.0,
    )
    b = make_floor_slab(
        boundary=[Vector(50, 0, 0), Vector(150, 0, 0), Vector(150, 100, 0), Vector(50, 100, 0)],
        thickness=5.0,
    )
    assert a.ok and b.ok

    result = safe_boolean_union(a.shape, b.shape)
    assert result.ok is True
    assert result.volume == pytest.approx(75000.0, rel=0.05)


def test_safe_boolean_handles_none_shape():
    from archi.kernel.isolation import safe_boolean_cut
    result = safe_boolean_cut(None, None)
    assert result.ok is False
    assert "shape" in result.diagnostics.get("reason", "").lower()


def test_safe_boolean_returns_build_result():
    from archi.kernel.isolation import safe_boolean_cut
    from archi.kernel.primitives import make_floor_slab
    from archi.kernel.result import BuildResult
    from archi.kernel.vector import Vector

    slab = make_floor_slab(
        boundary=[Vector(0, 0, 0), Vector(100, 0, 0), Vector(100, 100, 0), Vector(0, 100, 0)],
        thickness=5.0,
    )
    tool = make_floor_slab(
        boundary=[Vector(25, 25, 0), Vector(75, 25, 0), Vector(75, 75, 0), Vector(25, 75, 0)],
        thickness=5.0,
    )
    result = safe_boolean_cut(slab.shape, tool.shape)
    assert isinstance(result, BuildResult)
