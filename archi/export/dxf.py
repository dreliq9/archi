"""DXF floor plan export using canonical shared wall topology."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from archi.graph.model import BuildingGraph, NodeType
from archi.graph.topology import derive_wall_segments
from archi.units import feet_to_inches


def _wall_records(graph: BuildingGraph, level: int) -> list[dict]:
    records = [
        props for props in graph.get_all_nodes(NodeType.WALL).values()
        if props.get("level") == level and props.get("derived")
    ]
    if records:
        return records
    return [
        {
            "wall_key": seg.key,
            "orientation": seg.orientation,
            "start_x": seg.start_xy[0],
            "start_y": seg.start_xy[1],
            "end_x": seg.end_xy[0],
            "end_y": seg.end_xy[1],
            "length_ft": seg.length_ft,
            "room_ids": list(seg.room_ids),
            "exterior": seg.exterior,
        }
        for seg in derive_wall_segments(graph, level)
    ]


def _wall_openings(graph: BuildingGraph, wall_key: str) -> list[dict]:
    openings = []
    for props in graph.get_all_nodes(NodeType.OPENING).values():
        if props.get("wall_key") == wall_key and props.get("topology_status") == "bound":
            openings.append(props)
    return sorted(openings, key=lambda p: float(p.get("wall_offset_ft", 0.0)))


def _draw_wall_with_gaps(msp, wall: dict, graph: BuildingGraph) -> None:
    orientation = wall["orientation"]
    sx = feet_to_inches(float(wall["start_x"]))
    sy = feet_to_inches(float(wall["start_y"]))
    ex = feet_to_inches(float(wall["end_x"]))
    ey = feet_to_inches(float(wall["end_y"]))
    total = feet_to_inches(float(wall["length_ft"]))
    openings = _wall_openings(graph, wall.get("wall_key", ""))

    gaps: list[tuple[float, float]] = []
    for opening in openings:
        start = feet_to_inches(float(opening.get("wall_offset_ft", 0.0)))
        end = min(total, start + float(opening.get("width", 0.0)))
        if end > start:
            gaps.append((start, end))

    cursor = 0.0
    for start, end in gaps + [(total, total)]:
        if start > cursor:
            if orientation == "h":
                p1 = (sx + cursor, sy)
                p2 = (sx + start, sy)
            else:
                p1 = (sx, sy + cursor)
                p2 = (sx, sy + start)
            msp.add_line(p1, p2, dxfattribs={"layer": "WALLS"})
        cursor = max(cursor, end)

    for start, end in gaps:
        if orientation == "h":
            p1 = (sx + start, sy)
            p2 = (sx + end, sy)
        else:
            p1 = (sx, sy + start)
            p2 = (sx, sy + end)
        msp.add_line(p1, p2, dxfattribs={"layer": "OPENINGS"})


def export_floor_plan(
    graph: BuildingGraph,
    level: int = 0,
    output_path: str | Path = "floor_plan.dxf",
) -> None:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("ROOMS", color=7)
    doc.layers.add("WALLS", color=1)
    doc.layers.add("OPENINGS", color=6)
    doc.layers.add("FURNITURE", color=3)
    doc.layers.add("LABELS", color=5)
    doc.layers.add("DIMENSIONS", color=4)

    floors = graph.get_all_nodes(NodeType.FLOOR)
    for floor_id, floor_props in floors.items():
        if floor_props.get("level") != level:
            continue
        for room_id in graph.get_rooms_on_floor(floor_id):
            room_props = graph.get_node(room_id)
            rx = feet_to_inches(float(room_props.get("x", 0.0)))
            ry = feet_to_inches(float(room_props.get("y", 0.0)))
            rw = feet_to_inches(float(room_props.get("width", 0.0)))
            rd = feet_to_inches(float(room_props.get("depth", 0.0)))
            if rw <= 0 or rd <= 0:
                continue
            points = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rd), (rx, ry + rd)]
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "ROOMS"})
            room_type = room_props.get("room_type")
            label = room_type.value.replace("_", " ").title() if room_type else "Room"
            area = room_props.get("area", 0.0)
            cx, cy = rx + rw / 2, ry + rd / 2
            msp.add_text(
                label,
                height=6.0,
                dxfattribs={"layer": "LABELS", "insert": (cx, cy + 4)},
            ).set_placement((cx, cy + 4), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            msp.add_text(
                f"{area:.0f} sqft",
                height=4.0,
                dxfattribs={"layer": "LABELS", "insert": (cx, cy - 4)},
            ).set_placement((cx, cy - 4), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            for furn_id in graph.get_furniture_in_room(room_id):
                fp = graph.get_node(furn_id)
                fx, fy = rx + fp.get("x", 0.0), ry + fp.get("y", 0.0)
                fw, fd = fp.get("width", 0.0), fp.get("depth", 0.0)
                if fw > 0 and fd > 0:
                    msp.add_lwpolyline(
                        [(fx, fy), (fx + fw, fy), (fx + fw, fy + fd), (fx, fy + fd)],
                        close=True,
                        dxfattribs={"layer": "FURNITURE"},
                    )

    for wall in _wall_records(graph, level):
        _draw_wall_with_gaps(msp, wall, graph)

    doc.saveas(str(output_path))
