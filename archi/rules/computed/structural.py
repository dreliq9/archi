"""Structural span limits — checks openings in load-bearing walls.

This remains a deliberately simplified screening rule, not an IRC R602.7
header-sizing implementation. Opening widths are normalized to inches before
comparison so legacy feet-tagged graph data cannot silently pass an inch-based
threshold.
"""

from __future__ import annotations

from archi.graph.model import BuildingGraph, NodeType
from archi.units import feet_to_inches

_MAX_SPAN_INCHES: dict[str, float] = {
    "wood_frame": 72.0,
    "steel_frame": 96.0,
    "masonry": 48.0,
    "concrete": 60.0,
}

_WARNING_THRESHOLD = 0.8


def _opening_width_inches(props: dict) -> float:
    width = float(props.get("width", 0.0))
    unit = props.get("dimension_unit", "in")
    if unit == "ft":
        return feet_to_inches(width)
    if unit != "in":
        return 0.0
    return width


def check_structural_spans(graph: BuildingGraph) -> list:
    from archi.rules.engine import Violation

    violations: list[Violation] = []

    walls = graph.get_all_nodes(NodeType.WALL)
    for wall_id, wall_props in walls.items():
        if not wall_props.get("structural", False):
            continue

        material = wall_props.get("material", "wood_frame")
        max_span = _MAX_SPAN_INCHES.get(material, 72.0)
        warn_span = max_span * _WARNING_THRESHOLD

        for edge in graph.get_edges(wall_id):
            if edge["edge_type"] != "contains":
                continue
            target = edge["target"]
            target_props = graph.get_node(target)
            if target_props.get("type") != NodeType.OPENING:
                continue

            opening_width = _opening_width_inches(target_props)
            if opening_width > max_span:
                violations.append(Violation(
                    node_id=target,
                    rule="Structural span screening limit exceeded",
                    severity="error",
                    message=f"Opening is {opening_width:.0f}in wide in a {material} "
                            f"load-bearing wall (screening limit {max_span:.0f}in; engineered/header-table sizing required)",
                    code_ref="IRC R602.7 (screening only — not full table evaluation)",
                ))
            elif opening_width > warn_span:
                violations.append(Violation(
                    node_id=target,
                    rule="Structural span screening limit approaching",
                    severity="warning",
                    message=f"Opening is {opening_width:.0f}in wide in a {material} "
                            f"load-bearing wall (screening limit {max_span:.0f}in) — verify header sizing",
                    code_ref="IRC R602.7 (screening only — not full table evaluation)",
                ))

    return violations
