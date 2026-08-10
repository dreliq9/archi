# archi/server.py
"""Archi MCP Server — AI-native architectural design."""

from __future__ import annotations

import math

from mcp.server.fastmcp import FastMCP

from archi.export.svg import render_floor_plan
from archi.graph.model import BuildingGraph, NodeType
from archi.graph.solver import CSPSolver, TreemapSolver
from archi.graph.topology import sync_wall_topology
from archi.graph.validator import LiveValidator


class BuildingState:
    """Shared state for the MCP server session."""

    def __init__(self, jurisdiction: str = "IRC-2021"):
        self.graph = BuildingGraph()
        self.validator = LiveValidator(self.graph, jurisdiction=jurisdiction)
        self._layout_cache: dict[int, dict[str, dict]] = {}
        self._layout_meta: dict[int, dict[str, object]] = {}

    @staticmethod
    def _compact_footprint(
        target_area: float,
        buildable_width: float,
        buildable_depth: float,
    ) -> tuple[float, float] | None:
        """Fit a compact rectangle of ``target_area`` inside the buildable lot."""
        if target_area <= 0:
            return 0.0, 0.0
        buildable_area = buildable_width * buildable_depth
        if target_area > buildable_area + 1e-6:
            return None

        aspect = buildable_width / buildable_depth
        width = math.sqrt(target_area * aspect)
        depth = target_area / width
        if width > buildable_width:
            width = buildable_width
            depth = target_area / width
        if depth > buildable_depth:
            depth = buildable_depth
            width = target_area / depth
        if width > buildable_width + 1e-6 or depth > buildable_depth + 1e-6:
            return None
        return width, depth

    def run_layout(self, level: int = 0) -> dict[str, dict]:
        """Run packed treemap seeding followed by CP-SAT refinement.

        The building footprint is derived from the requested room area rather
        than the entire buildable lot. This keeps rooms spatially coherent and
        prevents CP-SAT from scattering a small house across a large parcel.
        CP-SAT refines the packed seed against target areas and requested graph
        adjacencies; canonical walls are then compiled from the solved rooms.
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
            target_area = float(props.get("target_area", props.get("area", 100.0)))
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
        buildable_width = 50.0
        buildable_depth = 40.0
        for _bid, bprops in building_nodes.items():
            buildable_width = float(bprops.get("lot_width", 50.0))
            buildable_depth = float(bprops.get("lot_depth", 40.0))
            setbacks = bprops.get("setbacks", {})
            buildable_width -= setbacks.get("left", 0) + setbacks.get("right", 0)
            buildable_depth -= setbacks.get("front", 0) + setbacks.get("back", 0)
            break

        if buildable_width <= 0 or buildable_depth <= 0:
            return {}

        if not rooms:
            sync_wall_topology(self.graph, level=level)
            self._layout_cache[level] = {}
            self._layout_meta[level] = {
                "solver": "empty",
                "canonical_walls": 0,
                "footprint_width_ft": 0.0,
                "footprint_depth_ft": 0.0,
                "footprint_area_sqft": 0.0,
            }
            return {}

        target_total = sum(float(room["target_area"]) for room in rooms)
        footprint = self._compact_footprint(target_total, buildable_width, buildable_depth)
        if footprint is None:
            return {}
        footprint_width, footprint_depth = footprint

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
            footprint_width=footprint_width,
            footprint_depth=footprint_depth,
            rooms=rooms,
        )
        refined = CSPSolver.solve(
            footprint_width=footprint_width,
            footprint_depth=footprint_depth,
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

        wall_ids = sync_wall_topology(self.graph, level=level)
        self._layout_cache[level] = layout
        self._layout_meta[level] = {
            "solver": solver_name,
            "canonical_walls": len(wall_ids),
            "footprint_width_ft": footprint_width,
            "footprint_depth_ft": footprint_depth,
            "footprint_area_sqft": footprint_width * footprint_depth,
            "buildable_width_ft": buildable_width,
            "buildable_depth_ft": buildable_depth,
        }
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
