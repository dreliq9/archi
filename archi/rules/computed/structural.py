"""Structural span limits — checks openings in load-bearing walls.

Simplified residential span table for wood-frame construction.
"""

from __future__ import annotations

from archi.graph.model import BuildingGraph, NodeType

_MAX_SPAN_INCHES: dict[str, float] = {
    "wood_frame": 72.0,    # 6 feet
    "steel_frame": 96.0,   # 8 feet
    "masonry": 48.0,       # 4 feet
    "concrete": 60.0,      # 5 feet
}

_WARNING_THRESHOLD = 0.8


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

            opening_width = target_props.get("width", 0.0)
            if opening_width > max_span:
                violations.append(Violation(
                    node_id=target,
                    rule="Structural span limit exceeded",
                    severity="error",
                    message=f"Opening is {opening_width:.0f}in wide in a {material} "
                            f"load-bearing wall (max {max_span:.0f}in without engineering)",
                    code_ref="IRC R602.7 (header spans)",
                ))
            elif opening_width > warn_span:
                violations.append(Violation(
                    node_id=target,
                    rule="Structural span limit approaching",
                    severity="warning",
                    message=f"Opening is {opening_width:.0f}in wide in a {material} "
                            f"load-bearing wall (max {max_span:.0f}in) — verify header sizing",
                    code_ref="IRC R602.7 (header spans)",
                ))

    return violations
