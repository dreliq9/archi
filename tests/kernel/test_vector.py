import math
import pytest


def test_vector_create():
    from archi.kernel.vector import Vector
    v = Vector(1.0, 2.0, 3.0)
    assert v.x == 1.0
    assert v.y == 2.0
    assert v.z == 3.0


def test_vector_add():
    from archi.kernel.vector import Vector
    a = Vector(1, 2, 3)
    b = Vector(4, 5, 6)
    c = a + b
    assert c.x == 5
    assert c.y == 7
    assert c.z == 9


def test_vector_sub():
    from archi.kernel.vector import Vector
    a = Vector(4, 5, 6)
    b = Vector(1, 2, 3)
    c = a - b
    assert c.x == 3
    assert c.y == 3
    assert c.z == 3


def test_vector_mul_scalar():
    from archi.kernel.vector import Vector
    v = Vector(1, 2, 3)
    r = v * 2
    assert r.x == 2
    assert r.y == 4
    assert r.z == 6


def test_vector_neg():
    from archi.kernel.vector import Vector
    v = Vector(1, -2, 3)
    n = -v
    assert n.x == -1
    assert n.y == 2
    assert n.z == -3


def test_vector_length():
    from archi.kernel.vector import Vector
    v = Vector(3, 4, 0)
    assert v.length == pytest.approx(5.0)


def test_vector_normalized():
    from archi.kernel.vector import Vector
    v = Vector(0, 0, 5)
    n = v.normalized()
    assert n.x == pytest.approx(0.0)
    assert n.y == pytest.approx(0.0)
    assert n.z == pytest.approx(1.0)


def test_vector_normalized_zero_raises():
    from archi.kernel.vector import Vector
    v = Vector(0, 0, 0)
    with pytest.raises(ValueError, match="zero-length"):
        v.normalized()


def test_vector_dot():
    from archi.kernel.vector import Vector
    a = Vector(1, 0, 0)
    b = Vector(0, 1, 0)
    assert a.dot(b) == pytest.approx(0.0)
    c = Vector(1, 2, 3)
    d = Vector(4, 5, 6)
    assert c.dot(d) == pytest.approx(32.0)


def test_vector_cross():
    from archi.kernel.vector import Vector
    a = Vector(1, 0, 0)
    b = Vector(0, 1, 0)
    c = a.cross(b)
    assert c.x == pytest.approx(0.0)
    assert c.y == pytest.approx(0.0)
    assert c.z == pytest.approx(1.0)


def test_vector_angle():
    from archi.kernel.vector import Vector
    a = Vector(1, 0, 0)
    b = Vector(0, 1, 0)
    assert a.angle(b) == pytest.approx(math.pi / 2)


def test_vector_eq():
    from archi.kernel.vector import Vector
    a = Vector(1, 2, 3)
    b = Vector(1, 2, 3)
    c = Vector(1, 2, 4)
    assert a == b
    assert a != c


def test_vector_to_pnt():
    from archi.kernel.vector import Vector
    from OCP.gp import gp_Pnt
    v = Vector(10, 20, 30)
    pnt = v.to_pnt()
    assert isinstance(pnt, gp_Pnt)
    assert pnt.X() == pytest.approx(10.0)
    assert pnt.Y() == pytest.approx(20.0)
    assert pnt.Z() == pytest.approx(30.0)


def test_vector_to_vec():
    from archi.kernel.vector import Vector
    from OCP.gp import gp_Vec
    v = Vector(1, 2, 3)
    gv = v.to_vec()
    assert isinstance(gv, gp_Vec)
    assert gv.X() == pytest.approx(1.0)
    assert gv.Y() == pytest.approx(2.0)
    assert gv.Z() == pytest.approx(3.0)


def test_vector_to_dir():
    from archi.kernel.vector import Vector
    from OCP.gp import gp_Dir
    v = Vector(0, 0, 5)
    d = v.to_dir()
    assert isinstance(d, gp_Dir)
    assert d.X() == pytest.approx(0.0)
    assert d.Y() == pytest.approx(0.0)
    assert d.Z() == pytest.approx(1.0)


def test_vector_from_pnt():
    from archi.kernel.vector import Vector
    from OCP.gp import gp_Pnt
    pnt = gp_Pnt(5.0, 10.0, 15.0)
    v = Vector.from_pnt(pnt)
    assert v.x == pytest.approx(5.0)
    assert v.y == pytest.approx(10.0)
    assert v.z == pytest.approx(15.0)


def test_vector_from_vec():
    from archi.kernel.vector import Vector
    from OCP.gp import gp_Vec
    gv = gp_Vec(3.0, 4.0, 5.0)
    v = Vector.from_vec(gv)
    assert v.x == pytest.approx(3.0)
    assert v.y == pytest.approx(4.0)
    assert v.z == pytest.approx(5.0)


def test_vector_repr():
    from archi.kernel.vector import Vector
    v = Vector(1.5, 2.5, 3.5)
    assert "1.5" in repr(v)
    assert "2.5" in repr(v)
    assert "3.5" in repr(v)
