"""query_* MCP tools — read state, topology, and compliance checks."""

from __future__ import annotations

from archi.export.svg import render_floor_plan
from archi.graph.model import NodeType
from archi.server import BuildingState, mcp, state


def get_plan(s: BuildingState, level: int = 0) -> dict:
    svg = render_floor_plan(s.graph, level=level)
    violations = s.validator.get_violations()
    return {"svg": svg, "violations": violations}


def get_room(s: BuildingState, room_id: str) -> dict:
    try:
        props = s.graph.get_node(room_id)
    except KeyError:
        return {"error": f"Room '{room_id}' not found"}
    room_type = props.get("room_type")
    furniture_ids = s.graph.get_furniture_in_room(room_id)
    adjacent_ids = s.graph.get_adjacent_rooms(room_id)
    violations = [v for v in s.validator.get_violations() if v.get("node_id") == room_id]
    wall_ids = [
        wall_id for wall_id, wall in s.graph.get_all_nodes(NodeType.WALL).items()
        if room_id in wall.get("room_ids", [])
    ]
    return {
        "room_id": room_id,
        "room_type": room_type.value if room_type else None,
        "area": props.get("area", 0.0),
        "target_area": props.get("target_area"),
        "width": props.get("width", 0.0),
        "depth": props.get("depth", 0.0),
        "x": props.get("x", 0.0),
        "y": props.get("y", 0.0),
        "level": props.get("level", 0),
        "furniture": furniture_ids,
        "adjacent_rooms": adjacent_ids,
        "walls": wall_ids,
        "violations": violations,
    }


def get_building(s: BuildingState) -> dict:
    buildings = s.graph.get_all_nodes(NodeType.BUILDING)
    if not buildings:
        return {"error": "No building exists"}
    bid, bprops = next(iter(buildings.items()))
    rooms = s.graph.get_all_nodes(NodeType.ROOM)
    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    walls = s.graph.get_all_nodes(NodeType.WALL)
    total_area = sum(p.get("area", 0.0) for p in rooms.values())
    return {
        "building_id": bid,
        "lot_width": bprops.get("lot_width", 0),
        "lot_depth": bprops.get("lot_depth", 0),
        "setbacks": bprops.get("setbacks", {}),
        "stories": len(floors),
        "room_count": len(rooms),
        "canonical_wall_count": sum(1 for p in walls.values() if p.get("derived")),
        "total_area": total_area,
        "violations": s.validator.get_violation_counts(),
    }


def get_topology(s: BuildingState, level: int = 0) -> dict:
    walls = []
    for wall_id, props in s.graph.get_all_nodes(NodeType.WALL).items():
        if props.get("level") != level or not props.get("derived"):
            continue
        opening_ids = [
            edge.get("target") for edge in s.graph.get_edges(wall_id)
            if edge.get("edge_type") == "contains"
            and s.graph.get_node(edge.get("target")).get("type") == NodeType.OPENING
        ]
        walls.append({
            "wall_id": wall_id,
            "wall_key": props.get("wall_key"),
            "orientation": props.get("orientation"),
            "start": [props.get("start_x"), props.get("start_y")],
            "end": [props.get("end_x"), props.get("end_y")],
            "length_ft": props.get("length_ft"),
            "room_ids": props.get("room_ids", []),
            "exterior": props.get("exterior", False),
            "structural": props.get("structural", False),
            "material": props.get("material"),
            "thickness_in": props.get("thickness_in"),
            "opening_ids": opening_ids,
        })

    openings = []
    for opening_id, props in s.graph.get_all_nodes(NodeType.OPENING).items():
        connected_rooms = [
            edge.get("target") for edge in s.graph.get_edges(opening_id)
            if edge.get("edge_type") == "connects"
        ]
        if connected_rooms:
            try:
                if s.graph.get_node(connected_rooms[0]).get("level", 0) != level:
                    continue
            except KeyError:
                continue
        opening_type = props.get("opening_type")
        openings.append({
            "opening_id": opening_id,
            "opening_type": opening_type.value if opening_type else None,
            "room_ids": connected_rooms,
            "wall_id": props.get("wall_id"),
            "wall_key": props.get("wall_key"),
            "wall_offset_ft": props.get("wall_offset_ft"),
            "width_in": props.get("width"),
            "height_in": props.get("height"),
            "sill_height_in": props.get("sill_height"),
            "exterior": props.get("exterior", False),
            "topology_status": props.get("topology_status", "unresolved"),
        })

    unresolved = [o["opening_id"] for o in openings if o["topology_status"] != "bound"]
    return {
        "level": level,
        "walls": walls,
        "openings": openings,
        "wall_count": len(walls),
        "opening_count": len(openings),
        "unresolved_openings": unresolved,
    }


def check_code(s: BuildingState) -> dict:
    violations = s.validator.get_violations()
    counts = s.validator.get_violation_counts()
    return {"compliant": counts.get("error", 0) == 0, "violations": violations, "counts": counts}


def get_violations(s: BuildingState) -> dict:
    return {"violations": s.validator.get_violations(), "counts": s.validator.get_violation_counts()}


def list_rooms(s: BuildingState, level: int | None = None) -> dict:
    all_rooms = s.graph.get_all_nodes(NodeType.ROOM)
    rooms_list = []
    for rid, props in all_rooms.items():
        if level is not None and props.get("level") != level:
            continue
        room_type = props.get("room_type")
        rooms_list.append({
            "room_id": rid,
            "room_type": room_type.value if room_type else None,
            "area": props.get("area", 0.0),
            "target_area": props.get("target_area"),
            "width": props.get("width", 0.0),
            "depth": props.get("depth", 0.0),
            "level": props.get("level", 0),
        })
    return {"rooms": rooms_list}


@mcp.tool()
def query_get_plan(level: int = 0) -> dict:
    """Get current floor plan as SVG with violation overlay."""
    return get_plan(state, level)


@mcp.tool()
def query_get_room(room_id: str) -> dict:
    """Get room details including dimensions, furniture, walls, and violations."""
    return get_room(state, room_id)


@mcp.tool()
def query_get_building() -> dict:
    """Get building summary — rooms, areas, stories, and topology counts."""
    return get_building(state)


@mcp.tool()
def query_get_topology(level: int = 0) -> dict:
    """Inspect canonical shared/exterior walls and opening bindings for a floor."""
    return get_topology(state, level)


@mcp.tool()
def query_check_code() -> dict:
    """Run the implemented code checks and return all detected violations."""
    return check_code(state)


@mcp.tool()
def query_get_violations() -> dict:
    """Get current violation list (updated live after every change)."""
    return get_violations(state)


@mcp.tool()
def query_list_rooms(level: int | None = None) -> dict:
    """List all rooms with types and areas. Optionally filter by level."""
    return list_rooms(state, level)
