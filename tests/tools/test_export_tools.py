# tests/tools/test_export_tools.py
import pytest
import os

def _populated_state():
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room
    s = BuildingState()
    create_building(s, lot_width=50, lot_depth=40)
    add_floor(s, level=0, height=9.0)
    add_room(s, room_type="kitchen", level=0, area=120.0)
    add_room(s, room_type="living_room", level=0, area=200.0)
    return s

def test_export_svg():
    from archi.tools.export import export_svg
    s = _populated_state()
    result = export_svg(s, level=0)
    assert result["success"] is True
    assert result["format"] == "svg"
    assert "</svg>" in result["content"]

def test_export_dxf():
    from archi.tools.export import export_dxf
    s = _populated_state()
    result = export_dxf(s, level=0)
    assert result["success"] is True
    assert result["format"] == "dxf"
    assert os.path.exists(result["path"])
    os.unlink(result["path"])

def test_export_gltf():
    from archi.tools.export import export_gltf
    s = _populated_state()
    result = export_gltf(s)
    assert result["success"] is True
    assert result["format"] == "glb"
    assert os.path.exists(result["path"])
    os.unlink(result["path"])
