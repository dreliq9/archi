import pytest

def _fresh_state():
    from archi.server import BuildingState
    return BuildingState()

def test_create_building():
    from archi.tools.arch import create_building
    s = _fresh_state()
    result = create_building(s, lot_width=80, lot_depth=120,
                              setbacks={"front": 25, "back": 20, "left": 10, "right": 10}, stories=1)
    assert result["success"] is True
    assert "building_id" in result
    assert "svg" in result

def test_add_floor():
    from archi.tools.arch import create_building, add_floor
    s = _fresh_state()
    create_building(s, lot_width=80, lot_depth=120)
    result = add_floor(s, level=0, height=9.0)
    assert result["success"] is True
    assert "floor_id" in result

def test_add_room():
    from archi.tools.arch import create_building, add_floor, add_room
    s = _fresh_state()
    create_building(s, lot_width=80, lot_depth=120)
    add_floor(s, level=0, height=9.0)
    result = add_room(s, room_type="kitchen", level=0, area=120.0)
    assert result["success"] is True
    assert "room_id" in result
    assert "svg" in result

def test_add_room_with_adjacency():
    from archi.tools.arch import create_building, add_floor, add_room
    s = _fresh_state()
    create_building(s, lot_width=80, lot_depth=120)
    add_floor(s, level=0, height=9.0)
    r1 = add_room(s, room_type="kitchen", level=0, area=120.0)
    r2 = add_room(s, room_type="living_room", level=0, area=200.0, adjacent_to=[r1["room_id"]])
    assert r2["success"] is True
    adj = s.graph.get_adjacent_rooms(r2["room_id"])
    assert r1["room_id"] in adj

def test_remove_room():
    from archi.tools.arch import create_building, add_floor, add_room, remove_room
    s = _fresh_state()
    create_building(s, lot_width=80, lot_depth=120)
    add_floor(s, level=0, height=9.0)
    r = add_room(s, room_type="bedroom", level=0, area=120.0)
    result = remove_room(s, room_id=r["room_id"])
    assert result["success"] is True

def test_add_opening():
    from archi.tools.arch import create_building, add_floor, add_room, add_opening
    s = _fresh_state()
    create_building(s, lot_width=80, lot_depth=120)
    add_floor(s, level=0, height=9.0)
    r1 = add_room(s, room_type="kitchen", level=0, area=120.0)
    r2 = add_room(s, room_type="dining_room", level=0, area=100.0, adjacent_to=[r1["room_id"]])
    result = add_opening(s, opening_type="door", width=36, height=80,
                          room_a=r1["room_id"], room_b=r2["room_id"])
    assert result["success"] is True
    assert "opening_id" in result

def test_add_room_triggers_layout():
    from archi.tools.arch import create_building, add_floor, add_room
    s = _fresh_state()
    create_building(s, lot_width=50, lot_depth=40)
    add_floor(s, level=0, height=9.0)
    add_room(s, room_type="kitchen", level=0, area=120.0)
    r = add_room(s, room_type="living_room", level=0, area=200.0)
    room_props = s.graph.get_node(r["room_id"])
    assert "x" in room_props
    assert "width" in room_props
    assert room_props["width"] > 0
