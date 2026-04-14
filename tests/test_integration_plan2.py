"""Integration tests — Plan 2: layout solver + code rules engine."""
import pytest


def test_treemap_to_csp_pipeline():
    """Treemap seeds the CSP solver, which produces a refined layout."""
    from archi.graph.solver import CSPSolver, TreemapSolver

    rooms = [
        {"id": "living", "target_area": 250.0, "min_area": 220.0, "max_area": 280.0},
        {"id": "kitchen", "target_area": 150.0, "min_area": 130.0, "max_area": 170.0},
        {"id": "bedroom", "target_area": 120.0, "min_area": 100.0, "max_area": 140.0},
    ]

    seed = TreemapSolver.solve(footprint_width=25.0, footprint_depth=22.0, rooms=rooms)
    assert len(seed) == 3

    result = CSPSolver.solve(
        footprint_width=25.0,
        footprint_depth=22.0,
        rooms=rooms,
        adjacencies=[("living", "kitchen"), ("kitchen", "bedroom")],
        seed=seed,
    )
    assert result is not None
    assert len(result) == 3
    for rid, r in result.items():
        assert r["x"] >= 0
        assert r["y"] >= 0
        assert r["x"] + r["width"] <= 25.01
        assert r["y"] + r["depth"] <= 22.01


def test_graph_to_validator_pipeline():
    """Build a house in the graph, run live validator, check for expected violations."""
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.graph.validator import LiveValidator

    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")

    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120,
                       setbacks={"front": 25, "back": 20, "left": 10, "right": 10})
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")

    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=6.0, depth=6.0, area=36.0)
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, bedroom, "contains")
    g.add_edge(kitchen, bedroom, "adjacent_to")

    ext_door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                           width=36, height=80, exterior=True)
    g.add_edge(ext_door, kitchen, "connects")

    int_door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                           width=36, height=80)
    g.add_edge(int_door, kitchen, "connects")
    g.add_edge(int_door, bedroom, "connects")

    violations = validator.get_violations()

    bedroom_area = [v for v in violations if v["node_id"] == bedroom
                    and "area" in v["rule"].lower()]
    assert len(bedroom_area) >= 1

    bedroom_dim = [v for v in violations if v["node_id"] == bedroom
                   and "dimension" in v["rule"].lower()]
    assert len(bedroom_dim) >= 1

    kitchen_errors = [v for v in violations if v["node_id"] == kitchen
                      and v["severity"] == "error"]
    assert len(kitchen_errors) == 0

    egress_violations = [v for v in violations if "egress" in v["rule"].lower()]
    assert len(egress_violations) == 0


def test_full_compliant_house():
    """A fully compliant small house should have zero error violations."""
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    from archi.graph.validator import LiveValidator

    g = BuildingGraph()
    validator = LiveValidator(g, jurisdiction="IRC-2021")

    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")

    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0)
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=12.0, depth=10.0, area=120.0)
    bathroom = g.add_node(NodeType.ROOM, room_type=RoomType.BATHROOM, level=0,
                           width=8.0, depth=5.0, area=40.0,
                           has_mechanical_vent=True)
    hallway = g.add_node(NodeType.ROOM, room_type=RoomType.HALLWAY, level=0,
                          width=4.0, depth=15.0, area=60.0)

    for room in [living, kitchen, bedroom, bathroom, hallway]:
        g.add_edge(floor, room, "contains")

    g.add_edge(living, hallway, "adjacent_to")
    g.add_edge(kitchen, hallway, "adjacent_to")
    g.add_edge(bedroom, hallway, "adjacent_to")
    g.add_edge(bathroom, hallway, "adjacent_to")

    ext_door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                           width=36, height=80, exterior=True)
    g.add_edge(ext_door, living, "connects")

    for room in [kitchen, bedroom, bathroom]:
        door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                           width=36, height=80)
        g.add_edge(door, hallway, "connects")
        g.add_edge(door, room, "connects")

    door_lh = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR,
                          width=36, height=80)
    g.add_edge(door_lh, living, "connects")
    g.add_edge(door_lh, hallway, "connects")

    for room in [living, kitchen, bedroom]:
        window = g.add_node(NodeType.OPENING, opening_type=OpeningType.WINDOW,
                             width=36, height=48, operable_area_sqft=12.0)
        g.add_edge(window, room, "connects")

    violations = validator.get_violations()
    errors = [v for v in violations if v["severity"] == "error"]
    assert len(errors) == 0, f"Expected no errors, got: {errors}"
