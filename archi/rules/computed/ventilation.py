"""Ventilation requirements — IRC R303.1.

Habitable rooms need operable window area >= 4% of floor area.
Bathrooms and kitchens need mechanical ventilation or operable windows.
"""

from __future__ import annotations

from archi.graph.model import BuildingGraph, NodeType, OpeningType, RoomType

_OPERABLE_RATIO = 0.04

_HABITABLE_TYPES = {
    RoomType.KITCHEN, RoomType.LIVING_ROOM, RoomType.DINING_ROOM,
    RoomType.BEDROOM, RoomType.OFFICE, RoomType.LAUNDRY,
    RoomType.MUDROOM, RoomType.FOYER,
}

_MECHANICAL_REQUIRED_TYPES = {RoomType.BATHROOM, RoomType.HALF_BATH, RoomType.KITCHEN}


def check_ventilation(graph: BuildingGraph) -> list:
    from archi.rules.engine import Violation

    violations: list[Violation] = []

    room_operable_area: dict[str, float] = {}
    openings = graph.get_all_nodes(NodeType.OPENING)
    for opening_id, opening_props in openings.items():
        if opening_props.get("opening_type") != OpeningType.WINDOW:
            continue
        operable_area = opening_props.get("operable_area_sqft", 0.0)
        if operable_area <= 0:
            continue
        for edge in graph.get_edges(opening_id):
            if edge["edge_type"] == "connects":
                target = edge["target"]
                if graph.get_node(target).get("type") == NodeType.ROOM:
                    room_operable_area[target] = room_operable_area.get(target, 0.0) + operable_area

    all_rooms = graph.get_all_nodes(NodeType.ROOM)
    for room_id, props in all_rooms.items():
        room_type = props.get("room_type")
        if room_type is None:
            continue
        area = props.get("area", 0.0)

        if room_type in _HABITABLE_TYPES:
            required = area * _OPERABLE_RATIO
            actual = room_operable_area.get(room_id, 0.0)
            if actual < required:
                violations.append(Violation(
                    node_id=room_id,
                    rule="Natural ventilation (operable windows)",
                    severity="warning",
                    message=f"{room_type.value} has {actual:.1f} sqft operable window area, "
                            f"needs {required:.1f} sqft (4% of {area:.0f} sqft floor area)",
                    code_ref="IRC R303.1",
                ))

        if room_type in _MECHANICAL_REQUIRED_TYPES:
            has_mechanical = props.get("has_mechanical_vent", False)
            has_operable = room_operable_area.get(room_id, 0.0) > 0
            if not has_mechanical and not has_operable:
                violations.append(Violation(
                    node_id=room_id,
                    rule="Mechanical ventilation required",
                    severity="warning",
                    message=f"{room_type.value} requires mechanical ventilation or operable window",
                    code_ref="IRC R303.3",
                ))

    return violations
