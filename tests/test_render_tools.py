# tests/test_render_tools.py
"""Integration tests for render MCP tools."""
import os
from unittest.mock import patch

from archi.graph.model import NodeType, RoomType
from archi.server import BuildingState


def _make_state_with_room():
    """Helper: create a BuildingState with one kitchen."""
    s = BuildingState()
    s.graph.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor_id = s.graph.add_node(NodeType.FLOOR, level=0)
    buildings = s.graph.get_all_nodes(NodeType.BUILDING)
    bldg_id = next(iter(buildings))
    s.graph.add_edge(bldg_id, floor_id, "contains")
    room_id = s.graph.add_node(
        NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
        area=120.0, width=10.0, depth=12.0,
    )
    s.graph.add_edge(floor_id, room_id, "contains")
    return s, room_id


def test_render_room_basic():
    from archi.tools.render import render_room_impl
    s, room_id = _make_state_with_room()
    with patch("archi.render.urlretrieve") as mock_retrieve:
        mock_retrieve.return_value = ("/tmp/test.png", {})
        result = render_room_impl(s, room_id)
    assert result["success"]
    assert result["image_path"]
    assert result["quality"] == "free"
    assert "kitchen" in result["prompt_used"].lower()


def test_render_room_not_found():
    from archi.tools.render import render_room_impl
    s = BuildingState()
    result = render_room_impl(s, "nonexistent")
    assert not result["success"]
    assert "not found" in result["error"]


def test_render_set_style():
    from archi.tools.render import set_style_impl
    s, room_id = _make_state_with_room()
    result = set_style_impl(s, room_id, "farmhouse")
    assert result["success"]
    assert result["style"] == "farmhouse"
    props = s.graph.get_node(room_id)
    assert props.get("render_style") == "farmhouse"


def test_render_explore_default_styles():
    from archi.tools.render import render_explore_impl
    s, room_id = _make_state_with_room()
    with patch("archi.render.urlretrieve") as mock_retrieve:
        mock_retrieve.return_value = ("/tmp/test.png", {})
        result = render_explore_impl(s, room_id)
    assert result["success"]
    assert len(result["renders"]) == 4
    styles_returned = [r["style"] for r in result["renders"]]
    assert "modern" in styles_returned
    assert "farmhouse" in styles_returned


def test_render_explore_custom_styles():
    from archi.tools.render import render_explore_impl
    s, room_id = _make_state_with_room()
    with patch("archi.render.urlretrieve") as mock_retrieve:
        mock_retrieve.return_value = ("/tmp/test.png", {})
        result = render_explore_impl(s, room_id, styles=["industrial", "bohemian"])
    assert result["success"]
    assert len(result["renders"]) == 2


def _make_state_with_floor():
    """Helper: BuildingState with 3 rooms on level 0."""
    s = BuildingState()
    bldg = s.graph.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor_id = s.graph.add_node(NodeType.FLOOR, level=0)
    s.graph.add_edge(bldg, floor_id, "contains")

    kitchen = s.graph.add_node(
        NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
        area=120.0, width=10.0, depth=12.0,
    )
    s.graph.add_edge(floor_id, kitchen, "contains")

    living = s.graph.add_node(
        NodeType.ROOM, room_type=RoomType.LIVING_ROOM, level=0,
        area=200.0, width=15.0, depth=13.0,
    )
    s.graph.add_edge(floor_id, living, "contains")

    bedroom = s.graph.add_node(
        NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
        area=150.0, width=12.0, depth=12.5,
    )
    s.graph.add_edge(floor_id, bedroom, "contains")

    return s, floor_id, [kitchen, living, bedroom]


def test_render_showcase_renders_all_rooms():
    from archi.tools.render import render_showcase_impl
    s, floor_id, room_ids = _make_state_with_floor()
    with patch("archi.render.urlretrieve") as mock_retrieve:
        mock_retrieve.return_value = ("/tmp/test.png", {})
        result = render_showcase_impl(s, level=0)
    assert result["success"]
    assert result["room_count"] == 3
    assert len(result["renders"]) == 3


def test_render_showcase_uses_saved_styles():
    from archi.tools.render import render_showcase_impl, set_style_impl
    s, floor_id, room_ids = _make_state_with_floor()
    set_style_impl(s, room_ids[0], "industrial")
    with patch("archi.render.urlretrieve") as mock_retrieve:
        mock_retrieve.return_value = ("/tmp/test.png", {})
        result = render_showcase_impl(s, level=0)
    assert result["success"]
    assert result["renders"][0]["style"] == "industrial"
