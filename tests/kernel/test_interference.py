import pytest

def test_no_interference_separate_boxes():
    from archi.kernel.interference import check_interference
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    box_a = backend.make_slab([Vector(0, 0, 0), Vector(10, 0, 0), Vector(10, 10, 0), Vector(0, 10, 0)], 10.0)
    box_b = backend.make_slab([Vector(50, 50, 0), Vector(60, 50, 0), Vector(60, 60, 0), Vector(50, 60, 0)], 10.0)
    collisions = check_interference([box_a, box_b])
    assert len(collisions) == 0

def test_interference_overlapping_boxes():
    from archi.kernel.interference import check_interference
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    box_a = backend.make_slab([Vector(0, 0, 0), Vector(20, 0, 0), Vector(20, 20, 0), Vector(0, 20, 0)], 10.0)
    box_b = backend.make_slab([Vector(10, 10, 0), Vector(30, 10, 0), Vector(30, 30, 0), Vector(10, 30, 0)], 10.0)
    collisions = check_interference([box_a, box_b])
    assert len(collisions) >= 1
    assert collisions[0]["pair"] == (0, 1)

def test_clearance_violation():
    from archi.kernel.interference import check_clearance
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    wall = backend.make_slab([Vector(0, -3, 0), Vector(100, -3, 0), Vector(100, 0, 0), Vector(0, 0, 0)], 96.0)
    furniture = backend.make_slab([Vector(10, 5, 0), Vector(40, 5, 0), Vector(40, 30, 0), Vector(10, 30, 0)], 30.0)
    violations = check_clearance(furniture_shape=furniture, obstacle_shapes=[wall], required_clearance=36.0)
    assert len(violations) >= 1

def test_clearance_ok():
    from archi.kernel.interference import check_clearance
    from archi.kernel.backend import OCPBackend
    from archi.kernel.vector import Vector
    backend = OCPBackend()
    wall = backend.make_slab([Vector(0, -3, 0), Vector(100, -3, 0), Vector(100, 0, 0), Vector(0, 0, 0)], 96.0)
    furniture = backend.make_slab([Vector(10, 50, 0), Vector(40, 50, 0), Vector(40, 75, 0), Vector(10, 75, 0)], 30.0)
    violations = check_clearance(furniture_shape=furniture, obstacle_shapes=[wall], required_clearance=36.0)
    assert len(violations) == 0

def test_interference_empty_list():
    from archi.kernel.interference import check_interference
    assert check_interference([]) == []
