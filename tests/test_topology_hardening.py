import pytest


def _fresh_state():
    from archi.server import BuildingState
    return BuildingState()


def _build_floor(state):
    from archi.tools.arch import create_building, add_floor
    create_building(
        state,
        lot_width=60,
        lot_depth=60,
        setbacks={"front": 5, "back": 5, "left": 5, "right": 5},
    )
    add_floor(state, level=0, height=9.0)


def test_derive_wall_segments_deduplicates_shared_boundary():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.graph.topology import derive_wall_segments

    g = BuildingGraph()
    building = g.add_node(NodeType.BUILDING)
    floor = g.add_node(NodeType.FLOOR, level=0)
    g.add_edge(building, floor, "contains")
    a = g.add_node(
        NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
        x=0.0, y=0.0, width=10.0, depth=10.0,
    )
    b = g.add_node(
        NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
        x=10.0, y=0.0, width=10.0, depth=10.0,
    )
    g.add_edge(floor, a, "contains")
    g.add_edge(floor, b, "contains")

    segments = derive_wall_segments(g, level=0)
    shared = [segment for segment in segments if set(segment.room_ids) == {a, b}]
    assert len(shared) == 1
    assert shared[0].length_ft == pytest.approx(10.0)
    assert len(segments) == 7


def test_live_layout_compiles_canonical_walls():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_room

    state = _fresh_state()
    _build_floor(state)
    a = add_room(state, "kitchen", area=150)
    b = add_room(state, "dining_room", area=120, adjacent_to=[a["room_id"]])

    walls = state.graph.get_all_nodes(NodeType.WALL)
    assert walls
    assert state._layout_meta[0]["canonical_walls"] == len(walls)
    shared = [
        props for props in walls.values()
        if set(props.get("room_ids", [])) == {a["room_id"], b["room_id"]}
    ]
    assert shared, "Adjacent rooms should have one canonical shared boundary segment"


def test_opening_binds_to_shared_wall():
    from archi.tools.arch import add_opening, add_room

    state = _fresh_state()
    _build_floor(state)
    a = add_room(state, "kitchen", area=150)
    b = add_room(state, "dining_room", area=120, adjacent_to=[a["room_id"]])
    result = add_opening(
        state,
        "door",
        width=36,
        height=80,
        room_a=a["room_id"],
        room_b=b["room_id"],
    )

    assert result["success"] is True
    opening = state.graph.get_node(result["opening_id"])
    assert opening["topology_status"] == "bound"
    wall = state.graph.get_node(opening["wall_id"])
    assert set(wall["room_ids"]) == {a["room_id"], b["room_id"]}
    assert any(
        edge["edge_type"] == "contains" and edge["target"] == result["opening_id"]
        for edge in state.graph.get_edges(opening["wall_id"])
    )


def test_oversize_opening_rolls_back():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_opening, add_room

    state = _fresh_state()
    _build_floor(state)
    a = add_room(state, "kitchen", area=150)
    b = add_room(state, "dining_room", area=120, adjacent_to=[a["room_id"]])
    before = set(state.graph.get_all_nodes(NodeType.OPENING))

    result = add_opening(
        state,
        "door",
        width=1000,
        height=80,
        room_a=a["room_id"],
        room_b=b["room_id"],
    )
    assert result["success"] is False
    assert set(state.graph.get_all_nodes(NodeType.OPENING)) == before


def test_removing_room_removes_connected_openings():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_opening, add_room, remove_room

    state = _fresh_state()
    _build_floor(state)
    a = add_room(state, "kitchen", area=150)
    b = add_room(state, "dining_room", area=120, adjacent_to=[a["room_id"]])
    opening = add_opening(
        state,
        "door",
        width=36,
        height=80,
        room_a=a["room_id"],
        room_b=b["room_id"],
    )
    assert opening["success"] is True

    result = remove_room(state, a["room_id"])
    assert result["success"] is True
    assert opening["opening_id"] not in state.graph.get_all_nodes(NodeType.OPENING)


def test_furniture_collision_is_rejected_atomically():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_room
    from archi.tools.interior import place_furniture

    state = _fresh_state()
    _build_floor(state)
    room = add_room(state, "living_room", area=240)
    room_id = room["room_id"]

    first = place_furniture(
        state, room_id, "coffee_table", x=10, y=10,
        width=24, depth=24, height=18,
    )
    assert first["success"] is True

    second = place_furniture(
        state, room_id, "end_table", x=20, y=20,
        width=24, depth=24, height=18,
    )
    assert second["success"] is False
    assert len(state.graph.get_all_nodes(NodeType.FURNITURE)) == 1
