"""BackendProtocol and OCPBackend — direct OCP geometry operations.

No CadQuery. No build123d. Direct OCP imports. Swappable via protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.TopoDS import TopoDS_Shape
from OCP.gp import gp_Vec

from archi.kernel.vector import Vector


@runtime_checkable
class BackendProtocol(Protocol):
    """Interface for geometry backends. Swap implementations without changing callers."""

    def make_slab(self, boundary: list[Vector], thickness: float) -> TopoDS_Shape: ...
    def make_wall(self, start: Vector, end: Vector, height: float, thickness: float) -> TopoDS_Shape: ...
    def make_opening(self, wall_shape: TopoDS_Shape, position: Vector, width: float, height: float) -> TopoDS_Shape: ...
    def boolean_cut(self, base: TopoDS_Shape, tool: TopoDS_Shape) -> TopoDS_Shape: ...
    def boolean_union(self, a: TopoDS_Shape, b: TopoDS_Shape) -> TopoDS_Shape: ...


class OCPBackend:
    """Direct OCP implementation of BackendProtocol."""

    def make_slab(self, boundary: list[Vector], thickness: float) -> TopoDS_Shape:
        if len(boundary) < 3:
            raise ValueError("Slab boundary requires at least 3 points")

        wire_builder = BRepBuilderAPI_MakeWire()
        for i in range(len(boundary)):
            p1 = boundary[i].to_pnt()
            p2 = boundary[(i + 1) % len(boundary)].to_pnt()
            edge = BRepBuilderAPI_MakeEdge(p1, p2).Edge()
            wire_builder.Add(edge)

        wire = wire_builder.Wire()
        face = BRepBuilderAPI_MakeFace(wire).Face()
        prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, thickness))
        return prism.Shape()

    def make_wall(self, start: Vector, end: Vector, height: float, thickness: float) -> TopoDS_Shape:
        dx = end.x - start.x
        dy = end.y - start.y
        wall_length = (dx**2 + dy**2) ** 0.5

        if wall_length < 1e-6:
            raise ValueError("Wall start and end are the same point")

        nx = -dy / wall_length * (thickness / 2)
        ny = dx / wall_length * (thickness / 2)

        boundary = [
            Vector(start.x + nx, start.y + ny, start.z),
            Vector(end.x + nx, end.y + ny, start.z),
            Vector(end.x - nx, end.y - ny, start.z),
            Vector(start.x - nx, start.y - ny, start.z),
        ]

        return self.make_slab(boundary, height)

    def make_opening(self, wall_shape: TopoDS_Shape, position: Vector, width: float, height: float) -> TopoDS_Shape:
        half_w = width / 2
        tool_origin = Vector(position.x - half_w, position.y - 6, position.z)
        tool_box = BRepPrimAPI_MakeBox(tool_origin.to_pnt(), width, 12.0, height).Shape()
        return self.boolean_cut(wall_shape, tool_box)

    def boolean_cut(self, base: TopoDS_Shape, tool: TopoDS_Shape) -> TopoDS_Shape:
        cut = BRepAlgoAPI_Cut(base, tool)
        if not cut.IsDone():
            raise RuntimeError("Boolean cut failed")
        return cut.Shape()

    def boolean_union(self, a: TopoDS_Shape, b: TopoDS_Shape) -> TopoDS_Shape:
        fuse = BRepAlgoAPI_Fuse(a, b)
        if not fuse.IsDone():
            raise RuntimeError("Boolean union failed")
        return fuse.Shape()


def shape_volume(shape: TopoDS_Shape) -> float:
    """Compute volume of an OCP shape in cubic units."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def check_valid(shape: TopoDS_Shape) -> dict:
    """Check if an OCP shape is geometrically valid."""
    analyzer = BRepCheck_Analyzer(shape)
    return {"is_valid": analyzer.IsValid()}
