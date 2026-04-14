"""Parametric furniture generators — simplified bounding geometry."""

from __future__ import annotations
from archi.kernel.backend import OCPBackend, shape_volume
from archi.kernel.result import BuildResult
from archi.kernel.vector import Vector

_backend = OCPBackend()

FURNITURE_DEFAULTS: dict[str, dict] = {
    "sofa":          {"width": 84, "depth": 36, "height": 34, "clearance": {"front": 36, "sides": 6}},
    "loveseat":      {"width": 60, "depth": 36, "height": 34, "clearance": {"front": 36, "sides": 6}},
    "armchair":      {"width": 36, "depth": 34, "height": 34, "clearance": {"front": 24, "sides": 6}},
    "dining_table":  {"width": 72, "depth": 36, "height": 30, "clearance": {"front": 36, "sides": 36}},
    "desk":          {"width": 60, "depth": 30, "height": 30, "clearance": {"front": 24, "sides": 6}},
    "bed_king":      {"width": 76, "depth": 80, "height": 24, "clearance": {"front": 36, "sides": 24}},
    "bed_queen":     {"width": 60, "depth": 80, "height": 24, "clearance": {"front": 36, "sides": 24}},
    "bed_twin":      {"width": 38, "depth": 75, "height": 24, "clearance": {"front": 36, "sides": 24}},
    "dresser":       {"width": 60, "depth": 18, "height": 34, "clearance": {"front": 36, "sides": 3}},
    "bookshelf":     {"width": 36, "depth": 12, "height": 72, "clearance": {"front": 24, "sides": 3}},
    "coffee_table":  {"width": 48, "depth": 24, "height": 18, "clearance": {"front": 18, "sides": 18}},
    "end_table":     {"width": 24, "depth": 24, "height": 24, "clearance": {"front": 6,  "sides": 3}},
    "tv_stand":      {"width": 60, "depth": 18, "height": 24, "clearance": {"front": 72, "sides": 6}},
    "nightstand":    {"width": 24, "depth": 18, "height": 24, "clearance": {"front": 6,  "sides": 3}},
    "cabinet":       {"width": 36, "depth": 18, "height": 36, "clearance": {"front": 24, "sides": 3}},
    "toilet":        {"width": 18, "depth": 28, "height": 16, "clearance": {"front": 21, "sides": 15}},
    "sink":          {"width": 24, "depth": 20, "height": 34, "clearance": {"front": 21, "sides": 6}},
    "bathtub":       {"width": 30, "depth": 60, "height": 20, "clearance": {"front": 24, "sides": 6}},
    "shower":        {"width": 36, "depth": 36, "height": 84, "clearance": {"front": 24, "sides": 6}},
    "refrigerator":  {"width": 36, "depth": 30, "height": 70, "clearance": {"front": 36, "sides": 3}},
    "range":         {"width": 30, "depth": 26, "height": 36, "clearance": {"front": 36, "sides": 6}},
}

_DEFAULT_CLEARANCE = {"front": 12, "sides": 6}


def make_furniture(furniture_type: str, width: float, depth: float, height: float, style: str = "modern") -> BuildResult:
    if width <= 0 or depth <= 0 or height <= 0:
        return BuildResult.fail("Furniture dimensions must be positive", hint=f"Got width={width}, depth={depth}, height={height}")
    try:
        boundary = [Vector(0, 0, 0), Vector(width, 0, 0), Vector(width, depth, 0), Vector(0, depth, 0)]
        shape = _backend.make_slab(boundary, height)
        vol = shape_volume(shape)
        defaults = FURNITURE_DEFAULTS.get(furniture_type, {})
        clearance = defaults.get("clearance", _DEFAULT_CLEARANCE)
        return BuildResult(shape=shape, valid=True, volume=vol, diagnostics={"furniture_type": furniture_type, "style": style, "clearance": clearance})
    except Exception as e:
        return BuildResult.fail(str(e))
