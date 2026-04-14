"""DXF floor plan export — 2D CAD format for contractor handoff."""

from __future__ import annotations
from pathlib import Path
import ezdxf
from archi.graph.model import BuildingGraph, NodeType

_FT_TO_INCHES = 12.0

def export_floor_plan(graph: BuildingGraph, level: int = 0, output_path: str | Path = "floor_plan.dxf") -> None:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("ROOMS", color=7)
    doc.layers.add("WALLS", color=1)
    doc.layers.add("FURNITURE", color=3)
    doc.layers.add("LABELS", color=5)
    doc.layers.add("DIMENSIONS", color=4)

    floors = graph.get_all_nodes(NodeType.FLOOR)
    for floor_id, floor_props in floors.items():
        if floor_props.get("level") != level:
            continue
        for room_id in graph.get_rooms_on_floor(floor_id):
            room_props = graph.get_node(room_id)
            rx = room_props.get("x", 0.0) * _FT_TO_INCHES
            ry = room_props.get("y", 0.0) * _FT_TO_INCHES
            rw = room_props.get("width", 0.0) * _FT_TO_INCHES
            rd = room_props.get("depth", 0.0) * _FT_TO_INCHES
            if rw <= 0 or rd <= 0:
                continue
            points = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rd), (rx, ry + rd)]
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "ROOMS"})
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "WALLS", "const_width": 5.5})
            room_type = room_props.get("room_type")
            label = room_type.value.replace("_", " ").title() if room_type else "Room"
            area = room_props.get("area", 0.0)
            cx, cy = rx + rw / 2, ry + rd / 2
            msp.add_text(f"{label}", height=6.0, dxfattribs={"layer": "LABELS", "insert": (cx, cy + 4)}).set_placement((cx, cy + 4), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            msp.add_text(f"{area:.0f} sqft", height=4.0, dxfattribs={"layer": "LABELS", "insert": (cx, cy - 4)}).set_placement((cx, cy - 4), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
            for furn_id in graph.get_furniture_in_room(room_id):
                fp = graph.get_node(furn_id)
                fx, fy = rx + fp.get("x", 0.0), ry + fp.get("y", 0.0)
                fw, fd = fp.get("width", 0.0), fp.get("depth", 0.0)
                if fw > 0 and fd > 0:
                    msp.add_lwpolyline([(fx, fy), (fx + fw, fy), (fx + fw, fy + fd), (fx, fy + fd)], close=True, dxfattribs={"layer": "FURNITURE"})
    doc.saveas(str(output_path))
