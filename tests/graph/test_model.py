import pytest


def test_create_building_node():
    from archi.graph.model import BuildingGraph, NodeType
    g = BuildingGraph()
    node_id = g.add_node(NodeType.BUILDING, lot_width=80.0, lot_depth=120.0,
        setbacks={"front": 25, "back": 20, "left": 10, "right": 10}, orientation=0.0, stories=1)
    node = g.get_node(node_id)
    assert node["type"] == NodeType.BUILDING
    assert node["lot_width"] == 80.0
    assert node["stories"] == 1


def test_create_floor_node():
    from archi.graph.model import BuildingGraph, NodeType
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor_id = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=108.0)
    g.add_edge(bldg, floor_id, "contains")
    node = g.get_node(floor_id)
    assert node["type"] == NodeType.FLOOR
    assert node["level"] == 0
    assert node["floor_to_floor_height"] == 108.0


def test_create_room_node():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    room_id = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, min_area=100.0, max_area=200.0, level=0)
    node = g.get_node(room_id)
    assert node["type"] == NodeType.ROOM
    assert node["room_type"] == RoomType.KITCHEN


def test_create_wall_node():
    from archi.graph.model import BuildingGraph, NodeType
    g = BuildingGraph()
    wall_id = g.add_node(NodeType.WALL, thickness=5.5, structural=True, exterior=True, material="wood_frame")
    node = g.get_node(wall_id)
    assert node["structural"] is True
    assert node["exterior"] is True


def test_create_opening_node():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType
    g = BuildingGraph()
    opening_id = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36.0, height=80.0)
    node = g.get_node(opening_id)
    assert node["opening_type"] == OpeningType.DOOR
    assert node["width"] == 36.0


def test_create_furniture_node():
    from archi.graph.model import BuildingGraph, FurnitureType, NodeType
    g = BuildingGraph()
    furn_id = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.SOFA,
        width=84.0, depth=36.0, height=34.0, clearance_zone={"front": 36, "sides": 6})
    node = g.get_node(furn_id)
    assert node["furniture_type"] == FurnitureType.SOFA


def test_create_fixture_node():
    from archi.graph.model import BuildingGraph, FixtureType, NodeType
    g = BuildingGraph()
    fix_id = g.add_node(NodeType.FIXTURE, fixture_type=FixtureType.TOILET,
        clearance_front=21.0, clearance_sides=15.0, plumbing=True, electrical=False, gas=False)
    node = g.get_node(fix_id)
    assert node["fixture_type"] == FixtureType.TOILET
    assert node["plumbing"] is True


def test_add_edge_adjacent():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    g.add_edge(kitchen, dining, "adjacent_to")
    edges = g.get_edges(kitchen)
    assert len(edges) == 1
    assert edges[0]["target"] == dining
    assert edges[0]["edge_type"] == "adjacent_to"


def test_add_edge_contains():
    from archi.graph.model import BuildingGraph, FurnitureType, NodeType, RoomType
    g = BuildingGraph()
    room = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0)
    sofa = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.SOFA, width=84, depth=36, height=34)
    g.add_edge(room, sofa, "contains")
    edges = g.get_edges(room)
    assert any(e["edge_type"] == "contains" and e["target"] == sofa for e in edges)


def test_add_edge_connects():
    from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType
    g = BuildingGraph()
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    door = g.add_node(NodeType.OPENING, opening_type=OpeningType.DOOR, width=36, height=80)
    g.add_edge(door, kitchen, "connects")
    g.add_edge(door, dining, "connects")
    door_edges = g.get_edges(door)
    assert len(door_edges) == 2


def test_adjacent_to_is_bidirectional():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    a = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    b = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    g.add_edge(a, b, "adjacent_to")
    assert any(e["target"] == b for e in g.get_edges(a))
    assert any(e["target"] == a for e in g.get_edges(b))


def test_get_adjacent_rooms():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0)
    g.add_edge(kitchen, dining, "adjacent_to")
    g.add_edge(kitchen, living, "adjacent_to")
    adjacent = g.get_adjacent_rooms(kitchen)
    assert set(adjacent) == {dining, living}


def test_get_rooms_on_floor():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    floor0 = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=108)
    floor1 = g.add_node(NodeType.FLOOR, level=1, floor_to_floor_height=108)
    r1 = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    r2 = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0)
    r3 = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=1)
    g.add_edge(floor0, r1, "contains")
    g.add_edge(floor0, r2, "contains")
    g.add_edge(floor1, r3, "contains")
    rooms_0 = g.get_rooms_on_floor(floor0)
    rooms_1 = g.get_rooms_on_floor(floor1)
    assert set(rooms_0) == {r1, r2}
    assert rooms_1 == [r3]


def test_get_furniture_in_room():
    from archi.graph.model import BuildingGraph, FurnitureType, NodeType, RoomType
    g = BuildingGraph()
    room = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0)
    sofa = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.SOFA, width=84, depth=36, height=34)
    table = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.COFFEE_TABLE, width=48, depth=24, height=18)
    g.add_edge(room, sofa, "contains")
    g.add_edge(room, table, "contains")
    furniture = g.get_furniture_in_room(room)
    assert set(furniture) == {sofa, table}


def test_remove_node_removes_edges():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    a = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    b = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    c = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0)
    g.add_edge(a, b, "adjacent_to")
    g.add_edge(b, c, "adjacent_to")
    g.remove_node(b)
    with pytest.raises(KeyError):
        g.get_node(b)
    assert len(g.get_edges(a)) == 0
    assert len(g.get_edges(c)) == 0


def test_get_nonexistent_node_raises():
    from archi.graph.model import BuildingGraph
    g = BuildingGraph()
    with pytest.raises(KeyError):
        g.get_node("nonexistent_id")


def test_graph_serialize_deserialize():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0, min_area=100)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    g.add_edge(kitchen, dining, "adjacent_to")
    data = g.to_dict()
    g2 = BuildingGraph.from_dict(data)
    assert g2.get_node(kitchen)["room_type"] == RoomType.KITCHEN
    assert g2.get_node(kitchen)["min_area"] == 100
    assert len(g2.get_edges(kitchen)) == 1


def test_mutation_callback():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    mutations = []
    g = BuildingGraph(on_mutate=lambda event: mutations.append(event))
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0)
    dining = g.add_node(NodeType.ROOM, room_type=RoomType.DINING_ROOM, level=0)
    g.add_edge(kitchen, dining, "adjacent_to")
    assert len(mutations) == 3
    assert mutations[0]["action"] == "add_node"
    assert mutations[2]["action"] == "add_edge"
