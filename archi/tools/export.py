"""export_* MCP tools — file export operations."""

from __future__ import annotations

import tempfile

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

from archi.export.dxf import export_floor_plan as dxf_export
from archi.export.gltf import export_shapes_to_gltf
from archi.export.svg import render_floor_plan
from archi.graph.model import NodeType
from archi.kernel.isolation import safe_boolean_cut
from archi.kernel.primitives import make_floor_slab, make_wall
from archi.kernel.vector import Vector
from archi.server import BuildingState, mcp, state
from archi.units import feet_to_inches


def export_svg(s: BuildingState, level: int = 0) -> dict:
    svg = render_floor_plan(s.graph, level=level)
    return {"success": True, "format": "svg", "content": svg}


def export_dxf(s: BuildingState, level: int = 0) -> dict:
    path = tempfile.mktemp(suffix=".dxf", prefix="archi_")
    dxf_export(s.graph, level=level, output_path=path)
    return {"success": True, "format": "dxf", "path": path}


def _floor_elevations(s: BuildingState) -> dict[int, float]:
    floors = sorted(
        (
            int(props.get("level", 0)),
            float(props.get("floor_to_floor_height", 9.0)),
        )
        for props in s.graph.get_all_nodes(NodeType.FLOOR).values()
    )
    elevations: dict[int, float] = {}
    z_ft = 0.0
    for level, height_ft in floors:
        elevations[level] = z_ft
        z_ft += height_ft
    return elevations


def _opening_shapes_for_wall(s: BuildingState, wall_id: str, wall: dict, z_in: float) -> list:
    cutters = []
    thickness = float(wall.get("thickness_in", 5.5))
    orientation = wall.get("orientation")
    sx = feet_to_inches(float(wall.get("start_x", 0.0)))
    sy = feet_to_inches(float(wall.get("start_y", 0.0)))

    for edge in s.graph.get_edges(wall_id):
        if edge.get("edge_type") != "contains":
            continue
        opening_id = edge.get("target")
        try:
            opening = s.graph.get_node(opening_id)
        except KeyError:
            continue
        if opening.get("type") != NodeType.OPENING:
            continue
        offset = feet_to_inches(float(opening.get("wall_offset_ft", 0.0)))
        width = float(opening.get("width", 0.0))
        height = float(opening.get("height", 0.0))
        sill = float(opening.get("sill_height", 0.0))
        if width <= 0 or height <= 0:
            continue

        if orientation == "h":
            origin = Vector(sx + offset, sy - thickness, z_in + sill)
            cutter = BRepPrimAPI_MakeBox(origin.to_pnt(), width, thickness * 3.0, height).Shape()
        else:
            origin = Vector(sx - thickness, sy + offset, z_in + sill)
            cutter = BRepPrimAPI_MakeBox(origin.to_pnt(), thickness * 3.0, width, height).Shape()
        cutters.append((opening_id, cutter))
    return cutters


def export_gltf(s: BuildingState) -> dict:
    shapes = []
    warnings: list[dict] = []
    elevations = _floor_elevations(s)

    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    for floor_id, floor_props in floors.items():
        level = int(floor_props.get("level", 0))
        z_in = feet_to_inches(elevations.get(level, 0.0))
        for room_id in s.graph.get_rooms_on_floor(floor_id):
            props = s.graph.get_node(room_id)
            x = feet_to_inches(float(props.get("x", 0.0)))
            y = feet_to_inches(float(props.get("y", 0.0)))
            w = feet_to_inches(float(props.get("width", 0.0)))
            d = feet_to_inches(float(props.get("depth", 0.0)))
            if w <= 0 or d <= 0:
                continue
            slab_result = make_floor_slab(
                [
                    Vector(x, y, z_in),
                    Vector(x + w, y, z_in),
                    Vector(x + w, y + d, z_in),
                    Vector(x, y + d, z_in),
                ],
                thickness=6.0,
            )
            if slab_result.ok:
                shapes.append(slab_result.shape)

    for wall_id, wall in s.graph.get_all_nodes(NodeType.WALL).items():
        if not wall.get("derived"):
            continue
        level = int(wall.get("level", 0))
        z_in = feet_to_inches(elevations.get(level, 0.0))
        floor_height = 9.0
        for props in floors.values():
            if int(props.get("level", 0)) == level:
                floor_height = float(props.get("floor_to_floor_height", 9.0))
                break
        start = Vector(
            feet_to_inches(float(wall.get("start_x", 0.0))),
            feet_to_inches(float(wall.get("start_y", 0.0))),
            z_in,
        )
        end = Vector(
            feet_to_inches(float(wall.get("end_x", 0.0))),
            feet_to_inches(float(wall.get("end_y", 0.0))),
            z_in,
        )
        wall_result = make_wall(
            start,
            end,
            height=feet_to_inches(floor_height),
            thickness=float(wall.get("thickness_in", 5.5)),
        )
        if not wall_result.ok:
            warnings.append({"wall_id": wall_id, "reason": wall_result.diagnostics.get("reason", "wall build failed")})
            continue

        wall_shape = wall_result.shape
        for opening_id, cutter in _opening_shapes_for_wall(s, wall_id, wall, z_in):
            cut = safe_boolean_cut(wall_shape, cutter)
            if cut.ok:
                wall_shape = cut.shape
            else:
                warnings.append({
                    "wall_id": wall_id,
                    "opening_id": opening_id,
                    "reason": cut.diagnostics.get("reason", "opening cut failed"),
                })
        shapes.append(wall_shape)

    path = tempfile.mktemp(suffix=".glb", prefix="archi_")
    export_shapes_to_gltf(shapes, output_path=path)
    return {
        "success": True,
        "format": "glb",
        "path": path,
        "canonical_wall_count": sum(1 for p in s.graph.get_all_nodes(NodeType.WALL).values() if p.get("derived")),
        "geometry_warnings": warnings,
    }


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
    """Export canonical 3D walls/slabs as glTF, cutting bound openings safely."""
    return export_gltf(state)
