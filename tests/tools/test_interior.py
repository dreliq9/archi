import pytest

def _house_with_room():
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room
    s = BuildingState()
    create_building(s, lot_width=50, lot_depth=40)
    add_floor(s, level=0, height=9.0)
    r = add_room(s, room_type="living_room", level=0, area=200.0)
    return s, r["room_id"]

def test_place_furniture():
    from archi.tools.interior import place_furniture
    s, room_id = _house_with_room()
    result = place_furniture(s, room_id=room_id, furniture_type="sofa", x=12.0, y=24.0)
    assert result["success"] is True
    assert "furniture_id" in result
    assert "svg" in result

def test_place_furniture_custom_dims():
    from archi.tools.interior import place_furniture
    s, room_id = _house_with_room()
    result = place_furniture(s, room_id=room_id, furniture_type="desk", x=0.0, y=0.0, width=48.0, depth=24.0, height=30.0)
    assert result["success"] is True
    props = s.graph.get_node(result["furniture_id"])
    assert props["width"] == 48.0

def test_place_furniture_invalid_room():
    from archi.tools.interior import place_furniture
    from archi.server import BuildingState
    s = BuildingState()
    result = place_furniture(s, room_id="nonexistent", furniture_type="sofa", x=0.0, y=0.0)
    assert result["success"] is False

def test_remove_furniture():
    from archi.tools.interior import place_furniture, remove_furniture
    s, room_id = _house_with_room()
    r = place_furniture(s, room_id=room_id, furniture_type="sofa", x=12.0, y=24.0)
    result = remove_furniture(s, furniture_id=r["furniture_id"])
    assert result["success"] is True
