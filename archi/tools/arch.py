"""arch_* MCP tools — structural design operations.

Returns Pydantic models defined in `archi.types`. FastMCP serializes each as
both `content` (human-readable text via __str__) and `structuredContent`
(typed JSON). Agents read fields like `result.building_id` directly without
parsing dict keys.
"""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import Field

from archi.graph.model import NodeType, OpeningType, RoomType
from archi.server import BuildingState, mcp, state
from archi.types import (
    BuildingCreated,
    FloorAdded,
    OpeningAdded,
    OpeningTypeStr,
    RoomAdded,
    RoomRemoved,
    RoomTypeStr,
    Violation,
)


def _envelope_kwargs(s: BuildingState, level: int = 0) -> dict:
    """Common kwargs for the SVG + violations baseline."""
    from archi.export.svg import render_floor_plan
    return {
        "svg": render_floor_plan(s.graph, level=level),
        "violations": [Violation.model_validate(v) for v in s.validator.get_violations()],
        "violation_counts": s.validator.get_violation_counts(),
        "layout": s._layout_meta.get(level, {}),
    }


def _create_building(
    s: BuildingState,
    lot_width: float,
    lot_depth: float,
    setbacks: dict,
    orientation: float,
    stories: int,
) -> BuildingCreated:
    with s.graph.transaction() as tx:
        building_id = s.graph.add_node(
            NodeType.BUILDING,
            lot_width=lot_width,
            lot_depth=lot_depth,
            setbacks=setbacks,
            orientation=orientation,
            stories=stories,
            length_unit="ft",
        )
        tx.commit()
    return BuildingCreated(success=True, building_id=building_id, **_envelope_kwargs(s, level=0))


def _add_floor(s: BuildingState, level: int, height: float) -> FloorAdded:
    buildings = s.graph.get_all_nodes(NodeType.BUILDING)
    if not buildings:
        return FloorAdded(success=False, error="No building exists. Call arch_create_building first.")
    for _fid, props in s.graph.get_all_nodes(NodeType.FLOOR).items():
        if props.get("level") == level:
            return FloorAdded(success=False, error=f"Floor level {level} already exists")

    building_id = next(iter(buildings))
    with s.graph.transaction() as tx:
        floor_id = s.graph.add_node(
            NodeType.FLOOR,
            level=level,
            floor_to_floor_height=height,
            length_unit="ft",
        )
        s.graph.add_edge(building_id, floor_id, "contains")
        tx.commit()
    return FloorAdded(success=True, floor_id=floor_id, level=level, **_envelope_kwargs(s, level=level))


def _validate_adjacent_rooms(s: BuildingState, adjacent_to: Optional[list[str]], level: int) -> str | None:
    for adj_id in adjacent_to or []:
        try:
            props = s.graph.get_node(adj_id)
        except KeyError:
            return f"Adjacent room '{adj_id}' not found"
        if props.get("type") != NodeType.ROOM:
            return f"Adjacent node '{adj_id}' is not a room"
        if props.get("level") != level:
            return f"Adjacent room '{adj_id}' is on level {props.get('level')}, not level {level}"
    return None


def _add_room(
    s: BuildingState,
    room_type: str,
    level: int,
    area: float,
    adjacent_to: Optional[list[str]],
    preferred_width: Optional[float],
    preferred_depth: Optional[float],
) -> RoomAdded:
    try:
        rt = RoomType(room_type)
    except ValueError:
        return RoomAdded(success=False, error=f"Unknown room type: {room_type}")

    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    floor_id = None
    for fid, fprops in floors.items():
        if fprops.get("level") == level:
            floor_id = fid
            break
    if floor_id is None:
        return RoomAdded(success=False, error=f"No floor at level {level}. Call arch_add_floor first.")

    adjacency_error = _validate_adjacent_rooms(s, adjacent_to, level)
    if adjacency_error:
        return RoomAdded(success=False, error=adjacency_error)

    props: dict = {
        "room_type": rt,
        "level": level,
        "target_area": area,
        "area": area,
        "length_unit": "ft",
        "area_unit": "sqft",
    }
    if preferred_width is not None:
        props["preferred_width"] = preferred_width
    if preferred_depth is not None:
        props["preferred_depth"] = preferred_depth

    with s.graph.transaction() as tx:
        room_id = s.graph.add_node(NodeType.ROOM, **props)
        s.graph.add_edge(floor_id, room_id, "contains")
        for adj_id in adjacent_to or []:
            s.graph.add_edge(room_id, adj_id, "adjacent_to")
        layout = s.run_layout(level=level)
        if room_id not in layout:
            return RoomAdded(success=False, error="Layout solver could not place the room")
        tx.commit()

    return RoomAdded(
        success=True,
        room_id=room_id,
        room_type=room_type,
        level=level,
        **_envelope_kwargs(s, level=level),
    )


def _remove_room(s: BuildingState, room_id: str) -> RoomRemoved:
    try:
        props = s.graph.get_node(room_id)
    except KeyError:
        return RoomRemoved(success=False, error=f"Room '{room_id}' not found")
    if props.get("type") != NodeType.ROOM:
        return RoomRemoved(success=False, error=f"Node '{room_id}' is not a room")
    level = props.get("level", 0)

    with s.graph.transaction() as tx:
        s.graph.remove_node(room_id)
        s.run_layout(level=level)
        tx.commit()
    return RoomRemoved(success=True, removed=room_id, **_envelope_kwargs(s, level=level))


def _room_for_opening(s: BuildingState, room_id: str) -> tuple[dict | None, str | None]:
    try:
        props = s.graph.get_node(room_id)
    except KeyError:
        return None, f"Room '{room_id}' not found"
    if props.get("type") != NodeType.ROOM:
        return None, f"Node '{room_id}' is not a room"
    return props, None


def _add_opening(
    s: BuildingState,
    opening_type: str,
    width: float,
    height: float,
    room_a: str,
    room_b: Optional[str],
    exterior: bool,
) -> OpeningAdded:
    try:
        ot = OpeningType(opening_type)
    except ValueError:
        return OpeningAdded(success=False, error=f"Unknown opening type: {opening_type}")

    room_a_props, error = _room_for_opening(s, room_a)
    if error:
        return OpeningAdded(success=False, error=error)
    if room_b:
        room_b_props, error = _room_for_opening(s, room_b)
        if error:
            return OpeningAdded(success=False, error=error)
        if room_b == room_a:
            return OpeningAdded(success=False, error="An opening cannot connect a room to itself")
        if room_b_props.get("level") != room_a_props.get("level"):
            return OpeningAdded(success=False, error="Opening rooms must be on the same level")

    with s.graph.transaction() as tx:
        opening_id = s.graph.add_node(
            NodeType.OPENING,
            opening_type=ot,
            width=width,
            height=height,
            exterior=exterior,
            dimension_unit="in",
        )
        s.graph.add_edge(opening_id, room_a, "connects")
        if room_b:
            s.graph.add_edge(opening_id, room_b, "connects")
        tx.commit()

    level = room_a_props.get("level", 0)
    return OpeningAdded(
        success=True,
        opening_id=opening_id,
        opening_type=opening_type,
        room_a=room_a,
        room_b=room_b,
        **_envelope_kwargs(s, level=level),
    )


@mcp.tool()
def arch_create_building(
    lot_width: Annotated[float, Field(gt=0, description="Lot width in feet")],
    lot_depth: Annotated[float, Field(gt=0, description="Lot depth in feet")],
    setbacks_front: Annotated[float, Field(ge=0, description="Front setback in feet")] = 25,
    setbacks_back: Annotated[float, Field(ge=0, description="Back setback in feet")] = 20,
    setbacks_left: Annotated[float, Field(ge=0, description="Left setback in feet")] = 10,
    setbacks_right: Annotated[float, Field(ge=0, description="Right setback in feet")] = 10,
    orientation: Annotated[float, Field(description="Building orientation in degrees from north")] = 0.0,
    stories: Annotated[int, Field(ge=1, le=10, description="Number of stories")] = 1,
) -> BuildingCreated:
    """Initialize a building on a lot with dimensions and setbacks."""
    setbacks = {
        "front": setbacks_front,
        "back": setbacks_back,
        "left": setbacks_left,
        "right": setbacks_right,
    }
    return _create_building(state, lot_width, lot_depth, setbacks, orientation, stories)


@mcp.tool()
def arch_add_floor(
    level: Annotated[int, Field(ge=0, description="Floor level (0 = ground)")],
    height: Annotated[float, Field(gt=0, description="Floor-to-floor height in feet")] = 9.0,
) -> FloorAdded:
    """Add a floor/story to the building."""
    return _add_floor(state, level, height)


@mcp.tool()
def arch_add_room(
    room_type: Annotated[RoomTypeStr, Field(description="Room type from the fixed taxonomy")],
    level: Annotated[int, Field(ge=0, description="Floor level the room belongs to")] = 0,
    area: Annotated[float, Field(gt=0, description="Target floor area in sq ft")] = 100.0,
    adjacent_to: Annotated[Optional[list[str]], Field(default=None, description="Room IDs this room must be adjacent to")] = None,
    preferred_width: Annotated[Optional[float], Field(default=None, gt=0, description="Preferred X dimension in feet")] = None,
    preferred_depth: Annotated[Optional[float], Field(default=None, gt=0, description="Preferred Y dimension in feet")] = None,
) -> RoomAdded:
    """Add a room and refine the floor layout against graph constraints."""
    return _add_room(state, room_type, level, area, adjacent_to, preferred_width, preferred_depth)


@mcp.tool()
def arch_remove_room(
    room_id: Annotated[str, Field(description="ID of the room to remove")],
) -> RoomRemoved:
    """Remove a room and its connections atomically."""
    return _remove_room(state, room_id)


@mcp.tool()
def arch_add_opening(
    opening_type: Annotated[OpeningTypeStr, Field(description="Opening type from the fixed taxonomy")],
    width: Annotated[float, Field(gt=0, description="Opening width in inches")],
    height: Annotated[float, Field(gt=0, description="Opening height in inches")],
    room_a: Annotated[str, Field(description="Room ID on one side of the opening")],
    room_b: Annotated[Optional[str], Field(default=None, description="Room ID on the other side, or omit for exterior")] = None,
    exterior: Annotated[bool, Field(description="True if this opening leads outside")] = False,
) -> OpeningAdded:
    """Add a door/window/archway between rooms or to the exterior."""
    return _add_opening(state, opening_type, width, height, room_a, room_b, exterior)


# In-process service helpers retained for tests and non-MCP callers.
def create_building(s: BuildingState, lot_width: float, lot_depth: float,
                    setbacks: dict | None = None, orientation: float = 0.0,
                    stories: int = 1) -> dict:
    setbacks = setbacks or {"front": 25, "back": 20, "left": 10, "right": 10}
    return _create_building(s, lot_width, lot_depth, setbacks, orientation, stories).model_dump()


def add_floor(s: BuildingState, level: int, height: float = 9.0) -> dict:
    return _add_floor(s, level, height).model_dump()


def add_room(s: BuildingState, room_type: str, level: int = 0, area: float = 100.0,
             adjacent_to: Optional[list[str]] = None, preferred_width: Optional[float] = None,
             preferred_depth: Optional[float] = None) -> dict:
    return _add_room(s, room_type, level, area, adjacent_to, preferred_width, preferred_depth).model_dump()


def remove_room(s: BuildingState, room_id: str) -> dict:
    return _remove_room(s, room_id).model_dump()


def add_opening(s: BuildingState, opening_type: str, width: float, height: float,
                room_a: str, room_b: Optional[str] = None, exterior: bool = False) -> dict:
    return _add_opening(s, opening_type, width, height, room_a, room_b, exterior).model_dump()
