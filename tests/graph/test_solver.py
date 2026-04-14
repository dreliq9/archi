import pytest


def test_treemap_single_room():
    """One room should fill the entire footprint."""
    from archi.graph.solver import TreemapSolver

    rooms = [{"id": "r1", "target_area": 200.0}]
    result = TreemapSolver.solve(
        footprint_width=20.0, footprint_depth=10.0, rooms=rooms
    )
    assert len(result) == 1
    r = result["r1"]
    assert r["x"] == pytest.approx(0.0)
    assert r["y"] == pytest.approx(0.0)
    assert r["width"] == pytest.approx(20.0)
    assert r["depth"] == pytest.approx(10.0)


def test_treemap_two_rooms_equal():
    """Two equal-area rooms should each get half the footprint."""
    from archi.graph.solver import TreemapSolver

    rooms = [
        {"id": "r1", "target_area": 100.0},
        {"id": "r2", "target_area": 100.0},
    ]
    result = TreemapSolver.solve(
        footprint_width=20.0, footprint_depth=10.0, rooms=rooms
    )
    assert len(result) == 2
    total_area = sum(r["width"] * r["depth"] for r in result.values())
    assert total_area == pytest.approx(200.0, rel=0.01)
    # No overlap
    placements = list(result.values())
    r1, r2 = placements[0], placements[1]
    overlap_x = max(0, min(r1["x"] + r1["width"], r2["x"] + r2["width"]) - max(r1["x"], r2["x"]))
    overlap_y = max(0, min(r1["y"] + r1["depth"], r2["y"] + r2["depth"]) - max(r1["y"], r2["y"]))
    assert overlap_x * overlap_y == pytest.approx(0.0, abs=0.01)


def test_treemap_three_rooms_unequal():
    """Three rooms with different areas. All fit, no overlap, areas proportional."""
    from archi.graph.solver import TreemapSolver

    rooms = [
        {"id": "living", "target_area": 250.0},
        {"id": "kitchen", "target_area": 150.0},
        {"id": "bedroom", "target_area": 120.0},
    ]
    result = TreemapSolver.solve(
        footprint_width=26.0, footprint_depth=20.0, rooms=rooms
    )
    assert len(result) == 3
    for rid, r in result.items():
        assert r["x"] >= -0.01
        assert r["y"] >= -0.01
        assert r["x"] + r["width"] <= 26.01
        assert r["y"] + r["depth"] <= 20.01
        assert r["width"] > 0
        assert r["depth"] > 0
    total_area = sum(r["width"] * r["depth"] for r in result.values())
    assert total_area == pytest.approx(26.0 * 20.0, rel=0.01)


def test_treemap_respects_area_ratios():
    """Room areas should be proportional to target areas."""
    from archi.graph.solver import TreemapSolver

    rooms = [
        {"id": "big", "target_area": 300.0},
        {"id": "small", "target_area": 100.0},
    ]
    result = TreemapSolver.solve(
        footprint_width=20.0, footprint_depth=20.0, rooms=rooms
    )
    big_area = result["big"]["width"] * result["big"]["depth"]
    small_area = result["small"]["width"] * result["small"]["depth"]
    assert big_area / small_area == pytest.approx(3.0, rel=0.05)


def test_treemap_empty_rooms():
    """No rooms should return empty dict."""
    from archi.graph.solver import TreemapSolver

    result = TreemapSolver.solve(
        footprint_width=20.0, footprint_depth=10.0, rooms=[]
    )
    assert result == {}


def test_csp_two_adjacent_rooms():
    """CSP should place two rooms that share a wall segment."""
    from archi.graph.solver import CSPSolver

    rooms = [
        {"id": "kitchen", "target_area": 150.0, "min_area": 120.0, "max_area": 180.0},
        {"id": "dining", "target_area": 120.0, "min_area": 100.0, "max_area": 150.0},
    ]
    adjacencies = [("kitchen", "dining")]
    result = CSPSolver.solve(
        footprint_width=20.0,
        footprint_depth=15.0,
        rooms=rooms,
        adjacencies=adjacencies,
    )
    assert result is not None, "CSP should find a solution"
    assert len(result) == 2
    for rid, r in result.items():
        assert r["x"] >= 0
        assert r["y"] >= 0
        assert r["x"] + r["width"] <= 20.0 + 0.01
        assert r["y"] + r["depth"] <= 15.0 + 0.01
    k = result["kitchen"]
    d = result["dining"]
    assert 120.0 <= k["width"] * k["depth"] <= 180.0 + 0.5
    assert 100.0 <= d["width"] * d["depth"] <= 150.0 + 0.5
    shares_x = (
        abs(k["x"] + k["width"] - d["x"]) < 0.5
        or abs(d["x"] + d["width"] - k["x"]) < 0.5
    )
    shares_y = (
        abs(k["y"] + k["depth"] - d["y"]) < 0.5
        or abs(d["y"] + d["depth"] - k["y"]) < 0.5
    )
    assert shares_x or shares_y, "Adjacent rooms must share a wall"


def test_csp_no_overlap():
    """CSP rooms must not overlap."""
    from archi.graph.solver import CSPSolver

    rooms = [
        {"id": "r1", "target_area": 100.0, "min_area": 80.0, "max_area": 120.0},
        {"id": "r2", "target_area": 100.0, "min_area": 80.0, "max_area": 120.0},
        {"id": "r3", "target_area": 100.0, "min_area": 80.0, "max_area": 120.0},
    ]
    result = CSPSolver.solve(
        footprint_width=20.0,
        footprint_depth=20.0,
        rooms=rooms,
        adjacencies=[],
    )
    assert result is not None
    placements = list(result.values())
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            a, b = placements[i], placements[j]
            overlap_x = max(0, min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"]))
            overlap_y = max(0, min(a["y"] + a["depth"], b["y"] + b["depth"]) - max(a["y"], b["y"]))
            assert overlap_x * overlap_y < 0.5, f"Rooms {i} and {j} overlap"


def test_csp_aspect_ratio():
    """CSP should respect aspect ratio constraints."""
    from archi.graph.solver import CSPSolver

    rooms = [
        {
            "id": "r1", "target_area": 200.0, "min_area": 180.0, "max_area": 220.0,
            "min_aspect_ratio": 0.5, "max_aspect_ratio": 2.0,
        },
    ]
    result = CSPSolver.solve(
        footprint_width=20.0,
        footprint_depth=20.0,
        rooms=rooms,
        adjacencies=[],
    )
    assert result is not None
    r = result["r1"]
    ratio = r["width"] / r["depth"]
    assert 0.5 <= ratio <= 2.0


def test_csp_returns_none_impossible():
    """If constraints are impossible, CSP returns None."""
    from archi.graph.solver import CSPSolver

    rooms = [
        {"id": "r1", "target_area": 500.0, "min_area": 500.0, "max_area": 600.0},
    ]
    result = CSPSolver.solve(
        footprint_width=10.0,
        footprint_depth=10.0,
        rooms=rooms,
        adjacencies=[],
    )
    assert result is None, "Should return None for impossible constraints"


def test_csp_seeded_from_treemap():
    """CSP can accept treemap output as initial seed positions."""
    from archi.graph.solver import CSPSolver, TreemapSolver

    rooms = [
        {"id": "living", "target_area": 250.0, "min_area": 220.0, "max_area": 280.0},
        {"id": "kitchen", "target_area": 150.0, "min_area": 130.0, "max_area": 170.0},
    ]
    seed = TreemapSolver.solve(
        footprint_width=20.0, footprint_depth=20.0, rooms=rooms,
    )
    result = CSPSolver.solve(
        footprint_width=20.0,
        footprint_depth=20.0,
        rooms=rooms,
        adjacencies=[("living", "kitchen")],
        seed=seed,
    )
    assert result is not None
    assert len(result) == 2
