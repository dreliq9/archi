import pytest

def _populated_state():
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room, add_opening
    s = BuildingState()
    create_building(s, lot_width=80, lot_depth=120)
    add_floor(s, level=0, height=9.0)
    r1 = add_room(s, room_type="kitchen", level=0, area=120.0)
    r2 = add_room(s, room_type="living_room", level=0, area=200.0, adjacent_to=[r1["room_id"]])
    add_opening(s, opening_type="door", width=36, height=80, room_a=r1["room_id"], room_b=r2["room_id"])
    add_opening(s, opening_type="door", width=36, height=80, room_a=r1["room_id"], exterior=True)
    return s, r1["room_id"], r2["room_id"]

def test_get_plan():
    from archi.tools.query import get_plan
    s, _, _ = _populated_state()
    result = get_plan(s, level=0)
    assert "svg" in result
    assert "</svg>" in result["svg"]

def test_get_room():
    from archi.tools.query import get_room
    s, kitchen_id, _ = _populated_state()
    result = get_room(s, room_id=kitchen_id)
    assert result["room_type"] == "kitchen"
    assert result["area"] > 0

def test_get_building():
    from archi.tools.query import get_building
    s, _, _ = _populated_state()
    result = get_building(s)
    assert result["lot_width"] == 80
    assert result["room_count"] == 2

def test_check_code():
    from archi.tools.query import check_code
    s, _, _ = _populated_state()
    result = check_code(s)
    assert "violations" in result
    assert "counts" in result
    assert isinstance(result["violations"], list)

def test_get_violations():
    from archi.tools.query import get_violations
    s, _, _ = _populated_state()
    result = get_violations(s)
    assert "violations" in result
    assert isinstance(result["violations"], list)

def test_list_rooms():
    from archi.tools.query import list_rooms
    s, _, _ = _populated_state()
    result = list_rooms(s, level=0)
    assert len(result["rooms"]) == 2
    assert all("room_type" in r for r in result["rooms"])
    assert all("area" in r for r in result["rooms"])
