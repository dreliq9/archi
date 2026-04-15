# archi/tools/render.py
"""render_* MCP tools — AI image generation for interior design."""
from __future__ import annotations

from collections import deque

from archi.render import (
    RENDER_DIR, STYLES, DEFAULT_STYLE,
    compose_prompt, generate_image, _make_filename, _ensure_render_dir,
)
from archi.server import BuildingState, mcp, state
from archi.graph.model import NodeType


# ---------------------------------------------------------------------------
# Core implementations (testable without MCP)
# ---------------------------------------------------------------------------

def render_room_impl(
    s: BuildingState,
    room_id: str,
    style: str = DEFAULT_STYLE,
    quality: str = "free",
) -> dict:
    try:
        props = s.graph.get_node(room_id)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}

    # Use saved style if no explicit style and room has one
    if style == DEFAULT_STYLE:
        style = props.get("render_style", DEFAULT_STYLE)

    room_type = props.get("room_type")
    room_name = room_type.value if room_type else "room"

    prompt = compose_prompt(s.graph, room_id, style=style)
    _ensure_render_dir()
    output_path = str(RENDER_DIR / _make_filename(room_name, style))

    result = generate_image(prompt=prompt, quality=quality, output_path=output_path)
    return {
        "success": result.success,
        "image_path": result.image_path,
        "image_url": result.image_url,
        "prompt_used": result.prompt_used,
        "estimated_cost": result.estimated_cost,
        "quality": result.quality,
        **({"error": result.error} if result.error else {}),
    }


def set_style_impl(s: BuildingState, room_id: str, style: str) -> dict:
    try:
        s.graph.get_node(room_id)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}
    if style not in STYLES:
        return {"success": False, "error": f"Unknown style '{style}'. Options: {', '.join(STYLES)}"}
    s.graph.update_node(room_id, render_style=style)
    return {"success": True, "room_id": room_id, "style": style}


def render_explore_impl(
    s: BuildingState,
    room_id: str,
    styles: list[str] | None = None,
    quality: str = "free",
) -> dict:
    try:
        s.graph.get_node(room_id)
    except KeyError:
        return {"success": False, "error": f"Room '{room_id}' not found"}

    if styles is None:
        styles = ["modern", "farmhouse", "mid-century", "scandinavian"]

    renders = []
    total_cost = 0.0
    for style in styles:
        result = render_room_impl(s, room_id, style=style, quality=quality)
        renders.append({
            "style": style,
            "image_path": result.get("image_path"),
            "image_url": result.get("image_url"),
            "estimated_cost": result.get("estimated_cost", 0.0),
        })
        total_cost += result.get("estimated_cost", 0.0)

    return {"success": True, "renders": renders, "total_cost": round(total_cost, 3)}


def render_showcase_impl(
    s: BuildingState,
    level: int = 0,
    style: str | None = None,
    quality: str = "free",
) -> dict:
    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    floor_id = None
    for fid, fprops in floors.items():
        if fprops.get("level") == level:
            floor_id = fid
            break
    if floor_id is None:
        return {"success": False, "error": f"No floor at level {level}"}

    room_ids = s.graph.get_rooms_on_floor(floor_id)
    if not room_ids:
        return {"success": False, "error": f"No rooms on level {level}"}

    renders = []
    total_cost = 0.0
    for rid in room_ids:
        props = s.graph.get_node(rid)
        room_style = style or props.get("render_style", DEFAULT_STYLE)
        room_type = props.get("room_type")
        result = render_room_impl(s, rid, style=room_style, quality=quality)
        renders.append({
            "room_id": rid,
            "room_type": room_type.value if room_type else None,
            "style": room_style,
            "image_path": result.get("image_path"),
            "image_url": result.get("image_url"),
            "estimated_cost": result.get("estimated_cost", 0.0),
        })
        total_cost += result.get("estimated_cost", 0.0)

    return {
        "success": True,
        "level": level,
        "room_count": len(renders),
        "renders": renders,
        "total_cost": round(total_cost, 3),
    }


def _find_walk_order(s: BuildingState, floor_id: str) -> list[str]:
    """BFS from the room with an exterior door, or first room if none."""
    room_ids = s.graph.get_rooms_on_floor(floor_id)
    if not room_ids:
        return []

    # Find room with exterior door
    start = None
    openings = s.graph.get_all_nodes(NodeType.OPENING)
    for oid, oprops in openings.items():
        if not oprops.get("exterior"):
            continue
        for edge in s.graph.get_edges(oid):
            if edge["edge_type"] == "connects" and edge["target"] in room_ids:
                start = edge["target"]
                break
        if start:
            break

    if start is None:
        start = room_ids[0]

    # BFS
    visited = set()
    order = []
    queue = deque([start])
    while queue:
        rid = queue.popleft()
        if rid in visited or rid not in room_ids:
            continue
        visited.add(rid)
        order.append(rid)
        for adj in s.graph.get_adjacent_rooms(rid):
            if adj not in visited and adj in room_ids:
                queue.append(adj)

    # Add any rooms not reachable via adjacency
    for rid in room_ids:
        if rid not in visited:
            order.append(rid)

    return order


def render_walkthrough_impl(
    s: BuildingState,
    level: int = 0,
    style: str | None = None,
    quality: str = "free",
) -> dict:
    floors = s.graph.get_all_nodes(NodeType.FLOOR)
    floor_id = None
    for fid, fprops in floors.items():
        if fprops.get("level") == level:
            floor_id = fid
            break
    if floor_id is None:
        return {"success": False, "error": f"No floor at level {level}"}

    walk_order = _find_walk_order(s, floor_id)
    if not walk_order:
        return {"success": False, "error": f"No rooms on level {level}"}

    renders = []
    total_cost = 0.0
    prev_room_name = None

    for rid in walk_order:
        props = s.graph.get_node(rid)
        room_style = style or props.get("render_style", DEFAULT_STYLE)
        room_type = props.get("room_type")
        room_name = room_type.value.replace("_", " ") if room_type else "room"

        prompt = compose_prompt(
            s.graph, rid, style=room_style,
            entering_from=prev_room_name,
        )
        _ensure_render_dir()
        output_path = str(RENDER_DIR / _make_filename(
            room_type.value if room_type else "room", room_style))

        result = generate_image(prompt=prompt, quality=quality, output_path=output_path)
        renders.append({
            "room_id": rid,
            "room_type": room_type.value if room_type else None,
            "style": room_style,
            "image_path": result.image_path,
            "image_url": result.image_url,
            "estimated_cost": result.estimated_cost,
        })
        total_cost += result.estimated_cost
        prev_room_name = room_name

    return {
        "success": True,
        "level": level,
        "walk_order": walk_order,
        "renders": renders,
        "total_cost": round(total_cost, 3),
    }


# ---------------------------------------------------------------------------
# MCP tool registrations
# ---------------------------------------------------------------------------

@mcp.tool()
def render_room(room_id: str, style: str = "modern", quality: str = "free") -> dict:
    """Generate a photorealistic render of a room. Quality: 'free' (default, no key), 'fast' or 'high' (requires FAL_KEY)."""
    return render_room_impl(state, room_id, style, quality)


@mcp.tool()
def render_set_style(room_id: str, style: str) -> dict:
    """Save a style preference on a room. Options: modern, farmhouse, mid-century, scandinavian, industrial, minimalist, traditional, bohemian."""
    return set_style_impl(state, room_id, style)


@mcp.tool()
def render_explore(room_id: str, styles: list[str] | None = None, quality: str = "free") -> dict:
    """Generate the same room in multiple styles for comparison. Defaults to 4 styles."""
    return render_explore_impl(state, room_id, styles, quality)


@mcp.tool()
def render_showcase(level: int = 0, style: str | None = None, quality: str = "free") -> dict:
    """Render every room on a floor — produces a complete set of interior renders."""
    return render_showcase_impl(state, level, style, quality)


@mcp.tool()
def render_walkthrough(level: int = 0, style: str | None = None, quality: str = "free") -> dict:
    """Render rooms in adjacency order as a visual walkthrough tour."""
    return render_walkthrough_impl(state, level, style, quality)
