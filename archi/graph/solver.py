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


class CSPSolver:
    GRID_SCALE = 24  # grid units per foot

    @staticmethod
    def solve(
        footprint_width: float,
        footprint_depth: float,
        rooms: list[dict],
        adjacencies: list[tuple[str, str]],
        seed: dict[str, dict] | None = None,
        max_time_seconds: float = 2.0,
    ) -> dict[str, dict] | None:
        if not rooms:
            return {}

        from ortools.sat.python import cp_model

        model = cp_model.CpModel()
        scale = CSPSolver.GRID_SCALE
        max_w = int(footprint_width * scale)
        max_d = int(footprint_depth * scale)
        min_dim = int(3 * scale)  # 3 feet minimum dimension

        vars_by_id: dict[str, dict] = {}

        for room in rooms:
            rid = room["id"]
            x = model.new_int_var(0, max_w, f"{rid}_x")
            y = model.new_int_var(0, max_d, f"{rid}_y")
            w = model.new_int_var(min_dim, max_w, f"{rid}_w")
            d = model.new_int_var(min_dim, max_d, f"{rid}_d")

            model.add(x + w <= max_w)
            model.add(y + d <= max_d)

            # Area constraints
            area = model.new_int_var(0, max_w * max_d, f"{rid}_area")
            model.add_multiplication_equality(area, [w, d])
            min_area_grid = int(room.get("min_area", room["target_area"] * 0.8) * scale * scale)
            max_area_grid = int(room.get("max_area", room["target_area"] * 1.2) * scale * scale)
            model.add(area >= min_area_grid)
            model.add(area <= max_area_grid)

            # Aspect ratio via cross-multiplication
            min_ratio = room.get("min_aspect_ratio", 0.33)
            max_ratio = room.get("max_aspect_ratio", 3.0)
            ratio_scale = 100
            model.add(w * ratio_scale >= int(min_ratio * ratio_scale) * d)
            model.add(w * ratio_scale <= int(max_ratio * ratio_scale) * d)

            vars_by_id[rid] = {"x": x, "y": y, "w": w, "d": d}

            if seed and rid in seed:
                s = seed[rid]
                model.add_hint(x, int(s["x"] * scale))
                model.add_hint(y, int(s["y"] * scale))
                model.add_hint(w, int(s["width"] * scale))
                model.add_hint(d, int(s["depth"] * scale))

        # No-overlap: for each pair, at least one separation direction
        room_ids = [r["id"] for r in rooms]
        for i in range(len(room_ids)):
            for j in range(i + 1, len(room_ids)):
                ri = vars_by_id[room_ids[i]]
                rj = vars_by_id[room_ids[j]]
                b1 = model.new_bool_var(f"sep_{i}_{j}_l")
                b2 = model.new_bool_var(f"sep_{i}_{j}_r")
                b3 = model.new_bool_var(f"sep_{i}_{j}_a")
                b4 = model.new_bool_var(f"sep_{i}_{j}_b")
                model.add(ri["x"] + ri["w"] <= rj["x"]).only_enforce_if(b1)
                model.add(rj["x"] + rj["w"] <= ri["x"]).only_enforce_if(b2)
                model.add(ri["y"] + ri["d"] <= rj["y"]).only_enforce_if(b3)
                model.add(rj["y"] + rj["d"] <= ri["y"]).only_enforce_if(b4)
                model.add_bool_or([b1, b2, b3, b4])

        # Adjacency: rooms must touch on one axis and overlap on the other by >= 3ft
        min_shared = int(3.0 * scale)
        for id_a, id_b in adjacencies:
            if id_a not in vars_by_id or id_b not in vars_by_id:
                continue
            ra = vars_by_id[id_a]
            rb = vars_by_id[id_b]

            adj_l = model.new_bool_var(f"adj_{id_a}_{id_b}_l")
            adj_r = model.new_bool_var(f"adj_{id_a}_{id_b}_r")
            adj_t = model.new_bool_var(f"adj_{id_a}_{id_b}_t")
            adj_b = model.new_bool_var(f"adj_{id_a}_{id_b}_b")

            # a right edge touches b left edge + overlap on y
            model.add(ra["x"] + ra["w"] == rb["x"]).only_enforce_if(adj_l)
            oys = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_l_ys")
            oye = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_l_ye")
            model.add_max_equality(oys, [ra["y"], rb["y"]])
            model.add_min_equality(oye, [ra["y"] + ra["d"], rb["y"] + rb["d"]])
            model.add(oye - oys >= min_shared).only_enforce_if(adj_l)

            # b right edge touches a left edge + overlap on y
            model.add(rb["x"] + rb["w"] == ra["x"]).only_enforce_if(adj_r)
            oys2 = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_r_ys")
            oye2 = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_r_ye")
            model.add_max_equality(oys2, [ra["y"], rb["y"]])
            model.add_min_equality(oye2, [ra["y"] + ra["d"], rb["y"] + rb["d"]])
            model.add(oye2 - oys2 >= min_shared).only_enforce_if(adj_r)

            # a bottom touches b top + overlap on x
            model.add(ra["y"] + ra["d"] == rb["y"]).only_enforce_if(adj_t)
            oxs = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_t_xs")
            oxe = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_t_xe")
            model.add_max_equality(oxs, [ra["x"], rb["x"]])
            model.add_min_equality(oxe, [ra["x"] + ra["w"], rb["x"] + rb["w"]])
            model.add(oxe - oxs >= min_shared).only_enforce_if(adj_t)

            # b bottom touches a top + overlap on x
            model.add(rb["y"] + rb["d"] == ra["y"]).only_enforce_if(adj_b)
            oxs2 = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_b_xs")
            oxe2 = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_b_xe")
            model.add_max_equality(oxs2, [ra["x"], rb["x"]])
            model.add_min_equality(oxe2, [ra["x"] + ra["w"], rb["x"] + rb["w"]])
            model.add(oxe2 - oxs2 >= min_shared).only_enforce_if(adj_b)

            model.add_bool_or([adj_l, adj_r, adj_t, adj_b])

        # Objective: minimize deviation from target areas
        deviations = []
        for room in rooms:
            rid = room["id"]
            target_grid = int(room["target_area"] * scale * scale)
            area_var = model.new_int_var(0, max_w * max_d, f"{rid}_obj_area")
            model.add_multiplication_equality(area_var, [vars_by_id[rid]["w"], vars_by_id[rid]["d"]])
            dev = model.new_int_var(0, max_w * max_d, f"{rid}_dev")
            diff = model.new_int_var(-max_w * max_d, max_w * max_d, f"{rid}_diff")
            model.add(diff == area_var - target_grid)
            model.add_abs_equality(dev, diff)
            deviations.append(dev)

        total_dev = model.new_int_var(0, max_w * max_d * len(rooms), "total_dev")
        model.add(total_dev == sum(deviations))
        model.minimize(total_dev)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_time_seconds

        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        result: dict[str, dict] = {}
        for room in rooms:
            rid = room["id"]
            v = vars_by_id[rid]
            result[rid] = {
                "x": solver.value(v["x"]) / scale,
                "y": solver.value(v["y"]) / scale,
                "width": solver.value(v["w"]) / scale,
                "depth": solver.value(v["d"]) / scale,
            }
        return result
