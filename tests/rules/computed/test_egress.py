import pytest


def _make_egress_graph(has_exterior_door=True):
    """Build graph: building -> floor -> 3 rooms in chain.
    kitchen <-adjacent-> hallway <-adjacent-> bedroom
    If has_exterior_door, kitchen has an exterior door.
    """
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType

    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")

    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=10.0, depth=10.0, area=100.0)
    hallway = g.add_node(NodeType.ROOM, room_type=RoomType.HALLWAY, level=0,
                          width=4.0, depth=10.0, area=40.0)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=12.0, depth=10.0, area=120.0)

    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, hallway, "contains")
    g.add_edge(floor, bedroom, "contains")
    g.add_edge(kitchen, hallway, "adjacent_to")
    g.add_edge(hallway, bedroom, "adjacent_to")

    door1 = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36, height=80)
    g.add_edge(door1, kitchen, "connects")
    g.add_edge(door1, hallway, "connects")
    door2 = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36, height=80)
    g.add_edge(door2, hallway, "connects")
    g.add_edge(door2, bedroom, "connects")

    if has_exterior_door:
        ext_door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                               width=36, height=80, exterior=True)
        g.add_edge(ext_door, kitchen, "connects")

    return g, {"kitchen": kitchen, "hallway": hallway, "bedroom": bedroom}


def test_egress_all_rooms_reachable():
    from archi.rules.computed.egress import check_egress
    g, ids = _make_egress_graph(has_exterior_door=True)
    violations = check_egress(g)
    habitable_violations = [v for v in violations if "egress" in v.rule.lower()]
    assert len(habitable_violations) == 0


def test_egress_no_exterior_door():
    from archi.rules.computed.egress import check_egress
    g, ids = _make_egress_graph(has_exterior_door=False)
    violations = check_egress(g)
    habitable_violations = [v for v in violations if "egress" in v.rule.lower()]
    assert len(habitable_violations) >= 2  # kitchen + bedroom


def test_egress_isolated_room():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    from archi.rules.computed.egress import check_egress
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=10.0, depth=12.0, area=120.0)
    g.add_edge(floor, bedroom, "contains")
    violations = check_egress(g)
    assert any(v.node_id == bedroom for v in violations)
