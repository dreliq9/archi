"""arch_* MCP tools — structural design operations."""

from __future__ import annotations
from archi.graph.model import NodeType, OpeningType, RoomType
from archi.server import BuildingState, mcp, state


def create_building(s: BuildingState, lot_width: float, lot_depth: float,
                     setbacks: dict | None = None, orientation: float = 0.0, stories: int = 1) -> dict:
    if setbacks is None:
        setbacks = {"front": 25, "back": 20, "left": 10, "right": 10}
    building_id = s.graph.add_node(NodeType.BUILDING, lot_width=lot_width, lot_depth=lot_depth,
                                    setbacks=setbacks, orientation=orientation, stories=stories)
    return s.respond({"success": True, "building_id": building_id})


def add_floor(s: BuildingState, level: int, height: float = 9.0) -> dict:
    buildings = s.graph.get_all_nodes(NodeType.BUILDING)
    if not buildings:
        return {"success": False, "error": "No building exists. Call create_building first."}
    building_id = next(iter(buildings))
    floor_id = s.graph.add_node(NodeType.FLOOR, level=level, floor_to_floor_height=height)
    s.graph.add_edge(building_id, floor_id, "contains")
    return s.respond({"success": True, "floor_id": floor_id}, level=level)


def add_room(s: BuildingState, room_type: str, level: int = 0, area: float = 100.0,
              adjacent_to: list[str] | None = None, preferred_width: float | None = None,
              preferred_depth: float | None = None) -> dict:
    try:
        rt = RoomType(room_type)
    except ValueError:
        return {"success": False, "error": f"Unknown room type: {room_type}"}
    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    floor_id = None
    for fid, fprops in floors.items():
        if fprops.get("level") == level:
            floor_id = fid
            break
    if floor_id is None:
        return {"success": False, "error": f"No floor at level {level}. Call add_floor first."}
    props: dict = {"room_type": rt, "level": level, "area": area}
    if preferred_width:
        props["width"] = preferred_width
    if preferred_depth:
        props["depth"] = preferred_depth
    room_id = s.graph.add_node(NodeType.ROOM, **props)
    s.graph.add_edge(floor_id, room_id, "contains")
    if adjacent_to:
        for adj_id in adjacent_to:
            try:
                s.graph.add_edge(room_id, adj_id, "adjacent_to")
            except KeyError:
                pass
    s.run_layout(level=level)
    return s.respond({"success": True, "room_id": room_id}, level=level)


def remove_room(s: BuildingState, room_id: str) -> dict:
    try:
        props = s.graph.get_node(room_id)
        level = props.get("level", 0)
        s.graph.remove_node(room_id)
        s.run_layout(level=level)
        return s.respond({"success": True, "removed": room_id}, level=level)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}


def add_opening(s: BuildingState, opening_type: str, width: float, height: float,
                 room_a: str, room_b: str | None = None, exterior: bool = False) -> dict:
    try:
        ot = OpeningType(opening_type)
    except ValueError:
        return {"success": False, "error": f"Unknown opening type: {opening_type}"}
    opening_id = s.graph.add_node(NodeType.OPENING, opening_type=ot, width=width, height=height, exterior=exterior)
    try:
        s.graph.add_edge(opening_id, room_a, "connects")
        if room_b:
            s.graph.add_edge(opening_id, room_b, "connects")
    except KeyError as e:
        return {"success": False, "error": f"Room not found: {e}"}
    room_props = s.graph.get_node(room_a)
    level = room_props.get("level", 0)
    return s.respond({"success": True, "opening_id": opening_id}, level=level)


# MCP tool registrations
@mcp.tool()
def arch_create_building(lot_width: float, lot_depth: float, setbacks_front: float = 25,
    setbacks_back: float = 20, setbacks_left: float = 10, setbacks_right: float = 10,
    orientation: float = 0.0, stories: int = 1) -> dict:
    """Initialize a building on a lot with dimensions and setbacks."""
    setbacks = {"front": setbacks_front, "back": setbacks_back, "left": setbacks_left, "right": setbacks_right}
    return create_building(state, lot_width, lot_depth, setbacks, orientation, stories)


@mcp.tool()
def arch_add_floor(level: int, height: float = 9.0) -> dict:
    """Add a floor/story to the building."""
    return add_floor(state, level, height)


@mcp.tool()
def arch_add_room(room_type: str, level: int = 0, area: float = 100.0,
    adjacent_to: list[str] | None = None, preferred_width: float | None = None,
    preferred_depth: float | None = None) -> dict:
    """Add a room by type and constraints. Triggers automatic layout."""
    return add_room(state, room_type, level, area, adjacent_to, preferred_width, preferred_depth)


@mcp.tool()
def arch_remove_room(room_id: str) -> dict:
    """Remove a room and its connections."""
    return remove_room(state, room_id)


@mcp.tool()
def arch_add_opening(opening_type: str, width: float, height: float, room_a: str,
    room_b: str | None = None, exterior: bool = False) -> dict:
    """Add a door/window/archway. Types: door, window, archway, sliding_door, pocket_door, garage_door."""
    return add_opening(state, opening_type, width, height, room_a, room_b, exterior)
