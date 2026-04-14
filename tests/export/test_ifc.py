import pytest
import tempfile
import os

ifcopenshell = pytest.importorskip("ifcopenshell")

def _make_house_graph():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=40, lot_depth=30, name="Test House")
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0, x=0.0, y=0.0)
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0, x=12.0, y=0.0)
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, living, "contains")
    return g

def test_ifc_export_creates_file():
    from archi.export.ifc import export_to_ifc
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        path = f.name
    try:
        export_to_ifc(g, output_path=path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)

def test_ifc_contains_spaces():
    from archi.export.ifc import export_to_ifc
    import ifcopenshell
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        path = f.name
    try:
        export_to_ifc(g, output_path=path)
        model = ifcopenshell.open(path)
        spaces = model.by_type("IfcSpace")
        assert len(spaces) >= 2
    finally:
        os.unlink(path)

def test_ifc_has_building_storey():
    from archi.export.ifc import export_to_ifc
    import ifcopenshell
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        path = f.name
    try:
        export_to_ifc(g, output_path=path)
        model = ifcopenshell.open(path)
        storeys = model.by_type("IfcBuildingStorey")
        assert len(storeys) >= 1
    finally:
        os.unlink(path)
