"""Constraint graph — semantic model for buildings.

Rooms, walls, openings, fixtures, furniture are nodes. Adjacency, containment,
connection are edges. The graph is the single source of truth.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Callable


class NodeType(str, Enum):
    BUILDING = "building"
    FLOOR = "floor"
    ROOM = "room"
    WALL = "wall"
    OPENING = "opening"
    FIXTURE = "fixture"
    FURNITURE = "furniture"


class RoomType(str, Enum):
    KITCHEN = "kitchen"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    HALF_BATH = "half_bath"
    CLOSET = "closet"
    HALLWAY = "hallway"
    GARAGE = "garage"
    LAUNDRY = "laundry"
    OFFICE = "office"
    MUDROOM = "mudroom"
    PANTRY = "pantry"
    FOYER = "foyer"
    UTILITY = "utility"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    ARCHWAY = "archway"
    SLIDING_DOOR = "sliding_door"
    POCKET_DOOR = "pocket_door"
    GARAGE_DOOR = "garage_door"


class FixtureType(str, Enum):
    TOILET = "toilet"
    SINK = "sink"
    BATHTUB = "bathtub"
    SHOWER = "shower"
    DISHWASHER = "dishwasher"
    RANGE = "range"
    REFRIGERATOR = "refrigerator"
    WASHER = "washer"
    DRYER = "dryer"
    WATER_HEATER = "water_heater"
    FURNACE = "furnace"
    OUTLET = "outlet"
    SWITCH = "switch"
    LIGHT = "light"


class FurnitureType(str, Enum):
    SOFA = "sofa"
    LOVESEAT = "loveseat"
    ARMCHAIR = "armchair"
    DINING_TABLE = "dining_table"
    DESK = "desk"
    BED_KING = "bed_king"
    BED_QUEEN = "bed_queen"
    BED_TWIN = "bed_twin"
    DRESSER = "dresser"
    BOOKSHELF = "bookshelf"
    COFFEE_TABLE = "coffee_table"
    END_TABLE = "end_table"
    TV_STAND = "tv_stand"
    NIGHTSTAND = "nightstand"
    CABINET = "cabinet"


_BIDIRECTIONAL_EDGES = {"adjacent_to"}


class BuildingGraph:
    def __init__(self, on_mutate: Callable[[dict], None] | None = None):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[str, list[dict[str, Any]]] = {}
        self._on_mutate = on_mutate

    def _emit(self, event: dict) -> None:
        if self._on_mutate is not None:
            self._on_mutate(event)

    def add_node(self, node_type: NodeType, **properties: Any) -> str:
        node_id = str(uuid.uuid4())[:8]
        self._nodes[node_id] = {"type": node_type, **properties}
        self._edges.setdefault(node_id, [])
        self._emit({"action": "add_node", "node_id": node_id, "node_type": node_type.value})
        return node_id

    def get_node(self, node_id: str) -> dict[str, Any]:
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        return self._nodes[node_id]

    def update_node(self, node_id: str, **properties: Any) -> None:
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        self._nodes[node_id].update(properties)
        self._emit({"action": "update_node", "node_id": node_id})

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            raise KeyError(f"Node '{node_id}' not found")
        del self._nodes[node_id]
        if node_id in self._edges:
            del self._edges[node_id]
        for source_id in list(self._edges.keys()):
            self._edges[source_id] = [e for e in self._edges[source_id] if e["target"] != node_id]
        self._emit({"action": "remove_node", "node_id": node_id})

    def add_edge(self, source_id: str, target_id: str, edge_type: str, **properties: Any) -> None:
        if source_id not in self._nodes:
            raise KeyError(f"Source node '{source_id}' not found")
        if target_id not in self._nodes:
            raise KeyError(f"Target node '{target_id}' not found")
        edge = {"target": target_id, "edge_type": edge_type, **properties}
        self._edges.setdefault(source_id, [])
        self._edges[source_id].append(edge)
        if edge_type in _BIDIRECTIONAL_EDGES:
            reverse = {"target": source_id, "edge_type": edge_type, **properties}
            self._edges.setdefault(target_id, [])
            self._edges[target_id].append(reverse)
        self._emit({"action": "add_edge", "source": source_id, "target": target_id, "edge_type": edge_type})

    def get_edges(self, node_id: str) -> list[dict[str, Any]]:
        return self._edges.get(node_id, [])

    def get_adjacent_rooms(self, room_id: str) -> list[str]:
        return [e["target"] for e in self.get_edges(room_id) if e["edge_type"] == "adjacent_to"]

    def get_rooms_on_floor(self, floor_id: str) -> list[str]:
        return [e["target"] for e in self.get_edges(floor_id)
                if e["edge_type"] == "contains" and self._nodes.get(e["target"], {}).get("type") == NodeType.ROOM]

    def get_furniture_in_room(self, room_id: str) -> list[str]:
        return [e["target"] for e in self.get_edges(room_id)
                if e["edge_type"] == "contains" and self._nodes.get(e["target"], {}).get("type") == NodeType.FURNITURE]

    def get_all_nodes(self, node_type: NodeType | None = None) -> dict[str, dict]:
        if node_type is None:
            return dict(self._nodes)
        return {nid: props for nid, props in self._nodes.items() if props.get("type") == node_type}

    def to_dict(self) -> dict:
        def _serialize_value(v: Any) -> Any:
            if isinstance(v, Enum):
                return v.value
            if isinstance(v, dict):
                return {k: _serialize_value(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_serialize_value(item) for item in v]
            return v
        nodes = {}
        for nid, props in self._nodes.items():
            nodes[nid] = {k: _serialize_value(v) for k, v in props.items()}
        edges = {}
        for source_id, edge_list in self._edges.items():
            edges[source_id] = [{k: _serialize_value(v) for k, v in e.items()} for e in edge_list]
        return {"nodes": nodes, "edges": edges}

    @classmethod
    def from_dict(cls, data: dict) -> BuildingGraph:
        _TYPE_MAP = {t.value: t for t in NodeType}
        _ROOM_TYPE_MAP = {t.value: t for t in RoomType}
        _OPENING_TYPE_MAP = {t.value: t for t in OpeningType}
        _FIXTURE_TYPE_MAP = {t.value: t for t in FixtureType}
        _FURNITURE_TYPE_MAP = {t.value: t for t in FurnitureType}
        g = cls()
        for nid, props in data["nodes"].items():
            restored = {}
            for k, v in props.items():
                if k == "type":
                    restored[k] = _TYPE_MAP[v]
                elif k == "room_type":
                    restored[k] = _ROOM_TYPE_MAP[v]
                elif k == "opening_type":
                    restored[k] = _OPENING_TYPE_MAP[v]
                elif k == "fixture_type":
                    restored[k] = _FIXTURE_TYPE_MAP[v]
                elif k == "furniture_type":
                    restored[k] = _FURNITURE_TYPE_MAP[v]
                else:
                    restored[k] = v
            g._nodes[nid] = restored
            g._edges.setdefault(nid, [])
        for source_id, edge_list in data.get("edges", {}).items():
            g._edges[source_id] = list(edge_list)
        return g
