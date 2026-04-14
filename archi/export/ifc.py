"""IFC export — architect handoff format. Requires ifcopenshell (optional)."""

from __future__ import annotations
from pathlib import Path

try:
    import ifcopenshell
    import ifcopenshell.api
    HAS_IFC = True
except ImportError:
    HAS_IFC = False

from archi.graph.model import BuildingGraph, NodeType

def export_to_ifc(graph: BuildingGraph, output_path: str | Path = "building.ifc", schema: str = "IFC4") -> None:
    if not HAS_IFC:
        raise ImportError("ifcopenshell is required for IFC export. Install with: pip install ifcopenshell")

    model = ifcopenshell.file(schema=schema)
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Archi Export")
    context = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    ifcopenshell.api.run("unit.assign_unit", model)

    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    ifcopenshell.api.run("aggregate.assign_object", model, products=[site], relating_object=project)

    buildings = graph.get_all_nodes(NodeType.BUILDING)
    building_name = "Building"
    for bid, bprops in buildings.items():
        building_name = bprops.get("name", "Building")
        break

    ifc_building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name=building_name)
    ifcopenshell.api.run("aggregate.assign_object", model, products=[ifc_building], relating_object=site)

    floors = graph.get_all_nodes(NodeType.FLOOR)
    for floor_id, floor_props in floors.items():
        level = floor_props.get("level", 0)
        storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name=f"Level {level}")
        ifcopenshell.api.run("aggregate.assign_object", model, products=[storey], relating_object=ifc_building)

        for room_id in graph.get_rooms_on_floor(floor_id):
            room_props = graph.get_node(room_id)
            room_type = room_props.get("room_type")
            room_name = room_type.value.replace("_", " ").title() if room_type else "Room"
            space = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSpace", name=room_name)
            ifcopenshell.api.run("spatial.assign_container", model, products=[space], relating_structure=storey)

    model.write(str(output_path))
