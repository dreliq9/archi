"""Layout solvers — treemap seed and CSP refinement.

TreemapSolver: fast rectangular subdivision (~10ms).
CSPSolver: OR-Tools CP-SAT refinement for adjacency constraints (~50-200ms).
"""

from __future__ import annotations


class TreemapSolver:
    """Squarified treemap layout. Recursively subdivides a rectangle into
    sub-rectangles proportional to target areas.

    Input:  footprint dimensions + list of rooms with target areas.
    Output: dict mapping room ID → {x, y, width, depth}.
    """

    @staticmethod
    def solve(
        footprint_width: float,
        footprint_depth: float,
        rooms: list[dict],
    ) -> dict[str, dict]:
        if not rooms:
            return {}

        total_target = sum(r["target_area"] for r in rooms)
        footprint_area = footprint_width * footprint_depth

        sorted_rooms = sorted(rooms, key=lambda r: r["target_area"], reverse=True)

        result: dict[str, dict] = {}
        TreemapSolver._subdivide(
            sorted_rooms, 0.0, 0.0, footprint_width, footprint_depth,
            footprint_area, total_target, result,
        )
        return result

    @staticmethod
    def _subdivide(
        rooms: list[dict],
        x: float, y: float,
        width: float, depth: float,
        available_area: float,
        total_target: float,
        result: dict[str, dict],
    ) -> None:
        if not rooms:
            return
        if len(rooms) == 1:
            result[rooms[0]["id"]] = {
                "x": x, "y": y, "width": width, "depth": depth,
            }
            return

        best_split = 1
        best_ratio_diff = float("inf")
        cumulative = 0.0
        for i in range(len(rooms) - 1):
            cumulative += rooms[i]["target_area"]
            ratio = cumulative / total_target
            diff = abs(ratio - 0.5)
            if diff < best_ratio_diff:
                best_ratio_diff = diff
                best_split = i + 1

        group_a = rooms[:best_split]
        group_b = rooms[best_split:]
        area_a = sum(r["target_area"] for r in group_a)
        area_b = sum(r["target_area"] for r in group_b)
        fraction_a = area_a / (area_a + area_b)

        if width >= depth:
            w_a = width * fraction_a
            TreemapSolver._subdivide(
                group_a, x, y, w_a, depth,
                w_a * depth, area_a, result,
            )
            TreemapSolver._subdivide(
                group_b, x + w_a, y, width - w_a, depth,
                (width - w_a) * depth, area_b, result,
            )
        else:
            d_a = depth * fraction_a
            TreemapSolver._subdivide(
                group_a, x, y, width, d_a,
                width * d_a, area_a, result,
            )
            TreemapSolver._subdivide(
                group_b, x, y + d_a, width, depth - d_a,
                width * (depth - d_a), area_b, result,
            )
