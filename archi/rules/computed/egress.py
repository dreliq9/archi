"""Egress path calculation — BFS on room adjacency via connected openings.

Every habitable room must have a path through doorways to a room that has
an exterior door. Returns Violation objects for rooms that fail.
"""

from __future__ import annotations

from collections import deque

from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType

_NON_HABITABLE = {RoomType.HALLWAY, RoomType.CLOSET, RoomType.GARAGE,
                  RoomType.UTILITY, RoomType.PANTRY}


def check_egress(graph: BuildingGraph) -> list:
    from archi.rules.engine import Violation

    # Find rooms with direct exterior doors
    rooms_with_exterior_door: set[str] = set()
    openings = graph.get_all_nodes(NodeType.OPENING)
    for opening_id, opening_props in openings.items():
        if not opening_props.get("exterior", False):
            continue
        edges = graph.get_edges(opening_id)
        for edge in edges:
            if edge["edge_type"] == "connects":
                target_node = graph.get_node(edge["target"])
                if target_node.get("type") == NodeType.ROOM:
                    rooms_with_exterior_door.add(edge["target"])

    # Build room-to-room connectivity through door openings
    room_connections: dict[str, set[str]] = {}
    for opening_id, opening_props in openings.items():
        op_type = opening_props.get("opening_type")
        if op_type not in (OpeningType.DOOR, OpeningType.ARCHWAY,
                           OpeningType.SLIDING_DOOR, OpeningType.POCKET_DOOR):
            continue
        connected_rooms: list[str] = []
        for edge in graph.get_edges(opening_id):
            if edge["edge_type"] == "connects":
                target = edge["target"]
                if graph.get_node(target).get("type") == NodeType.ROOM:
                    connected_rooms.append(target)
        for i in range(len(connected_rooms)):
            for j in range(i + 1, len(connected_rooms)):
                room_connections.setdefault(connected_rooms[i], set()).add(connected_rooms[j])
                room_connections.setdefault(connected_rooms[j], set()).add(connected_rooms[i])

    # BFS from rooms with exterior doors
    reachable: set[str] = set()
    queue: deque[str] = deque(rooms_with_exterior_door)
    reachable.update(rooms_with_exterior_door)
    while queue:
        current = queue.popleft()
        for neighbor in room_connections.get(current, set()):
            if neighbor not in reachable:
                reachable.add(neighbor)
                queue.append(neighbor)

    # Check all habitable rooms
    violations: list[Violation] = []
    all_rooms = graph.get_all_nodes(NodeType.ROOM)
    for room_id, room_props in all_rooms.items():
        room_type = room_props.get("room_type")
        if room_type is None or room_type in _NON_HABITABLE:
            continue
        if room_id not in reachable:
            violations.append(Violation(
                node_id=room_id,
                rule="Egress path required",
                severity="error",
                message=f"{room_type.value} has no path through doorways to an exterior door",
                code_ref="IRC R311.1",
            ))

    return violations
