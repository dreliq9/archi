"""interior_* MCP tools — furniture placement and interior design."""
from __future__ import annotations
from archi.graph.model import FurnitureType, NodeType
from archi.kernel.furniture import FURNITURE_DEFAULTS
from archi.server import BuildingState, mcp, state

def place_furniture(s: BuildingState, room_id: str, furniture_type: str, x: float, y: float,
                     width: float | None = None, depth: float | None = None,
                     height: float | None = None, style: str = "modern") -> dict:
    try:
        s.graph.get_node(room_id)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}
    defaults = FURNITURE_DEFAULTS.get(furniture_type, {})
    w = width or defaults.get("width", 24.0)
    d = depth or defaults.get("depth", 24.0)
    h = height or defaults.get("height", 24.0)
    try:
        ft = FurnitureType(furniture_type)
    except ValueError:
        ft = None
    props: dict = {"width": w, "depth": d, "height": h, "x": x, "y": y, "style": style}
    if ft: props["furniture_type"] = ft
    furniture_id = s.graph.add_node(NodeType.FURNITURE, **props)
    s.graph.add_edge(room_id, furniture_id, "contains")
    room_props = s.graph.get_node(room_id)
    level = room_props.get("level", 0)
    return s.respond({"success": True, "furniture_id": furniture_id,
                       "clearance": defaults.get("clearance", {"front": 12, "sides": 6})}, level=level)

def remove_furniture(s: BuildingState, furniture_id: str) -> dict:
    try:
        s.graph.remove_node(furniture_id)
        return s.respond({"success": True, "removed": furniture_id})
    except KeyError:
        return {"success": False, "error": f"Furniture '{furniture_id}' not found"}

@mcp.tool()
def interior_place_furniture(room_id: str, furniture_type: str, x: float, y: float,
    width: float | None = None, depth: float | None = None, height: float | None = None,
    style: str = "modern") -> dict:
    """Place a parametric furniture piece in a room. Position in inches relative to room origin."""
    return place_furniture(state, room_id, furniture_type, x, y, width, depth, height, style)

@mcp.tool()
def interior_remove_furniture(furniture_id: str) -> dict:
    """Remove a placed furniture piece."""
    return remove_furniture(state, furniture_id)
