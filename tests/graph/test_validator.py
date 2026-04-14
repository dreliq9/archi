import pytest


def test_validator_catches_small_room():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.graph.validator import LiveValidator
    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=6.0, depth=5.0, area=30.0)
    g.add_edge(floor, bedroom, "contains")
    violations = validator.get_violations()
    bedroom_violations = [v for v in violations if v["node_id"] == bedroom]
    assert len(bedroom_violations) >= 1


def test_validator_no_violations_compliant():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.graph.validator import LiveValidator
    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0)
    g.add_edge(floor, kitchen, "contains")
    # Add exterior door so egress check passes
    ext_door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                           exterior=True, width_in=36.0, height_in=80.0)
    g.add_edge(ext_door, kitchen, "connects")
    violations = validator.get_violations()
    errors = [v for v in violations if v["severity"] == "error"]
    assert len(errors) == 0


def test_validator_updates_on_mutation():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.graph.validator import LiveValidator
    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=5.0, depth=5.0, area=25.0)
    g.add_edge(floor, bedroom, "contains")
    v1 = validator.get_violations()
    assert any(v["node_id"] == bedroom for v in v1)
    g.update_node(bedroom, width=12.0, depth=10.0, area=120.0)
    v2 = validator.get_violations()
    bedroom_errors = [v for v in v2 if v["node_id"] == bedroom and v["severity"] == "error"
                      and "area" in v["rule"].lower()]
    assert len(bedroom_errors) == 0


def test_validator_includes_computed_rules():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.graph.validator import LiveValidator
    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=12.0, depth=10.0, area=120.0)
    g.add_edge(floor, bedroom, "contains")
    violations = validator.get_violations()
    egress_violations = [v for v in violations if "egress" in v["rule"].lower()]
    assert len(egress_violations) >= 1


def test_validator_violation_count():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.graph.validator import LiveValidator
    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=5.0, depth=5.0, area=25.0)
    g.add_edge(floor, bedroom, "contains")
    counts = validator.get_violation_counts()
    assert isinstance(counts, dict)
    assert counts.get("error", 0) >= 1
