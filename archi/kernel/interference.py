"""Interference checker — collision detection and clearance validation."""

from __future__ import annotations
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopoDS import TopoDS_Shape

def check_interference(shapes: list[TopoDS_Shape]) -> list[dict]:
    if len(shapes) < 2:
        return []
    collisions: list[dict] = []
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            common = BRepAlgoAPI_Common(shapes[i], shapes[j])
            if not common.IsDone():
                continue
            result_shape = common.Shape()
            props = GProp_GProps()
            BRepGProp.VolumeProperties_s(result_shape, props)
            vol = props.Mass()
            if vol > 0.01:
                collisions.append({"pair": (i, j), "volume": vol})
    return collisions

def check_clearance(furniture_shape: TopoDS_Shape, obstacle_shapes: list[TopoDS_Shape], required_clearance: float) -> list[dict]:
    violations: list[dict] = []
    for idx, obstacle in enumerate(obstacle_shapes):
        dist_calc = BRepExtrema_DistShapeShape(furniture_shape, obstacle)
        if not dist_calc.IsDone():
            continue
        distance = dist_calc.Value()
        if distance < required_clearance:
            violations.append({"obstacle_index": idx, "distance": distance, "required": required_clearance})
    return violations
