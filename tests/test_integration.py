"""Integration tests — verify kernel and graph work together."""
import pytest


def test_wall_with_opening_round_trip():
    """Create a wall, cut a door, verify geometry and graph agree."""
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.kernel.primitives import make_opening, make_wall
    from archi.kernel.vector import Vector

    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=108)
    g.add_edge(bldg, floor, "contains")

    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0, min_area=100)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, dining, "contains")
    g.add_edge(kitchen, dining, "adjacent_to")

    wall_node = g.add_node(NodeType.WALL, thickness=5.5, structural=False, exterior=False)
    door_node = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36.0, height=80.0)
    g.add_edge(door_node, kitchen, "connects")
    g.add_edge(door_node, dining, "connects")

    wall_result = make_wall(start=Vector(0, 0, 0), end=Vector(120, 0, 0), height=108.0, thickness=5.5)
    assert wall_result.ok

    door_result = make_opening(wall_result=wall_result, position=Vector(60, 0, 0), width=36.0, height=80.0)
    assert door_result.ok
    assert door_result.volume < wall_result.volume

    assert len(g.get_adjacent_rooms(kitchen)) == 1
    assert g.get_adjacent_rooms(kitchen)[0] == dining

    data = g.to_dict()
    g2 = BuildingGraph.from_dict(data)
    assert g2.get_node(kitchen)["room_type"] == RoomType.KITCHEN
    assert len(g2.get_adjacent_rooms(kitchen)) == 1


def test_multi_room_floor_plan():
    """Build a simple 3-room floor plan with graph relationships."""
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.kernel.primitives import make_floor_slab, make_wall
    from archi.kernel.vector import Vector

    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=50, lot_depth=80, stories=1)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=108)
    g.add_edge(bldg, floor, "contains")

    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0, min_area=100)
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0, min_area=200)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0, min_area=120)

    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, living, "contains")
    g.add_edge(floor, bedroom, "contains")
    g.add_edge(kitchen, living, "adjacent_to")
    g.add_edge(living, bedroom, "adjacent_to")

    slab = make_floor_slab(
        boundary=[Vector(0, 0, 0), Vector(360, 0, 0), Vector(360, 480, 0), Vector(0, 480, 0)],
        thickness=6.0,
    )
    assert slab.ok

    w1 = make_wall(Vector(0, 200, 0), Vector(360, 200, 0), height=108, thickness=5.5)
    w2 = make_wall(Vector(0, 320, 0), Vector(360, 320, 0), height=108, thickness=5.5)
    assert w1.ok and w2.ok

    rooms = g.get_rooms_on_floor(floor)
    assert len(rooms) == 3

    living_adjacent = g.get_adjacent_rooms(living)
    assert set(living_adjacent) == {kitchen, bedroom}

    kitchen_adjacent = g.get_adjacent_rooms(kitchen)
    assert bedroom not in kitchen_adjacent


def test_subprocess_isolation_with_wall_booleans():
    """Verify subprocess isolation works for wall intersection booleans."""
    try:
        from archi.kernel.isolation import safe_boolean_cut
    except ImportError:
        pytest.skip("isolation module not yet implemented")

    from archi.kernel.primitives import make_wall
    from archi.kernel.vector import Vector

    wall_a = make_wall(Vector(0, 0, 0), Vector(120, 0, 0), height=108, thickness=5.5)
    wall_b = make_wall(Vector(60, -60, 0), Vector(60, 60, 0), height=108, thickness=5.5)
    assert wall_a.ok and wall_b.ok

    result = safe_boolean_cut(wall_a.shape, wall_b.shape)
    assert result.ok
    assert result.volume < wall_a.volume
