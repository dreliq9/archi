import pytest


def test_compact_footprint_matches_requested_area():
    from archi.server import BuildingState

    footprint = BuildingState._compact_footprint(400.0, 80.0, 100.0)
    assert footprint is not None
    width, depth = footprint
    assert width <= 80.0
    assert depth <= 100.0
    assert width * depth == pytest.approx(400.0)


def test_compact_footprint_rejects_area_larger_than_buildable_lot():
    from archi.server import BuildingState

    assert BuildingState._compact_footprint(1001.0, 10.0, 100.0) is None


def test_live_layout_packs_rooms_into_target_sized_footprint():
    from archi.graph.model import NodeType
    from archi.server import BuildingState
    from archi.tools.arch import add_floor, add_room, create_building

    state = BuildingState()
    create_building(
        state,
        lot_width=100,
        lot_depth=100,
        setbacks={"front": 5, "back": 5, "left": 5, "right": 5},
    )
    add_floor(state, 0, 9.0)
    a = add_room(state, "kitchen", area=150)
    b = add_room(state, "dining_room", area=120, adjacent_to=[a["room_id"]])

    meta = state._layout_meta[0]
    assert meta["footprint_area_sqft"] == pytest.approx(270.0)
    rooms = state.graph.get_all_nodes(NodeType.ROOM)
    solved_area = sum(float(props["area"]) for props in rooms.values())
    assert solved_area == pytest.approx(meta["footprint_area_sqft"], rel=0.02)
