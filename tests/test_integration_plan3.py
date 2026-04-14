# tests/test_integration_plan3.py
"""Integration tests — Plan 3: export pipeline + interior design."""
import pytest
import tempfile
import os

def _make_furnished_house():
    from archi.graph.model import BuildingGraph, FurnitureType, NodeType, OpeningType, RoomType
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=50, lot_depth=40)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=9.0)
    g.add_edge(bldg, floor, "contains")
    living = g.add_node(NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
                         width=15.0, depth=12.0, area=180.0, x=0.0, y=0.0)
    kitchen = g.add_node(NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
                          width=12.0, depth=10.0, area=120.0, x=15.0, y=0.0)
    bedroom = g.add_node(NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
                          width=12.0, depth=10.0, area=120.0, x=0.0, y=12.0)
    g.add_edge(floor, living, "contains")
    g.add_edge(floor, kitchen, "contains")
    g.add_edge(floor, bedroom, "contains")
    g.add_edge(living, kitchen, "adjacent_to")
    g.add_edge(living, bedroom, "adjacent_to")
    sofa = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.SOFA,
                       width=84, depth=36, height=34, x=12.0, y=24.0)
    table = g.add_node(NodeType.FURNITURE, furniture_type=FurnitureType.COFFEE_TABLE,
                        width=48, depth=24, height=18, x=30.0, y=60.0)
    g.add_edge(living, sofa, "contains")
    g.add_edge(living, table, "contains")
    return g

def test_furniture_to_svg_pipeline():
    from archi.export.svg import render_floor_plan
    g = _make_furnished_house()
    svg = render_floor_plan(g, level=0)
    assert "</svg>" in svg
    assert svg.count("<rect") >= 5  # 3 rooms + 2 furniture

def test_furniture_to_dxf_pipeline():
    from archi.export.dxf import export_floor_plan
    g = _make_furnished_house()
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        path = f.name
    try:
        export_floor_plan(g, level=0, output_path=path)
        assert os.path.getsize(path) > 0
    finally:
        os.unlink(path)

def test_parametric_furniture_geometry():
    from archi.kernel.furniture import make_furniture
    result = make_furniture("sofa", width=84.0, depth=36.0, height=34.0)
    assert result.ok
    assert result.volume > 0
    from archi.kernel.interference import check_interference
    result2 = make_furniture("coffee_table", width=48.0, depth=24.0, height=18.0)
    collisions = check_interference([result.shape, result2.shape])
    assert isinstance(collisions, list)

def test_full_export_pipeline():
    from archi.export.svg import render_floor_plan
    from archi.export.dxf import export_floor_plan as export_dxf
    from archi.export.gltf import export_shapes_to_gltf
    from archi.kernel.primitives import make_wall, make_floor_slab
    from archi.kernel.vector import Vector
    g = _make_furnished_house()
    svg = render_floor_plan(g, level=0)
    assert "</svg>" in svg
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        dxf_path = f.name
    try:
        export_dxf(g, level=0, output_path=dxf_path)
        assert os.path.getsize(dxf_path) > 0
    finally:
        os.unlink(dxf_path)
    slab = make_floor_slab(
        [Vector(0, 0, 0), Vector(324, 0, 0), Vector(324, 264, 0), Vector(0, 264, 0)], thickness=6.0)
    wall = make_wall(Vector(0, 0, 0), Vector(324, 0, 0), height=108, thickness=5.5)
    assert slab.ok and wall.ok
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as f:
        glb_path = f.name
    try:
        export_shapes_to_gltf([slab.shape, wall.shape], output_path=glb_path)
        assert os.path.getsize(glb_path) > 0
    finally:
        os.unlink(glb_path)
