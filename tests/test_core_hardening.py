import pytest


def _fresh_state():
    from archi.server import BuildingState
    return BuildingState()


def _build_floor(state, width=80.0, depth=120.0):
    from archi.tools.arch import create_building, add_floor

    create_building(
        state,
        lot_width=width,
        lot_depth=depth,
        setbacks={"front": 10, "back": 10, "left": 10, "right": 10},
    )
    add_floor(state, level=0, height=9.0)


def _share_wall(a, b, tol=0.1):
    vertical = (
        abs(a["x"] + a["width"] - b["x"]) <= tol
        or abs(b["x"] + b["width"] - a["x"]) <= tol
    )
    horizontal = (
        abs(a["y"] + a["depth"] - b["y"]) <= tol
        or abs(b["y"] + b["depth"] - a["y"]) <= tol
    )
    return vertical or horizontal


def test_unit_helpers():
    from archi.units import feet_to_inches, inches_to_feet, sqft_to_sqin, sqin_to_sqft

    assert feet_to_inches(10) == pytest.approx(120)
    assert inches_to_feet(120) == pytest.approx(10)
    assert sqft_to_sqin(1) == pytest.approx(144)
    assert sqin_to_sqft(144) == pytest.approx(1)


def test_graph_transaction_rolls_back_without_commit():
    from archi.graph.model import BuildingGraph, NodeType

    graph = BuildingGraph()
    original = graph.add_node(NodeType.BUILDING, name="original")
    with graph.transaction():
        graph.add_node(NodeType.ROOM, name="temporary")

    nodes = graph.get_all_nodes()
    assert set(nodes) == {original}


def test_graph_transaction_commits():
    from archi.graph.model import BuildingGraph, NodeType

    graph = BuildingGraph()
    with graph.transaction() as tx:
        room_id = graph.add_node(NodeType.ROOM, name="kept")
        tx.commit()

    assert graph.get_node(room_id)["name"] == "kept"


def test_failed_opening_leaves_no_orphan_node():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_opening, add_room

    state = _fresh_state()
    _build_floor(state)
    room = add_room(state, room_type="living_room", level=0, area=180)
    before = set(state.graph.get_all_nodes(NodeType.OPENING))

    result = add_opening(
        state,
        opening_type="door",
        width=36,
        height=80,
        room_a=room["room_id"],
        room_b="missing-room",
    )

    assert result["success"] is False
    assert set(state.graph.get_all_nodes(NodeType.OPENING)) == before


def test_room_target_area_survives_relayout():
    from archi.tools.arch import add_room

    state = _fresh_state()
    _build_floor(state)
    first = add_room(state, room_type="kitchen", level=0, area=120)
    first_props = state.graph.get_node(first["room_id"])
    assert first_props["target_area"] == pytest.approx(120)

    add_room(state, room_type="living_room", level=0, area=200)
    first_props = state.graph.get_node(first["room_id"])
    assert first_props["target_area"] == pytest.approx(120)
    assert 96 <= first_props["area"] <= 144


def test_live_layout_uses_csp_for_adjacency():
    from archi.tools.arch import add_room

    state = _fresh_state()
    _build_floor(state)
    kitchen = add_room(state, room_type="kitchen", level=0, area=150)
    dining = add_room(
        state,
        room_type="dining_room",
        level=0,
        area=120,
        adjacent_to=[kitchen["room_id"]],
    )

    assert state._layout_meta[0]["solver"] == "csp"
    k = state.graph.get_node(kitchen["room_id"])
    d = state.graph.get_node(dining["room_id"])
    assert _share_wall(k, d)


def test_opening_dimensions_are_explicit_inches():
    from archi.graph.model import NodeType
    from archi.tools.arch import add_opening, add_room

    state = _fresh_state()
    _build_floor(state)
    a = add_room(state, room_type="living_room", level=0, area=180)
    b = add_room(state, room_type="dining_room", level=0, area=120, adjacent_to=[a["room_id"]])
    result = add_opening(
        state,
        opening_type="door",
        width=36,
        height=80,
        room_a=a["room_id"],
        room_b=b["room_id"],
    )
    props = state.graph.get_node(result["opening_id"])
    assert props["dimension_unit"] == "in"
    assert props["width"] == pytest.approx(36)
    assert props["type"] == NodeType.OPENING
