"""Pure Python vector with OCP geometry bridges.

Public API uses Vector exclusively — raw OCP types (gp_Pnt, gp_Vec, gp_Dir)
never appear in function signatures outside this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from OCP.gp import gp_Dir, gp_Pnt, gp_Vec


@dataclass(frozen=True, slots=True)
class Vector:
    """3D vector for building geometry. Immutable."""

    x: float
    y: float
    z: float

    @property
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> Vector:
        ln = self.length
        if ln < 1e-12:
            raise ValueError("Cannot normalize zero-length vector")
        return Vector(self.x / ln, self.y / ln, self.z / ln)

    def dot(self, other: Vector) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector) -> Vector:
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def angle(self, other: Vector) -> float:
        d = self.dot(other) / (self.length * other.length)
        d = max(-1.0, min(1.0, d))
        return math.acos(d)

    def __add__(self, other: Vector) -> Vector:
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector) -> Vector:
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector:
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector:
        return self.__mul__(scalar)

    def __neg__(self) -> Vector:
        return Vector(-self.x, -self.y, -self.z)

    def __repr__(self) -> str:
        return f"Vector({self.x}, {self.y}, {self.z})"

    # --- OCP bridges ---

    def to_pnt(self) -> gp_Pnt:
        return gp_Pnt(self.x, self.y, self.z)

    def to_vec(self) -> gp_Vec:
        return gp_Vec(self.x, self.y, self.z)

    def to_dir(self) -> gp_Dir:
        n = self.normalized()
        return gp_Dir(n.x, n.y, n.z)

    @classmethod
    def from_pnt(cls, pnt: gp_Pnt) -> Vector:
        return cls(pnt.X(), pnt.Y(), pnt.Z())

    @classmethod
    def from_vec(cls, vec: gp_Vec) -> Vector:
        return cls(vec.X(), vec.Y(), vec.Z())
