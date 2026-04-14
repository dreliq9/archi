import pytest


def test_ventilation_adequate_windows():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.rules.computed.ventilation import check_ventilation
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=10.0, depth=10.0, area=100.0)
    g.add_edge(floor, living, "contains")
    window = g.add_node(NodeType.OPENING, opening_type=OpeningType.WINDOW,
                         width=36.0, height=48.0, operable_area_sqft=12.0)
    g.add_edge(window, living, "connects")
    violations = check_ventilation(g)
    living_violations = [v for v in violations if v.node_id == living]
    assert len(living_violations) == 0


def test_ventilation_insufficient_windows():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.computed.ventilation import check_ventilation
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=15.0, area=225.0)
    g.add_edge(floor, living, "contains")
    violations = check_ventilation(g)
    living_violations = [v for v in violations if v.node_id == living
                         and "ventilation" in v.rule.lower()]
    assert len(living_violations) >= 1


def test_ventilation_bathroom_needs_mechanical():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.computed.ventilation import check_ventilation
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bath = g.add_node(NodeType.ROOM, room_type=RoomType.BATHROOM, level=0,
                       width=8.0, depth=5.0, area=40.0, has_mechanical_vent=False)
    g.add_edge(floor, bath, "contains")
    violations = check_ventilation(g)
    bath_violations = [v for v in violations if v.node_id == bath]
    assert len(bath_violations) >= 1


def test_ventilation_bathroom_with_mechanical_passes():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.computed.ventilation import check_ventilation
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bath = g.add_node(NodeType.ROOM, room_type=RoomType.BATHROOM, level=0,
                       width=8.0, depth=5.0, area=40.0, has_mechanical_vent=True)
    g.add_edge(floor, bath, "contains")
    violations = check_ventilation(g)
    bath_violations = [v for v in violations if v.node_id == bath
                       and "mechanical" in v.rule.lower()]
    assert len(bath_violations) == 0
