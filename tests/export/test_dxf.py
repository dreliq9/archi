import pytest
import tempfile
import os

def _make_house_graph():
    from archi.graph.model import BuildingGraph, NodeType, RoomType
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
    return g

def test_dxf_export_creates_file():
    from archi.export.dxf import export_floor_plan
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        path = f.name
    try:
        export_floor_plan(g, level=0, output_path=path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)

def test_dxf_has_layers():
    from archi.export.dxf import export_floor_plan
    import ezdxf
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        path = f.name
    try:
        export_floor_plan(g, level=0, output_path=path)
        doc = ezdxf.readfile(path)
        layer_names = [l.dxf.name for l in doc.layers]
        assert "ROOMS" in layer_names
        assert "WALLS" in layer_names
        assert "LABELS" in layer_names
    finally:
        os.unlink(path)

def test_dxf_has_room_entities():
    from archi.export.dxf import export_floor_plan
    import ezdxf
    g = _make_house_graph()
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        path = f.name
    try:
        export_floor_plan(g, level=0, output_path=path)
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        polylines = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
        assert len(polylines) >= 2
    finally:
        os.unlink(path)
