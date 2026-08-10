"""interior_* MCP tools — furniture placement and interior design."""

from __future__ import annotations

from archi.graph.model import FurnitureType, NodeType
from archi.kernel.backend import OCPBackend
from archi.kernel.furniture import FURNITURE_DEFAULTS
from archi.kernel.isolation import safe_boolean_common
from archi.kernel.vector import Vector
from archi.server import BuildingState, mcp, state
from archi.units import feet_to_inches

_backend = OCPBackend()


def _furniture_shape(x: float, y: float, width: float, depth: float, height: float):
    return _backend.make_slab(
        [
            Vector(x, y, 0),
            Vector(x + width, y, 0),
            Vector(x + width, y + depth, 0),
            Vector(x, y + depth, 0),
        ],
        height,
    )


def _placement_error(s: BuildingState, room_id: str, x: float, y: float,
                     width: float, depth: float, height: float) -> str | None:
    room = s.graph.get_node(room_id)
    room_width = feet_to_inches(float(room.get("width", 0.0)))
    room_depth = feet_to_inches(float(room.get("depth", 0.0)))
    if x < 0 or y < 0:
        return "Furniture position must be inside the room (x/y >= 0)"
    if x + width > room_width + 1e-6 or y + depth > room_depth + 1e-6:
        return (
            f"Furniture footprint {width:.1f}×{depth:.1f}in at ({x:.1f}, {y:.1f}) "
            f"does not fit inside room {room_width:.1f}×{room_depth:.1f}in"
        )

    candidate = _furniture_shape(x, y, width, depth, height)
    for existing_id in s.graph.get_furniture_in_room(room_id):
        props = s.graph.get_node(existing_id)
        existing = _furniture_shape(
            float(props.get("x", 0.0)),
            float(props.get("y", 0.0)),
            float(props.get("width", 0.0)),
            float(props.get("depth", 0.0)),
            float(props.get("height", 0.0)),
        )
        common = safe_boolean_common(candidate, existing)
        if not common.ok:
            reason = common.diagnostics.get("reason", "intersection check failed")
            return f"Could not safely validate furniture interference: {reason}"
        if float(common.volume or 0.0) > 0.01:
            return f"Furniture collides with existing item '{existing_id}'"
    return None


def _clearance_warnings(s: BuildingState, room_id: str, x: float, y: float,
                        width: float, depth: float, clearance: dict) -> list[dict]:
    """Conservative axis-aligned clearance screening.

    Furniture orientation/front direction is not yet modeled, so this uses the
    smaller declared front/side clearance as a neutral perimeter screening
    distance and reports warnings rather than claiming full ergonomic compliance.
    """
    required = float(min(clearance.get("front", 0), clearance.get("sides", 0)))
    if required <= 0:
        return []
    room = s.graph.get_node(room_id)
    room_width = feet_to_inches(float(room.get("width", 0.0)))
    room_depth = feet_to_inches(float(room.get("depth", 0.0)))
    distances = {
        "left_wall": x,
        "right_wall": room_width - (x + width),
        "top_wall": y,
        "bottom_wall": room_depth - (y + depth),
    }
    return [
        {"obstacle": name, "distance": distance, "required_screening": required}
        for name, distance in distances.items()
        if distance < required
    ]


def place_furniture(
    s: BuildingState,
    room_id: str,
    furniture_type: str,
    x: float,
    y: float,
    width: float | None = None,
    depth: float | None = None,
    height: float | None = None,
    style: str = "modern",
) -> dict:
    try:
        room_props = s.graph.get_node(room_id)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}
    if room_props.get("type") != NodeType.ROOM:
        return {"success": False, "error": f"Node '{room_id}' is not a room"}

    defaults = FURNITURE_DEFAULTS.get(furniture_type, {})
    w = width if width is not None else defaults.get("width", 24.0)
    d = depth if depth is not None else defaults.get("depth", 24.0)
    h = height if height is not None else defaults.get("height", 24.0)
    if w <= 0 or d <= 0 or h <= 0:
        return {"success": False, "error": "Furniture dimensions must be positive"}

    error = _placement_error(s, room_id, x, y, w, d, h)
    if error:
        return {"success": False, "error": error}

    try:
        ft = FurnitureType(furniture_type)
    except ValueError:
        ft = None
    props: dict = {
        "width": w,
        "depth": d,
        "height": h,
        "x": x,
        "y": y,
        "style": style,
        "dimension_unit": "in",
    }
    if ft:
        props["furniture_type"] = ft

    clearance = defaults.get("clearance", {"front": 12, "sides": 6})
    warnings = _clearance_warnings(s, room_id, x, y, w, d, clearance)
    level = room_props.get("level", 0)
    with s.graph.transaction() as tx:
        furniture_id = s.graph.add_node(NodeType.FURNITURE, **props)
        s.graph.add_edge(room_id, furniture_id, "contains")
        tx.commit()
    return s.respond(
        {
            "success": True,
            "furniture_id": furniture_id,
            "clearance": clearance,
            "clearance_warnings": warnings,
            "interference_checked": True,
        },
        level=level,
    )


def remove_furniture(s: BuildingState, furniture_id: str) -> dict:
    try:
        props = s.graph.get_node(furniture_id)
    except KeyError:
        return {"success": False, "error": f"Furniture '{furniture_id}' not found"}
    if props.get("type") != NodeType.FURNITURE:
        return {"success": False, "error": f"Node '{furniture_id}' is not furniture"}
    with s.graph.transaction() as tx:
        s.graph.remove_node(furniture_id)
        tx.commit()
    return s.respond({"success": True, "removed": furniture_id})


@mcp.tool()
def interior_place_furniture(
    room_id: str,
    furniture_type: str,
    x: float,
    y: float,
    width: float | None = None,
    depth: float | None = None,
    height: float | None = None,
    style: str = "modern",
) -> dict:
    """Place furniture in inches, rejecting out-of-room or colliding geometry."""
    return place_furniture(state, room_id, furniture_type, x, y, width, depth, height, style)


@mcp.tool()
def interior_remove_furniture(furniture_id: str) -> dict:
    """Remove a placed furniture piece."""
    return remove_furniture(state, furniture_id)
