# tests/test_integration_plan4.py
"""Integration tests — Plan 4: MCP server full pipeline demo."""
import pytest
import os

def test_demo_3bedroom_ranch():
    """Demo scenario 1: Design a 3-bedroom ranch house."""
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room, add_opening
    from archi.tools.query import check_code, get_building, get_plan, list_rooms

    s = BuildingState()
    b = create_building(s, lot_width=80, lot_depth=120,
                         setbacks={"front": 25, "back": 20, "left": 10, "right": 10}, stories=1)
    assert b["success"]

    f = add_floor(s, level=0, height=9.0)
    assert f["success"]

    living = add_room(s, room_type="living_room", level=0, area=250.0)
    assert living["success"]
    kitchen = add_room(s, room_type="kitchen", level=0, area=150.0, adjacent_to=[living["room_id"]])
    assert kitchen["success"]
    dining = add_room(s, room_type="dining_room", level=0, area=120.0, adjacent_to=[kitchen["room_id"]])
    assert dining["success"]
    bed1 = add_room(s, room_type="bedroom", level=0, area=120.0)
    bed2 = add_room(s, room_type="bedroom", level=0, area=120.0)
    bed3 = add_room(s, room_type="bedroom", level=0, area=100.0)
    bath1 = add_room(s, room_type="bathroom", level=0, area=50.0)
    bath2 = add_room(s, room_type="bathroom", level=0, area=40.0)
    hallway = add_room(s, room_type="hallway", level=0, area=60.0)

    add_opening(s, opening_type="door", width=36, height=80, room_a=living["room_id"], exterior=True)
    for room_result in [kitchen, dining, bed1, bed2, bed3, bath1, bath2]:
        add_opening(s, opening_type="door", width=36, height=80,
                    room_a=hallway["room_id"], room_b=room_result["room_id"])
    add_opening(s, opening_type="door", width=36, height=80,
                room_a=living["room_id"], room_b=hallway["room_id"])

    building = get_building(s)
    assert building["room_count"] == 9

    rooms = list_rooms(s, level=0)
    assert len(rooms["rooms"]) == 9

    plan = get_plan(s, level=0)
    assert "</svg>" in plan["svg"]

    code = check_code(s)
    assert isinstance(code["violations"], list)


def test_demo_furnish_room():
    """Demo scenario 2: Furnish a living room."""
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room
    from archi.tools.interior import place_furniture
    from archi.tools.query import get_room

    s = BuildingState()
    create_building(s, lot_width=50, lot_depth=40)
    add_floor(s, level=0, height=9.0)
    r = add_room(s, room_type="living_room", level=0, area=200.0)

    sofa = place_furniture(s, room_id=r["room_id"], furniture_type="sofa", x=12.0, y=24.0)
    assert sofa["success"]
    table = place_furniture(s, room_id=r["room_id"], furniture_type="coffee_table", x=30.0, y=60.0)
    assert table["success"]
    tv = place_furniture(s, room_id=r["room_id"], furniture_type="tv_stand", x=60.0, y=6.0)
    assert tv["success"]

    room = get_room(s, room_id=r["room_id"])
    assert len(room["furniture"]) == 3


def test_demo_full_export():
    """Demo scenario 3: Build and export."""
    from archi.server import BuildingState
    from archi.tools.arch import create_building, add_floor, add_room
    from archi.tools.export import export_svg, export_dxf, export_gltf

    s = BuildingState()
    create_building(s, lot_width=50, lot_depth=40)
    add_floor(s, level=0, height=9.0)
    add_room(s, room_type="kitchen", level=0, area=120.0)
    add_room(s, room_type="living_room", level=0, area=200.0)
    add_room(s, room_type="bedroom", level=0, area=120.0)

    svg_result = export_svg(s, level=0)
    assert svg_result["success"]
    assert "</svg>" in svg_result["content"]

    dxf_result = export_dxf(s, level=0)
    assert dxf_result["success"]
    assert os.path.exists(dxf_result["path"])
    os.unlink(dxf_result["path"])

    gltf_result = export_gltf(s)
    assert gltf_result["success"]
    assert os.path.exists(gltf_result["path"])
    os.unlink(gltf_result["path"])
