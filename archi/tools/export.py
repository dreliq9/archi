"""export_* MCP tools — file export operations."""
from __future__ import annotations
import tempfile
from archi.export.dxf import export_floor_plan as dxf_export
from archi.export.gltf import export_shapes_to_gltf
from archi.export.svg import render_floor_plan
from archi.graph.model import NodeType
from archi.kernel.primitives import make_floor_slab, make_wall
from archi.kernel.vector import Vector
from archi.server import BuildingState, mcp, state

def export_svg(s: BuildingState, level: int = 0) -> dict:
    svg = render_floor_plan(s.graph, level=level)
    return {"success": True, "format": "svg", "content": svg}

def export_dxf(s: BuildingState, level: int = 0) -> dict:
    path = tempfile.mktemp(suffix=".dxf", prefix="archi_")
    dxf_export(s.graph, level=level, output_path=path)
    return {"success": True, "format": "dxf", "path": path}

def export_gltf(s: BuildingState) -> dict:
    shapes = []
    rooms = s.graph.get_all_nodes(NodeType.ROOM)
    for rid, props in rooms.items():
        x = props.get("x", 0.0) * 12  # feet to inches
        y = props.get("y", 0.0) * 12
        w = props.get("width", 0.0) * 12
        d = props.get("depth", 0.0) * 12
        if w <= 0 or d <= 0:
            continue
        slab_result = make_floor_slab(
            [Vector(x, y, 0), Vector(x + w, y, 0), Vector(x + w, y + d, 0), Vector(x, y + d, 0)], thickness=6.0)
        if slab_result.ok:
            shapes.append(slab_result.shape)
        height = 108.0
        for start, end in [
            (Vector(x, y, 0), Vector(x + w, y, 0)),
            (Vector(x + w, y, 0), Vector(x + w, y + d, 0)),
            (Vector(x + w, y + d, 0), Vector(x, y + d, 0)),
            (Vector(x, y + d, 0), Vector(x, y, 0)),
        ]:
            wall_result = make_wall(start, end, height=height, thickness=5.5)
            if wall_result.ok:
                shapes.append(wall_result.shape)
    path = tempfile.mktemp(suffix=".glb", prefix="archi_")
    export_shapes_to_gltf(shapes, output_path=path)
    return {"success": True, "format": "glb", "path": path}

@mcp.tool()
def export_to_svg(level: int = 0) -> dict:
    """Export 2D floor plan as SVG. Returns SVG string inline."""
    return export_svg(state, level)

@mcp.tool()
def export_to_dxf(level: int = 0) -> dict:
    """Export 2D floor plan as DXF file for contractor handoff."""
    return export_dxf(state, level)

@mcp.tool()
def export_to_gltf() -> dict:
    """Export 3D model as glTF binary (.glb) for browser viewing."""
    return export_gltf(state)
