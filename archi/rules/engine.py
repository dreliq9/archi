"""Rule engine — loads YAML jurisdiction profiles and evaluates declarative rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from archi.graph.model import BuildingGraph, NodeType, RoomType

_PROFILES_DIR = Path(__file__).parent / "profiles"

_HABITABLE_TYPES = {
    RoomType.KITCHEN, RoomType.LIVING_ROOM, RoomType.DINING_ROOM,
    RoomType.BEDROOM, RoomType.BATHROOM, RoomType.HALF_BATH,
    RoomType.OFFICE, RoomType.LAUNDRY, RoomType.MUDROOM, RoomType.FOYER,
}

_CATEGORY_MAP: dict[str, set[RoomType]] = {
    "habitable_room": _HABITABLE_TYPES,
    "kitchen": {RoomType.KITCHEN},
    "bedroom": {RoomType.BEDROOM},
    "bathroom": {RoomType.BATHROOM, RoomType.HALF_BATH},
    "hallway": {RoomType.HALLWAY},
    "garage": {RoomType.GARAGE},
}


def _room_categories(room_type: RoomType) -> list[str]:
    cats = []
    for cat_name, type_set in _CATEGORY_MAP.items():
        if room_type in type_set:
            cats.append(cat_name)
    return cats


class Violation:
    __slots__ = ("node_id", "rule", "severity", "message", "code_ref")

    def __init__(self, node_id: str, rule: str, severity: str, message: str,
                 code_ref: str = ""):
        self.node_id = node_id
        self.rule = rule
        self.severity = severity
        self.message = message
        self.code_ref = code_ref

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "code_ref": self.code_ref,
        }


class RuleEngine:
    def __init__(self, jurisdiction: str):
        self.jurisdiction = jurisdiction
        self._profile_path = _PROFILES_DIR / f"{jurisdiction.lower().replace('-', '_')}.yaml"
        if not self._profile_path.exists():
            raise FileNotFoundError(
                f"No rule profile for jurisdiction '{jurisdiction}' "
                f"(looked for {self._profile_path})"
            )
        with open(self._profile_path) as f:
            self._profile = yaml.safe_load(f)
        self.rules: dict = self._profile.get("rules", {})
        self._computed_rules: list[Callable[[BuildingGraph], list[Violation]]] = []

    def register_computed_rule(self, fn: Callable[[BuildingGraph], list[Violation]]) -> None:
        self._computed_rules.append(fn)

    def evaluate_declarative(self, graph: BuildingGraph) -> list[dict]:
        violations: list[Violation] = []
        violations.extend(self._check_room_minimums(graph))
        violations.extend(self._check_ceiling_heights(graph))
        violations.extend(self._check_stairs(graph))
        return [v.to_dict() for v in violations]

    def evaluate_computed(self, graph: BuildingGraph) -> list[dict]:
        violations: list[Violation] = []
        for fn in self._computed_rules:
            violations.extend(fn(graph))
        return [v.to_dict() for v in violations]

    def evaluate_all(self, graph: BuildingGraph) -> list[dict]:
        return self.evaluate_declarative(graph) + self.evaluate_computed(graph)

    def _check_room_minimums(self, graph: BuildingGraph) -> list[Violation]:
        violations: list[Violation] = []
        minimums = self.rules.get("room_minimums", {})
        rooms = graph.get_all_nodes(NodeType.ROOM)
        for room_id, props in rooms.items():
            room_type = props.get("room_type")
            if room_type is None:
                continue
            categories = _room_categories(room_type)
            area = props.get("area", 0.0)
            width = props.get("width", 0.0)
            depth = props.get("depth", 0.0)
            min_dim = min(width, depth) if width > 0 and depth > 0 else 0.0
            for cat in categories:
                cat_rules = minimums.get(cat, {})
                min_area = cat_rules.get("min_area_sqft")
                if min_area is not None and area < min_area:
                    violations.append(Violation(
                        node_id=room_id,
                        rule=f"Room minimum area ({cat})",
                        severity="error",
                        message=f"{room_type.value} has {area:.1f} sqft, minimum is {min_area} sqft",
                        code_ref=f"{self.jurisdiction} room_minimums.{cat}.min_area_sqft",
                    ))
                min_dimension = cat_rules.get("min_dimension_ft")
                if min_dimension is not None and min_dim > 0 and min_dim < min_dimension:
                    violations.append(Violation(
                        node_id=room_id,
                        rule=f"Room minimum dimension ({cat})",
                        severity="error",
                        message=f"{room_type.value} has {min_dim:.1f}ft minimum dimension, "
                                f"minimum is {min_dimension}ft",
                        code_ref=f"{self.jurisdiction} room_minimums.{cat}.min_dimension_ft",
                    ))
        return violations

    def _check_ceiling_heights(self, graph: BuildingGraph) -> list[Violation]:
        violations: list[Violation] = []
        height_rules = self.rules.get("ceiling_height", {})
        floors = graph.get_all_nodes(NodeType.FLOOR)
        for floor_id, floor_props in floors.items():
            height = floor_props.get("floor_to_floor_height", 9.0)
            room_ids = graph.get_rooms_on_floor(floor_id)
            for room_id in room_ids:
                room_props = graph.get_node(room_id)
                room_type = room_props.get("room_type")
                if room_type is None:
                    continue
                categories = _room_categories(room_type)
                for cat in categories:
                    cat_rules = height_rules.get(cat, {})
                    min_height = cat_rules.get("min_ft")
                    if min_height is not None and height < min_height:
                        violations.append(Violation(
                            node_id=room_id,
                            rule=f"Ceiling height minimum ({cat})",
                            severity="error",
                            message=f"{room_type.value} on floor has {height:.2f}ft ceiling, "
                                    f"minimum is {min_height}ft",
                            code_ref=f"{self.jurisdiction} ceiling_height.{cat}.min_ft",
                        ))
        return violations

    def _check_stairs(self, graph: BuildingGraph) -> list[Violation]:
        violations: list[Violation] = []
        stair_rules = self.rules.get("stairs", {})
        if not stair_rules:
            return violations
        all_nodes = graph.get_all_nodes()
        for node_id, props in all_nodes.items():
            if not props.get("is_stair"):
                continue
            riser = props.get("riser_height_in")
            if riser is not None:
                max_riser = stair_rules.get("max_riser_height_in")
                if max_riser is not None and riser > max_riser:
                    violations.append(Violation(
                        node_id=node_id,
                        rule="Stair maximum riser height",
                        severity="error",
                        message=f"Riser height is {riser}in, maximum is {max_riser}in",
                        code_ref=f"{self.jurisdiction} stairs.max_riser_height_in",
                    ))
            tread = props.get("tread_depth_in")
            if tread is not None:
                min_tread = stair_rules.get("min_tread_depth_in")
                if min_tread is not None and tread < min_tread:
                    violations.append(Violation(
                        node_id=node_id,
                        rule="Stair minimum tread depth",
                        severity="error",
                        message=f"Tread depth is {tread}in, minimum is {min_tread}in",
                        code_ref=f"{self.jurisdiction} stairs.min_tread_depth_in",
                    ))
            width = props.get("width_in")
            if width is not None:
                min_width = stair_rules.get("min_width_in")
                if min_width is not None and width < min_width:
                    violations.append(Violation(
                        node_id=node_id,
                        rule="Stair minimum width",
                        severity="error",
                        message=f"Stair width is {width}in, minimum is {min_width}in",
                        code_ref=f"{self.jurisdiction} stairs.min_width_in",
                    ))
        return violations
