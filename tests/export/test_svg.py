import pytest

def _make_simple_house():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=40, lot_depth=30)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0, x=0.0, y=0.0)
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0, x=12.0, y=0.0)
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, living, "contains")
    g.add_edge(kitchen, living, "adjacent_to")
    door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36, height=80)
    g.add_edge(door, kitchen, "connects")
    g.add_edge(door, living, "connects")
    return g

def test_svg_produces_valid_svg():
    from archi.export.svg import render_floor_plan
    g = _make_simple_house()
    svg_str = render_floor_plan(g, level=0)
    assert svg_str.startswith("<?xml") or svg_str.startswith("<svg")
    assert "</svg>" in svg_str

def test_svg_contains_room_labels():
    from archi.export.svg import render_floor_plan
    g = _make_simple_house()
    svg_str = render_floor_plan(g, level=0)
    assert "kitchen" in svg_str.lower() or "Kitchen" in svg_str
    assert "living" in svg_str.lower() or "Living" in svg_str

def test_svg_contains_room_areas():
    from archi.export.svg import render_floor_plan
    g = _make_simple_house()
    svg_str = render_floor_plan(g, level=0)
    assert "120" in svg_str
    assert "180" in svg_str

def test_svg_rooms_have_color():
    from archi.export.svg import render_floor_plan
    g = _make_simple_house()
    svg_str = render_floor_plan(g, level=0)
    assert "fill" in svg_str

def test_svg_empty_graph():
    from archi.graph.model import BuildingGraph
    from archi.export.svg import render_floor_plan
    g = BuildingGraph()
    svg_str = render_floor_plan(g, level=0)
    assert "</svg>" in svg_str

def test_svg_with_furniture():
    from archi.graph.model import BuildingGraph, FurnitureType, NodeType, RoomType
    from archi.export.svg import render_floor_plan
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=40, lot_depth=30)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0, x=0.0, y=0.0)
    g.add_edge(floor, living, "contains")
    sofa = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.SOFA,
                       width=84, depth=36, height=34, x=12.0, y=24.0)
    g.add_edge(living, sofa, "contains")
    svg_str = render_floor_plan(g, level=0)
    assert "</svg>" in svg_str
    assert svg_str.count("<rect") >= 2
