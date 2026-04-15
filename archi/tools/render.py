# archi/tools/render.py
"""render_* MCP tools — AI image generation for interior design."""
from __future__ import annotations

from archi.render import (
    RENDER_DIR, STYLES, DEFAULT_STYLE,
    compose_prompt, generate_image, _make_filename, _ensure_render_dir,
)
from archi.server import BuildingState, mcp, state


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
