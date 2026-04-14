# tests/rules/test_engine.py
import pytest


def _make_test_graph():
    """Build a minimal graph: building -> floor -> 2 rooms (kitchen 8x8, bedroom 6x6)."""
    from archi.graph.model import BuildingGraph, NodeType, RoomType

    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120,
                       setbacks={"front": 25, "back": 20, "left": 10, "right": 10})
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")

    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=8.0, depth=8.0, area=64.0)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=6.0, depth=6.0, area=36.0)
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, bedroom, "contains")
    return g, {"kitchen": kitchen, "bedroom": bedroom, "floor": floor}


def test_load_irc_2021():
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    assert engine.jurisdiction == "IRC-2021"
    assert "room_minimums" in engine.rules


def test_load_unknown_jurisdiction_raises():
    from archi.rules.engine import RuleEngine
    with pytest.raises(FileNotFoundError):
        RuleEngine("FAKE-999")


def test_room_minimum_area_violation():
    """Bedroom with 36 sqft should violate the 70 sqft minimum."""
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    g, ids = _make_test_graph()
    violations = engine.evaluate_declarative(g)
    bedroom_violations = [v for v in violations if v["node_id"] == ids["bedroom"]
                          and "area" in v["rule"].lower()]
    assert len(bedroom_violations) >= 1
    assert bedroom_violations[0]["severity"] == "error"


def test_room_minimum_dimension_violation():
    """Bedroom with 6ft dimension should violate the 7ft minimum."""
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    g, ids = _make_test_graph()
    violations = engine.evaluate_declarative(g)
    dim_violations = [v for v in violations if v["node_id"] == ids["bedroom"]
                      and "dimension" in v["rule"].lower()]
    assert len(dim_violations) >= 1


def test_compliant_room_no_violations():
    """A 12x10 kitchen (120 sqft) should pass all room minimum rules."""
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0)
    g.add_edge(floor, kitchen, "contains")
    violations = engine.evaluate_declarative(g)
    kitchen_violations = [v for v in violations if v["node_id"] == kitchen]
    assert len(kitchen_violations) == 0


def test_ceiling_height_violation():
    """Floor with 6.5ft ceiling should violate the 7ft minimum for habitable rooms."""
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=6.5)
    g.add_edge(bldg, floor, "contains")
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0)
    g.add_edge(floor, living, "contains")
    violations = engine.evaluate_declarative(g)
    height_violations = [v for v in violations if v["node_id"] == living
                         and "ceiling" in v["rule"].lower()]
    assert len(height_violations) >= 1
    assert height_violations[0]["severity"] == "error"


def test_stair_riser_violation():
    """Stair with 8-inch risers should violate the 7.75-inch max."""
    from archi.graph.model import BuildingGraph, NodeType
    from archi.rules.engine import RuleEngine
    engine = RuleEngine("IRC-2021")
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    stair = g.add_node(NodeType.WALL, riser_height_in=8.0, tread_depth_in=11.0,
                        width_in=36.0, is_stair=True)
    g.add_edge(floor, stair, "contains")
    violations = engine.evaluate_declarative(g)
    stair_violations = [v for v in violations if v["node_id"] == stair
                        and "riser" in v["rule"].lower()]
    assert len(stair_violations) >= 1
