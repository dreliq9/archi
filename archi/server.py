# archi/server.py
"""Archi MCP Server — AI-native architectural design."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from archi.graph.model import BuildingGraph, NodeType
from archi.graph.solver import CSPSolver, TreemapSolver
from archi.graph.validator import LiveValidator
from archi.export.svg import render_floor_plan


class BuildingState:
    """Shared state for the MCP server session."""

    def __init__(self, jurisdiction: str = "IRC-2021"):
        self.graph = BuildingGraph()
        self.validator = LiveValidator(self.graph, jurisdiction=jurisdiction)
        self._layout_cache: dict[int, dict[str, dict]] = {}
        self._layout_meta: dict[int, dict[str, str]] = {}

    def run_layout(self, level: int = 0) -> dict[str, dict]:
        """Run treemap seeding followed by CP-SAT constraint refinement.

        The treemap gives the solver a fast full-footprint seed. CP-SAT then
        refines room dimensions/positions against requested target areas and
        graph adjacency constraints. If the constrained solve is infeasible,
        the deterministic treemap seed remains the fallback layout.
        """
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
        room_id_set = set(room_ids)
        for rid in room_ids:
            props = self.graph.get_node(rid)
            target_area = props.get("target_area", props.get("area", 100.0))
            room = {
                "id": rid,
                "target_area": target_area,
                "min_area": props.get("min_area", target_area * 0.8),
                "max_area": props.get("max_area", target_area * 1.2),
            }
            if props.get("preferred_width"):
                room["preferred_width"] = props["preferred_width"]
            if props.get("preferred_depth"):
                room["preferred_depth"] = props["preferred_depth"]
            rooms.append(room)

        building_nodes = self.graph.get_all_nodes(NodeType.BUILDING)
        lot_width = 50.0
        lot_depth = 40.0
        for _bid, bprops in building_nodes.items():
            lot_width = bprops.get("lot_width", 50.0)
            lot_depth = bprops.get("lot_depth", 40.0)
            setbacks = bprops.get("setbacks", {})
            lot_width -= setbacks.get("left", 0) + setbacks.get("right", 0)
            lot_depth -= setbacks.get("front", 0) + setbacks.get("back", 0)
            break

        if lot_width <= 0 or lot_depth <= 0:
            return {}

        adjacencies: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for rid in room_ids:
            for edge in self.graph.get_edges(rid):
                other = edge.get("target")
                if edge.get("edge_type") != "adjacent_to" or other not in room_id_set:
                    continue
                pair = tuple(sorted((rid, other)))
                if pair not in seen:
                    seen.add(pair)
                    adjacencies.append(pair)

        seed = TreemapSolver.solve(
            footprint_width=lot_width,
            footprint_depth=lot_depth,
            rooms=rooms,
        )
        refined = CSPSolver.solve(
            footprint_width=lot_width,
            footprint_depth=lot_depth,
            rooms=rooms,
            adjacencies=adjacencies,
            seed=seed,
        )
        layout = refined if refined is not None else seed
        solver_name = "csp" if refined is not None else "treemap_fallback"

        for rid, pos in layout.items():
            self.graph.update_node(
                rid,
                x=pos["x"],
                y=pos["y"],
                width=pos["width"],
                depth=pos["depth"],
                area=pos["width"] * pos["depth"],
            )

        self._layout_cache[level] = layout
        self._layout_meta[level] = {"solver": solver_name}
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
            "layout": self._layout_meta.get(level, {}),
        }


mcp = FastMCP("archi", instructions="AI-native architectural and interior design server")
state = BuildingState()

# Import tool modules to register @mcp.tool() decorators
import archi.tools.arch  # noqa: E402, F401
import archi.tools.interior  # noqa: E402, F401
import archi.tools.query  # noqa: E402, F401
import archi.tools.export  # noqa: E402, F401
import archi.tools.render  # noqa: E402, F401


def main():
    """Entry point for the archi MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
