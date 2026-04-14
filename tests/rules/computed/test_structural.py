import pytest


def test_structural_small_opening_passes():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.rules.computed.structural import check_structural_spans
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    room = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                       width=10.0, depth=10.0, area=100.0)
    g.add_edge(floor, room, "contains")
    wall = g.add_node(NodeType.WALL, thickness=5.5, structural=True,
                       exterior=True, material="wood_frame")
    opening = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                          width=36.0, height=80.0)
    g.add_edge(wall, opening, "contains")
    violations = check_structural_spans(g)
    assert len(violations) == 0


def test_structural_wide_opening_warns():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType
    from archi.rules.computed.structural import check_structural_spans
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    wall = g.add_node(NodeType.WALL, thickness=5.5, structural=True,
                       exterior=True, material="wood_frame")
    opening = g.add_node(NodeType.OPENING, opening_type=OpeningType.SLIDING_DOOR,
                          width=120.0, height=80.0)  # 10 feet
    g.add_edge(wall, opening, "contains")
    violations = check_structural_spans(g)
    assert len(violations) >= 1
    assert violations[0].severity in ("warning", "error")


def test_structural_nonstructural_wall_skipped():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType
    from archi.rules.computed.structural import check_structural_spans
    g = BuildingGraph()
    wall = g.add_node(NodeType.WALL, thickness=4.5, structural=False,
                       exterior=False, material="wood_frame")
    opening = g.add_node(NodeType.OPENING, opening_type=OpeningType.ARCHWAY,
                          width=144.0, height=80.0)  # 12 feet
    g.add_edge(wall, opening, "contains")
    violations = check_structural_spans(g)
    assert len(violations) == 0
