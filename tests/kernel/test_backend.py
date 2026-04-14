import pytest
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


def _volume(shape) -> float:
    """Helper: compute volume of an OCP shape."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def test_backend_protocol_exists():
    from archi.kernel.backend import BackendProtocol
    assert hasattr(BackendProtocol, "make_slab")
    assert hasattr(BackendProtocol, "make_wall")
    assert hasattr(BackendProtocol, "make_opening")
    assert hasattr(BackendProtocol, "boolean_cut")
    assert hasattr(BackendProtocol, "boolean_union")


def test_ocp_backend_isinstance():
    from archi.kernel.backend import BackendProtocol, OCPBackend
    backend = OCPBackend()
    assert isinstance(backend, BackendProtocol)


def test_make_slab_basic():
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    boundary = [
        Vector(0, 0, 0),
        Vector(120, 0, 0),
        Vector(120, 144, 0),
        Vector(0, 144, 0),
    ]
    shape = backend.make_slab(boundary, thickness=6.0)
    assert shape is not None
    vol = _volume(shape)
    expected = 120.0 * 144.0 * 6.0
    assert vol == pytest.approx(expected, rel=0.01)


def test_make_slab_triangle():
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    boundary = [
        Vector(0, 0, 0),
        Vector(100, 0, 0),
        Vector(50, 86.6, 0),
    ]
    shape = backend.make_slab(boundary, thickness=4.0)
    assert shape is not None
    vol = _volume(shape)
    assert vol == pytest.approx(17320.0, rel=0.02)


def test_make_slab_too_few_points():
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    boundary = [Vector(0, 0, 0), Vector(10, 0, 0)]
    with pytest.raises(ValueError, match="at least 3"):
        backend.make_slab(boundary, thickness=4.0)


def test_boolean_union():
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    slab_a = backend.make_slab(
        [Vector(0, 0, 0), Vector(100, 0, 0), Vector(100, 100, 0), Vector(0, 100, 0)],
        thickness=6.0,
    )
    slab_b = backend.make_slab(
        [Vector(50, 0, 0), Vector(150, 0, 0), Vector(150, 100, 0), Vector(50, 100, 0)],
        thickness=6.0,
    )
    fused = backend.boolean_union(slab_a, slab_b)
    assert fused is not None
    vol = _volume(fused)
    assert vol == pytest.approx(90000.0, rel=0.02)


def test_boolean_cut():
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    base = backend.make_slab(
        [Vector(0, 0, 0), Vector(100, 0, 0), Vector(100, 100, 0), Vector(0, 100, 0)],
        thickness=10.0,
    )
    tool = backend.make_slab(
        [Vector(25, 25, 0), Vector(75, 25, 0), Vector(75, 75, 0), Vector(25, 75, 0)],
        thickness=10.0,
    )
    cut = backend.boolean_cut(base, tool)
    assert cut is not None
    vol = _volume(cut)
    assert vol == pytest.approx(75000.0, rel=0.02)


def test_shape_volume_helper():
    from archi.kernel.backend import OCPBackend, shape_volume
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    slab = backend.make_slab(
        [Vector(0, 0, 0), Vector(60, 0, 0), Vector(60, 60, 0), Vector(0, 60, 0)],
        thickness=8.0,
    )
    vol = shape_volume(slab)
    assert vol == pytest.approx(60 * 60 * 8, rel=0.01)


def test_check_valid_helper():
    from archi.kernel.backend import OCPBackend, check_valid
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    slab = backend.make_slab(
        [Vector(0, 0, 0), Vector(60, 0, 0), Vector(60, 60, 0), Vector(0, 60, 0)],
        thickness=8.0,
    )
    result = check_valid(slab)
    assert result["is_valid"] is True
