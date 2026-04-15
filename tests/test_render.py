"""Tests for archi.render — prompt composition and render logic."""
import os
import pytest
from unittest.mock import patch, MagicMock
from archi.graph.model import BuildingGraph, NodeType, RoomType, FurnitureType, OpeningType
from archi.render import RenderResult


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


def _mock_urlopen():
    """Mock urlopen to return fake image bytes."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"\x89PNG fake image data"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return patch("archi.render.urlopen", return_value=mock_resp)


def test_generate_image_free_builds_correct_url():
    """Free tier should call Pollinations with URL-encoded prompt."""
    from archi.render import generate_image

    with _mock_urlopen() as mock_open:
        result = generate_image(
            prompt="A modern kitchen",
            quality="free",
            output_path="/tmp/test.png",
        )
    assert result.success
    assert result.image_path == "/tmp/test.png"
    call_args = mock_open.call_args[0][0]
    url = call_args.full_url if hasattr(call_args, "full_url") else str(call_args)
    assert "pollinations.ai" in url
    assert "modern%20kitchen" in url or "modern+kitchen" in url


def test_generate_image_free_no_api_key_needed():
    """Free tier must not check for FAL_KEY."""
    from archi.render import generate_image

    with _mock_urlopen():
        with patch.dict(os.environ, {}, clear=True):
            result = generate_image(
                prompt="A bedroom",
                quality="free",
                output_path="/tmp/test.png",
            )
    assert result.success


def test_generate_image_fast_requires_fal_key():
    """Fast tier should fail with clear error when FAL_KEY is missing."""
    from archi.render import generate_image

    with patch.dict(os.environ, {}, clear=True):
        result = generate_image(prompt="A kitchen", quality="fast")
    assert not result.success
    assert "FAL_KEY" in result.error
    assert "fal.ai/dashboard/keys" in result.error


def test_generate_image_high_requires_fal_key():
    """High tier should fail with clear error when FAL_KEY is missing."""
    from archi.render import generate_image

    with patch.dict(os.environ, {}, clear=True):
        result = generate_image(prompt="A kitchen", quality="high")
    assert not result.success
    assert "FAL_KEY" in result.error


def test_compose_prompt_with_entering_from():
    """Walkthrough prompts should include spatial transition context."""
    from archi.render import compose_prompt
    g, room_id = _make_graph_with_room()
    prompt = compose_prompt(g, room_id, style="modern", entering_from="living room")
    assert "entering from the living room" in prompt.lower()


def test_generate_image_fast_calls_fal():
    """Fast tier should call _generate_fal with correct args."""
    from archi.render import generate_image

    with patch.dict(os.environ, {"FAL_KEY": "test-key-123"}):
        with patch("archi.render._generate_fal") as mock_fal:
            mock_fal.return_value = RenderResult(
                success=True, image_path="/tmp/test.png",
                image_url="https://fal.ai/result.png",
                prompt_used="A kitchen", quality="fast",
            )
            result = generate_image(
                prompt="A kitchen", quality="fast",
                output_path="/tmp/test.png",
            )
    assert result.success
    mock_fal.assert_called_once_with("A kitchen", "fast", "/tmp/test.png")
