"""SVG floor plan renderer — primary visual format for AI-in-the-loop preview."""

from __future__ import annotations
import svgwrite
from archi.graph.model import BuildingGraph, NodeType, RoomType, FurnitureType

SCALE = 20  # 1 foot = 20 SVG pixels
MARGIN = 20

_ROOM_COLORS: dict[RoomType, str] = {
    RoomType.KITCHEN:     "#FFE4B5",
    RoomType.LIVING_ROOM: "#E0F0E0",
    RoomType.DINING_ROOM: "#FFEFD5",
    RoomType.BEDROOM:     "#E0E8F0",
    RoomType.BATHROOM:    "#E0F0F8",
    RoomType.HALF_BATH:   "#E0F0F8",
    RoomType.CLOSET:      "#F0E0F0",
    RoomType.HALLWAY:     "#F0F0F0",
    RoomType.GARAGE:      "#E8E8E0",
    RoomType.LAUNDRY:     "#F0E8E0",
    RoomType.OFFICE:      "#E8F0E0",
    RoomType.MUDROOM:     "#E8E0D0",
    RoomType.PANTRY:      "#F8F0E0",
    RoomType.FOYER:       "#F0F0E0",
    RoomType.UTILITY:     "#E0E0E0",
}
_DEFAULT_ROOM_COLOR = "#F5F5F5"
_FURNITURE_COLOR = "#C0A080"
_WALL_COLOR = "#333333"

def render_floor_plan(graph: BuildingGraph, level: int = 0, title: str = "") -> str:
    rooms: list[tuple[str, dict]] = []
    floors = graph.get_all_nodes(NodeType.FLOOR)
    for floor_id, floor_props in floors.items():
        if floor_props.get("level") != level:
            continue
        for room_id in graph.get_rooms_on_floor(floor_id):
            rooms.append((room_id, graph.get_node(room_id)))

    max_x = max_y = 0.0
    for _, props in rooms:
        max_x = max(max_x, props.get("x", 0.0) + props.get("width", 0.0))
        max_y = max(max_y, props.get("y", 0.0) + props.get("depth", 0.0))
    if max_x == 0 and max_y == 0:
        max_x = max_y = 10

    canvas_w = int(max_x * SCALE) + MARGIN * 2
    canvas_h = int(max_y * SCALE) + MARGIN * 2
    dwg = svgwrite.Drawing(size=(f"{canvas_w}px", f"{canvas_h}px"))
    dwg.viewbox(0, 0, canvas_w, canvas_h)
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_w, canvas_h), fill="white"))

    for room_id, props in rooms:
        rx = props.get("x", 0.0) * SCALE + MARGIN
        ry = props.get("y", 0.0) * SCALE + MARGIN
        rw = props.get("width", 0.0) * SCALE
        rd = props.get("depth", 0.0) * SCALE
        if rw <= 0 or rd <= 0:
            continue
        room_type = props.get("room_type")
        fill = _ROOM_COLORS.get(room_type, _DEFAULT_ROOM_COLOR) if room_type else _DEFAULT_ROOM_COLOR
        dwg.add(dwg.rect(insert=(rx, ry), size=(rw, rd), fill=fill, stroke=_WALL_COLOR, stroke_width=2))
        label = room_type.value.replace("_", " ").title() if room_type else "Room"
        area = props.get("area", 0.0)
        cx, cy = rx + rw / 2, ry + rd / 2
        dwg.add(dwg.text(label, insert=(cx, cy - 6), text_anchor="middle", font_size="11px", font_family="sans-serif", fill="#333"))
        dwg.add(dwg.text(f"{area:.0f} sqft", insert=(cx, cy + 10), text_anchor="middle", font_size="9px", font_family="sans-serif", fill="#666"))

        for furn_id in graph.get_furniture_in_room(room_id):
            fp = graph.get_node(furn_id)
            fx, fy = fp.get("x", 0.0), fp.get("y", 0.0)
            fw, fd = fp.get("width", 0.0), fp.get("depth", 0.0)
            if fw <= 0 or fd <= 0:
                continue
            dwg.add(dwg.rect(insert=(rx + fx/12.0*SCALE, ry + fy/12.0*SCALE),
                             size=(fw/12.0*SCALE, fd/12.0*SCALE),
                             fill=_FURNITURE_COLOR, fill_opacity=0.5, stroke="#8B7355", stroke_width=1))

    return dwg.tostring()
