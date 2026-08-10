"""Derived canonical wall/opening topology from solved room rectangles.

Room rectangles remain the spatial source of truth. This module splits their
collinear boundaries into unique wall segments, records room ownership, and
rebinds semantic openings to the appropriate shared or exterior wall after
layout changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from archi.graph.model import BuildingGraph, NodeType
from archi.units import inches_to_feet

_TOL = 1e-6


@dataclass(frozen=True)
class WallSegment:
    key: str
    level: int
    orientation: str  # "h" or "v"
    coord: float
    start: float
    end: float
    room_ids: tuple[str, ...]

    @property
    def exterior(self) -> bool:
        return len(self.room_ids) == 1

    @property
    def length_ft(self) -> float:
        return self.end - self.start

    @property
    def start_xy(self) -> tuple[float, float]:
        if self.orientation == "h":
            return self.start, self.coord
        return self.coord, self.start

    @property
    def end_xy(self) -> tuple[float, float]:
        if self.orientation == "h":
            return self.end, self.coord
        return self.coord, self.end


def _q(value: float) -> float:
    return round(float(value), 6)


def _floor_room_ids(graph: BuildingGraph, level: int) -> list[str]:
    for floor_id, props in graph.get_all_nodes(NodeType.FLOOR).items():
        if props.get("level") == level:
            return graph.get_rooms_on_floor(floor_id)
    return []


def derive_wall_segments(graph: BuildingGraph, level: int = 0) -> list[WallSegment]:
    """Return unique wall segments for one solved floor.

    Shared boundaries are represented once with two room owners. Partial
    overlaps are split at every collinear endpoint so T-junctions remain
    canonical rather than creating overlapping wall records.
    """
    sides: dict[tuple[str, float], list[tuple[float, float, str]]] = {}
    for room_id in _floor_room_ids(graph, level):
        props = graph.get_node(room_id)
        x = float(props.get("x", 0.0))
        y = float(props.get("y", 0.0))
        w = float(props.get("width", 0.0))
        d = float(props.get("depth", 0.0))
        if w <= 0 or d <= 0:
            continue
        room_sides = [
            ("h", _q(y), _q(x), _q(x + w)),
            ("h", _q(y + d), _q(x), _q(x + w)),
            ("v", _q(x), _q(y), _q(y + d)),
            ("v", _q(x + w), _q(y), _q(y + d)),
        ]
        for orientation, coord, start, end in room_sides:
            sides.setdefault((orientation, coord), []).append((start, end, room_id))

    segments: list[WallSegment] = []
    for (orientation, coord), intervals in sorted(sides.items()):
        points = sorted({p for start, end, _ in intervals for p in (start, end)})
        for a, b in zip(points, points[1:]):
            if b - a <= _TOL:
                continue
            mid = (a + b) / 2.0
            owners = tuple(sorted(
                room_id for start, end, room_id in intervals
                if start - _TOL <= mid <= end + _TOL
            ))
            if not owners:
                continue
            key = f"L{level}:{orientation}:{coord:.6f}:{a:.6f}:{b:.6f}"
            segments.append(WallSegment(
                key=key,
                level=level,
                orientation=orientation,
                coord=coord,
                start=a,
                end=b,
                room_ids=owners,
            ))
    return segments


def _opening_room_ids(graph: BuildingGraph, opening_id: str) -> tuple[str, ...]:
    rooms = []
    for edge in graph.get_edges(opening_id):
        if edge.get("edge_type") != "connects":
            continue
        target = edge.get("target")
        try:
            props = graph.get_node(target)
        except KeyError:
            continue
        if props.get("type") == NodeType.ROOM:
            rooms.append(target)
    return tuple(sorted(set(rooms)))


def _candidate_walls(graph: BuildingGraph, opening_id: str) -> list[tuple[str, dict]]:
    props = graph.get_node(opening_id)
    room_ids = _opening_room_ids(graph, opening_id)
    exterior = bool(props.get("exterior", False))
    candidates: list[tuple[str, dict]] = []
    for wall_id, wall in graph.get_all_nodes(NodeType.WALL).items():
        owners = tuple(sorted(wall.get("room_ids", [])))
        if exterior:
            if len(room_ids) == 1 and wall.get("exterior") and owners == room_ids:
                candidates.append((wall_id, wall))
        elif len(room_ids) == 2 and owners == room_ids:
            candidates.append((wall_id, wall))
    return candidates


def bind_opening_to_wall(graph: BuildingGraph, opening_id: str) -> tuple[bool, str | None]:
    """Attach an opening to the best canonical wall for its connected rooms."""
    props = graph.get_node(opening_id)
    width_ft = inches_to_feet(float(props.get("width", 0.0)))
    candidates = [
        (wall_id, wall) for wall_id, wall in _candidate_walls(graph, opening_id)
        if float(wall.get("length_ft", 0.0)) + _TOL >= width_ft
    ]
    if not candidates:
        graph.update_node(opening_id, topology_status="unresolved", wall_id=None, wall_key=None)
        return False, "No canonical wall can accommodate this opening"

    wall_id, wall = sorted(
        candidates,
        key=lambda item: (-float(item[1].get("length_ft", 0.0)), item[1].get("wall_key", "")),
    )[0]
    offset_ft = max(0.0, (float(wall["length_ft"]) - width_ft) / 2.0)
    graph.add_edge(wall_id, opening_id, "contains")
    graph.update_node(
        opening_id,
        wall_id=wall_id,
        wall_key=wall.get("wall_key"),
        wall_offset_ft=offset_ft,
        topology_status="bound",
    )
    return True, None


def sync_wall_topology(graph: BuildingGraph, level: int = 0) -> dict[str, str]:
    """Replace derived walls for a level and rebind existing openings."""
    old_wall_ids = [
        wall_id for wall_id, props in graph.get_all_nodes(NodeType.WALL).items()
        if props.get("derived") and props.get("level") == level
    ]
    for wall_id in old_wall_ids:
        graph.remove_node(wall_id)

    wall_ids: dict[str, str] = {}
    for segment in derive_wall_segments(graph, level):
        sx, sy = segment.start_xy
        ex, ey = segment.end_xy
        wall_id = graph.add_node(
            NodeType.WALL,
            derived=True,
            level=level,
            wall_key=segment.key,
            orientation=segment.orientation,
            start_x=sx,
            start_y=sy,
            end_x=ex,
            end_y=ey,
            length_ft=segment.length_ft,
            room_ids=list(segment.room_ids),
            exterior=segment.exterior,
            thickness_in=5.5,
            structural=False,
            material="wood_frame",
            length_unit="ft",
        )
        for room_id in segment.room_ids:
            graph.add_edge(wall_id, room_id, "bounds")
        wall_ids[segment.key] = wall_id

    for opening_id, props in graph.get_all_nodes(NodeType.OPENING).items():
        connected = _opening_room_ids(graph, opening_id)
        if not connected:
            continue
        room_level = graph.get_node(connected[0]).get("level", 0)
        if room_level == level:
            bind_opening_to_wall(graph, opening_id)
    return wall_ids
