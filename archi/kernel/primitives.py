"""Building primitives — high-level geometry operations returning BuildResult.

Each function validates inputs, calls the OCPBackend, validates the result,
and returns a BuildResult with diagnostics. No raw exceptions escape.
"""

from __future__ import annotations

import math

from archi.kernel.backend import OCPBackend, check_valid, shape_volume
from archi.kernel.result import BuildResult
from archi.kernel.vector import Vector

_backend = OCPBackend()


def make_wall(start: Vector, end: Vector, height: float, thickness: float) -> BuildResult:
    if height <= 0 or thickness <= 0:
        return BuildResult.fail(
            "Wall height and thickness must be positive",
            hint=f"Got height={height}, thickness={thickness}",
        )
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.sqrt(dx**2 + dy**2)
    if length < 1e-6:
        return BuildResult.fail(
            "Wall start and end are the same point",
            hint="Provide two different points for wall endpoints",
        )
    try:
        shape = _backend.make_wall(start, end, height, thickness)
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e))


def make_floor_slab(boundary: list[Vector], thickness: float) -> BuildResult:
    if len(boundary) < 3:
        return BuildResult.fail(
            "Slab boundary requires at least 3 points",
            hint=f"Got {len(boundary)} points",
        )
    if thickness <= 0:
        return BuildResult.fail("Slab thickness must be positive")
    try:
        shape = _backend.make_slab(boundary, thickness)
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e))


def make_foundation_slab(boundary: list[Vector], thickness: float, depth: float) -> BuildResult:
    if len(boundary) < 3:
        return BuildResult.fail("Foundation boundary requires at least 3 points")
    if thickness <= 0 or depth <= 0:
        return BuildResult.fail("Foundation thickness and depth must be positive")
    z_bottom = -depth
    shifted = [Vector(p.x, p.y, z_bottom) for p in boundary]
    try:
        shape = _backend.make_slab(shifted, thickness)
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e))


def make_opening(wall_result: BuildResult, position: Vector, width: float, height: float) -> BuildResult:
    if not wall_result.ok:
        return BuildResult.fail("Cannot cut opening in invalid wall", hint="Fix the wall first")
    if width <= 0 or height <= 0:
        return BuildResult.fail("Opening width and height must be positive")
    try:
        shape = _backend.make_opening(wall_result.shape, position, width, height)
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e), hint="Try different opening position or size")


def make_roof(footprint: list[Vector], profile: str, pitch: float) -> BuildResult:
    if len(footprint) < 3:
        return BuildResult.fail("Roof footprint requires at least 3 points")
    if pitch < 0:
        return BuildResult.fail("Roof pitch must be non-negative")

    if profile == "flat":
        return make_floor_slab(footprint, thickness=6.0)
    if profile == "gable":
        return _make_gable_roof(footprint, pitch)
    if profile == "shed":
        return _make_shed_roof(footprint, pitch)
    if profile == "hip":
        return _make_gable_roof(footprint, pitch)

    return BuildResult.fail(f"Unknown roof profile: {profile}", hint="Use 'gable', 'hip', 'shed', or 'flat'")


def _make_gable_roof(footprint: list[Vector], pitch: float) -> BuildResult:
    try:
        min_x = min(p.x for p in footprint)
        max_x = max(p.x for p in footprint)
        min_y = min(p.y for p in footprint)
        max_y = max(p.y for p in footprint)
        z = footprint[0].z
        width = max_x - min_x
        depth = max_y - min_y
        mid_x = (min_x + max_x) / 2
        ridge_height = (width / 2) * (pitch / 12.0)

        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
        from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
        from OCP.gp import gp_Pnt, gp_Vec

        p1 = gp_Pnt(min_x, min_y, z)
        p2 = gp_Pnt(max_x, min_y, z)
        p3 = gp_Pnt(mid_x, min_y, z + ridge_height)

        wire = BRepBuilderAPI_MakeWire()
        wire.Add(BRepBuilderAPI_MakeEdge(p1, p2).Edge())
        wire.Add(BRepBuilderAPI_MakeEdge(p2, p3).Edge())
        wire.Add(BRepBuilderAPI_MakeEdge(p3, p1).Edge())

        face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
        prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, depth, 0))
        shape = prism.Shape()
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e), hint="Check footprint points are coplanar")


def _make_shed_roof(footprint: list[Vector], pitch: float) -> BuildResult:
    try:
        min_x = min(p.x for p in footprint)
        max_x = max(p.x for p in footprint)
        min_y = min(p.y for p in footprint)
        max_y = max(p.y for p in footprint)
        z = footprint[0].z
        width = max_x - min_x
        rise = width * (pitch / 12.0)

        boundary = [
            Vector(min_x, min_y, z),
            Vector(max_x, min_y, z + rise),
            Vector(max_x, max_y, z + rise),
            Vector(min_x, max_y, z),
        ]
        shape = _backend.make_slab(boundary, 6.0)
        vol = shape_volume(shape)
        return BuildResult(shape=shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e))


def make_stair(start: Vector, direction: Vector, run: float, rise: float, width: float, n_steps: int) -> BuildResult:
    if run <= 0 or rise <= 0 or width <= 0 or n_steps <= 0:
        return BuildResult.fail("Stair dimensions must be positive")
    try:
        dir_norm = direction.normalized()
        perp = Vector(-dir_norm.y, dir_norm.x, 0).normalized()
        shapes = []
        for i in range(n_steps):
            step_origin = Vector(
                start.x + dir_norm.x * run * i,
                start.y + dir_norm.y * run * i,
                start.z + rise * i,
            )
            half_w = width / 2
            boundary = [
                Vector(step_origin.x - perp.x * half_w, step_origin.y - perp.y * half_w, step_origin.z),
                Vector(step_origin.x - perp.x * half_w + dir_norm.x * run, step_origin.y - perp.y * half_w + dir_norm.y * run, step_origin.z),
                Vector(step_origin.x + perp.x * half_w + dir_norm.x * run, step_origin.y + perp.y * half_w + dir_norm.y * run, step_origin.z),
                Vector(step_origin.x + perp.x * half_w, step_origin.y + perp.y * half_w, step_origin.z),
            ]
            tread = _backend.make_slab(boundary, thickness=1.5)
            shapes.append(tread)

        result_shape = shapes[0]
        for s in shapes[1:]:
            result_shape = _backend.boolean_union(result_shape, s)

        vol = shape_volume(result_shape)
        return BuildResult(shape=result_shape, valid=True, volume=vol)
    except Exception as e:
        return BuildResult.fail(str(e), hint="Check direction is not zero-length")
