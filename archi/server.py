# archi/server.py
"""Archi MCP Server — AI-native architectural design."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from archi.graph.model import BuildingGraph, NodeType, RoomType
from archi.graph.solver import TreemapSolver
from archi.graph.validator import LiveValidator
from archi.export.svg import render_floor_plan


class BuildingState:
    """Shared state for the MCP server session."""

    def __init__(self, jurisdiction: str = "IRC-2021"):
        self.graph = BuildingGraph()
        self.validator = LiveValidator(self.graph, jurisdiction=jurisdiction)
        self._layout_cache: dict[int, dict[str, dict]] = {}

    def run_layout(self, level: int = 0) -> dict[str, dict]:
        """Run treemap layout for a floor level and cache the result."""
        floor_nodes = self.graph.get_all_nodes(NodeType.FLOOR)
        floor_id = None
        for fid, fprops in floor_nodes.items():
            if fprops.get("level") == level:
                floor_id = fid
                break
        if floor_id is None:
            return {}

        room_ids = self.graph.get_rooms_on_floor(floor_id)
        rooms = []
        for rid in room_ids:
            props = self.graph.get_node(rid)
            target_area = props.get("area", props.get("min_area", 100.0))
            rooms.append({"id": rid, "target_area": target_area})

        building_nodes = self.graph.get_all_nodes(NodeType.BUILDING)
        lot_width = 50.0
        lot_depth = 40.0
        for bid, bprops in building_nodes.items():
            lot_width = bprops.get("lot_width", 50.0)
            lot_depth = bprops.get("lot_depth", 40.0)
            setbacks = bprops.get("setbacks", {})
            lot_width -= setbacks.get("left", 0) + setbacks.get("right", 0)
            lot_depth -= setbacks.get("front", 0) + setbacks.get("back", 0)
            break

        layout = TreemapSolver.solve(
            footprint_width=lot_width, footprint_depth=lot_depth, rooms=rooms)

        for rid, pos in layout.items():
            self.graph.update_node(rid, x=pos["x"], y=pos["y"],
                                    width=pos["width"], depth=pos["depth"],
                                    area=pos["width"] * pos["depth"])

        self._layout_cache[level] = layout
        return layout

    def respond(self, result: dict, level: int = 0) -> dict:
        """Wrap a tool result with SVG preview and violations."""
        svg = render_floor_plan(self.graph, level=level)
        violations = self.validator.get_violations()
        return {
            **result,
            "svg": svg,
            "violations": violations,
            "violation_counts": self.validator.get_violation_counts(),
        }


mcp = FastMCP("archi", instructions="AI-native architectural and interior design server")
state = BuildingState()


def main():
    """Entry point for the archi MCP server."""
    import archi.tools.arch
    import archi.tools.interior
    import archi.tools.query
    import archi.tools.export
    mcp.run()
