"""Layout solvers — treemap seed and CP-SAT refinement.

TreemapSolver produces a compact rectangular partition. CSPSolver preserves
that packed topology as a soft objective while enforcing area, aspect-ratio,
non-overlap, and requested adjacency constraints.
"""

from __future__ import annotations


class TreemapSolver:
    """Recursively subdivide a rectangle proportional to target room areas."""

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
            sorted_rooms,
            0.0,
            0.0,
            footprint_width,
            footprint_depth,
            footprint_area,
            total_target,
            result,
        )
        return result

    @staticmethod
    def _subdivide(
        rooms: list[dict],
        x: float,
        y: float,
        width: float,
        depth: float,
        available_area: float,
        total_target: float,
        result: dict[str, dict],
    ) -> None:
        if not rooms:
            return
        if len(rooms) == 1:
            result[rooms[0]["id"]] = {
                "x": x,
                "y": y,
                "width": width,
                "depth": depth,
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
                group_a, x, y, w_a, depth, w_a * depth, area_a, result,
            )
            TreemapSolver._subdivide(
                group_b,
                x + w_a,
                y,
                width - w_a,
                depth,
                (width - w_a) * depth,
                area_b,
                result,
            )
        else:
            d_a = depth * fraction_a
            TreemapSolver._subdivide(
                group_a, x, y, width, d_a, width * d_a, area_a, result,
            )
            TreemapSolver._subdivide(
                group_b,
                x,
                y + d_a,
                width,
                depth - d_a,
                width * (depth - d_a),
                area_b,
                result,
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
        max_w = int(round(footprint_width * scale))
        max_d = int(round(footprint_depth * scale))
        min_dim = int(3 * scale)
        if max_w < min_dim or max_d < min_dim:
            return None

        vars_by_id: dict[str, dict] = {}
        area_vars: dict[str, object] = {}

        for room in rooms:
            rid = room["id"]
            x = model.new_int_var(0, max_w, f"{rid}_x")
            y = model.new_int_var(0, max_d, f"{rid}_y")
            w = model.new_int_var(min_dim, max_w, f"{rid}_w")
            d = model.new_int_var(min_dim, max_d, f"{rid}_d")
            model.add(x + w <= max_w)
            model.add(y + d <= max_d)

            area = model.new_int_var(0, max_w * max_d, f"{rid}_area")
            model.add_multiplication_equality(area, [w, d])
            min_area_grid = int(room.get("min_area", room["target_area"] * 0.8) * scale * scale)
            max_area_grid = int(room.get("max_area", room["target_area"] * 1.2) * scale * scale)
            model.add(area >= min_area_grid)
            model.add(area <= max_area_grid)

            min_ratio = room.get("min_aspect_ratio", 0.33)
            max_ratio = room.get("max_aspect_ratio", 3.0)
            ratio_scale = 100
            model.add(w * ratio_scale >= int(min_ratio * ratio_scale) * d)
            model.add(w * ratio_scale <= int(max_ratio * ratio_scale) * d)

            vars_by_id[rid] = {"x": x, "y": y, "w": w, "d": d}
            area_vars[rid] = area

            if seed and rid in seed:
                s = seed[rid]
                model.add_hint(x, int(round(s["x"] * scale)))
                model.add_hint(y, int(round(s["y"] * scale)))
                model.add_hint(w, int(round(s["width"] * scale)))
                model.add_hint(d, int(round(s["depth"] * scale)))

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

            model.add(ra["x"] + ra["w"] == rb["x"]).only_enforce_if(adj_l)
            oys = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_l_ys")
            oye = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_l_ye")
            model.add_max_equality(oys, [ra["y"], rb["y"]])
            model.add_min_equality(oye, [ra["y"] + ra["d"], rb["y"] + rb["d"]])
            model.add(oye - oys >= min_shared).only_enforce_if(adj_l)

            model.add(rb["x"] + rb["w"] == ra["x"]).only_enforce_if(adj_r)
            oys2 = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_r_ys")
            oye2 = model.new_int_var(0, max_d, f"adj_{id_a}_{id_b}_r_ye")
            model.add_max_equality(oys2, [ra["y"], rb["y"]])
            model.add_min_equality(oye2, [ra["y"] + ra["d"], rb["y"] + rb["d"]])
            model.add(oye2 - oys2 >= min_shared).only_enforce_if(adj_r)

            model.add(ra["y"] + ra["d"] == rb["y"]).only_enforce_if(adj_t)
            oxs = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_t_xs")
            oxe = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_t_xe")
            model.add_max_equality(oxs, [ra["x"], rb["x"]])
            model.add_min_equality(oxe, [ra["x"] + ra["w"], rb["x"] + rb["w"]])
            model.add(oxe - oxs >= min_shared).only_enforce_if(adj_t)

            model.add(rb["y"] + rb["d"] == ra["y"]).only_enforce_if(adj_b)
            oxs2 = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_b_xs")
            oxe2 = model.new_int_var(0, max_w, f"adj_{id_a}_{id_b}_b_xe")
            model.add_max_equality(oxs2, [ra["x"], rb["x"]])
            model.add_min_equality(oxe2, [ra["x"] + ra["w"], rb["x"] + rb["w"]])
            model.add(oxe2 - oxs2 >= min_shared).only_enforce_if(adj_b)
            model.add_bool_or([adj_l, adj_r, adj_t, adj_b])

        area_deviations = []
        for room in rooms:
            rid = room["id"]
            target_grid = int(round(room["target_area"] * scale * scale))
            dev = model.new_int_var(0, max_w * max_d, f"{rid}_area_dev")
            diff = model.new_int_var(-max_w * max_d, max_w * max_d, f"{rid}_area_diff")
            model.add(diff == area_vars[rid] - target_grid)
            model.add_abs_equality(dev, diff)
            area_deviations.append(dev)

        total_area_dev = model.new_int_var(
            0, max_w * max_d * len(rooms), "total_area_dev"
        )
        model.add(total_area_dev == sum(area_deviations))

        seed_deviations = []
        if seed:
            for room in rooms:
                rid = room["id"]
                if rid not in seed:
                    continue
                s = seed[rid]
                for name, key, bound in (
                    ("x", "x", max_w),
                    ("y", "y", max_d),
                    ("w", "width", max_w),
                    ("d", "depth", max_d),
                ):
                    seed_value = int(round(s[key] * scale))
                    diff = model.new_int_var(-bound, bound, f"{rid}_{name}_seed_diff")
                    dev = model.new_int_var(0, bound, f"{rid}_{name}_seed_dev")
                    model.add(diff == vars_by_id[rid][name] - seed_value)
                    model.add_abs_equality(dev, diff)
                    seed_deviations.append(dev)

        seed_bound = max(1, (max_w + max_d) * 2 * len(rooms))
        total_seed_dev = model.new_int_var(0, seed_bound, "total_seed_dev")
        if seed_deviations:
            model.add(total_seed_dev == sum(seed_deviations))
        else:
            model.add(total_seed_dev == 0)

        pref_deviations = []
        for room in rooms:
            rid = room["id"]
            for name, key, bound in (
                ("w", "preferred_width", max_w),
                ("d", "preferred_depth", max_d),
            ):
                if room.get(key) is None:
                    continue
                preferred = int(round(float(room[key]) * scale))
                diff = model.new_int_var(-bound, bound, f"{rid}_{name}_pref_diff")
                dev = model.new_int_var(0, bound, f"{rid}_{name}_pref_dev")
                model.add(diff == vars_by_id[rid][name] - preferred)
                model.add_abs_equality(dev, diff)
                pref_deviations.append(dev)

        pref_bound = max(1, (max_w + max_d) * len(rooms))
        total_pref_dev = model.new_int_var(0, pref_bound, "total_pref_dev")
        if pref_deviations:
            model.add(total_pref_dev == sum(pref_deviations))
        else:
            model.add(total_pref_dev == 0)

        area_weight = seed_bound + pref_bound + 1
        model.minimize(
            total_area_dev * area_weight
            + total_pref_dev * 4
            + total_seed_dev
        )

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
