"""Tests for archi.render — prompt composition and render logic."""
import pytest
from archi.graph.model import BuildingGraph, NodeType, RoomType, FurnitureType, OpeningType


def _make_graph_with_room():
    """Helper: build → floor → kitchen with furniture and window."""
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=80, lot_depth=120)
    floor = g.add_node(NodeType.FLOOR, level=0, floor_to_floor_height=108)
    g.add_edge(bldg, floor, "contains")
    kitchen = g.add_node(
        NodeType.ROOM, room_type=RoomType.KITCHEN, level=0,
        area=120.0, width=10.0, depth=12.0,
    )
    g.add_edge(floor, kitchen, "contains")
    fridge = g.add_node(
        NodeType.FURNITURE, furniture_type=FurnitureType.CABINET,
        width=36, depth=24, height=70, x=0, y=0, style="modern",
    )
    g.add_edge(kitchen, fridge, "contains")
    window = g.add_node(
        NodeType.OPENING, opening_type=OpeningType.WINDOW,
        width=48, height=36, exterior=True,
    )
    g.add_edge(window, kitchen, "connects")
    return g, kitchen


def test_compose_prompt_basic():
    from archi.render import compose_prompt
    g, room_id = _make_graph_with_room()
    prompt = compose_prompt(g, room_id)
    assert "kitchen" in prompt.lower()
    assert "10" in prompt and "12" in prompt
    assert "modern" in prompt.lower()


def test_compose_prompt_with_style():
    from archi.render import compose_prompt
    g, room_id = _make_graph_with_room()
    prompt = compose_prompt(g, room_id, style="farmhouse")
    assert "farmhouse" in prompt.lower()


def test_compose_prompt_includes_furniture():
    from archi.render import compose_prompt
    g, room_id = _make_graph_with_room()
    prompt = compose_prompt(g, room_id)
    assert "cabinet" in prompt.lower()


def test_compose_prompt_includes_openings():
    from archi.render import compose_prompt
    g, room_id = _make_graph_with_room()
    prompt = compose_prompt(g, room_id)
    assert "window" in prompt.lower()


def test_compose_prompt_empty_room():
    from archi.render import compose_prompt
    g = BuildingGraph()
    bldg = g.add_node(NodeType.BUILDING, lot_width=50, lot_depth=50)
    floor = g.add_node(NodeType.FLOOR, level=0)
    g.add_edge(bldg, floor, "contains")
    room = g.add_node(
        NodeType.ROOM, room_type=RoomType.BEDROOM, level=0,
        area=150.0, width=10.0, depth=15.0,
    )
    g.add_edge(floor, room, "contains")
    prompt = compose_prompt(g, room)
    assert "bedroom" in prompt.lower()
    assert "10" in prompt and "15" in prompt
