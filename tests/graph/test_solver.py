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
