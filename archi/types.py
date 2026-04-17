"""Shared Pydantic models for structured tool outputs.

FastMCP serializes these as both `structuredContent` (typed JSON) and
`content` text via __str__. Clients that understand structured output
read fields directly; legacy clients still see a clean human-readable line.

All response envelopes inherit from `ArchResult` so every tool returns the
same `svg + violations + violation_counts` baseline that `BuildingState.respond()`
historically attached. Tool-specific fields live on each subclass.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Domain enums — sourced from archi.graph.model.{RoomType,OpeningType}
# ---------------------------------------------------------------------------

RoomTypeStr = Literal[
    "kitchen", "living_room", "dining_room", "bedroom", "bathroom",
    "half_bath", "closet", "hallway", "garage", "laundry", "office",
    "mudroom", "pantry", "foyer", "utility",
]

OpeningTypeStr = Literal[
    "door", "window", "archway", "sliding_door", "pocket_door", "garage_door",
]


# ---------------------------------------------------------------------------
# Common envelope
# ---------------------------------------------------------------------------

class Violation(BaseModel):
    """A single rule/code violation reported by the LiveValidator."""

    model_config = ConfigDict(extra="allow")

    rule: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    node_id: Optional[str] = None


class ArchResult(BaseModel):
    """Base envelope returned by every arch_* tool.

    Carries the success/failure flag, the SVG floor-plan preview, and any
    code violations the LiveValidator has accumulated. Subclasses add the
    specific identifiers the tool produced.
    """

    model_config = ConfigDict(extra="allow")

    success: bool
    error: Optional[str] = Field(default=None, description="Failure reason when success=False")
    svg: Optional[str] = Field(default=None, description="SVG floor-plan preview, when applicable")
    violations: list[Violation] = Field(default_factory=list)
    violation_counts: dict[str, int] = Field(default_factory=dict)

    def __str__(self) -> str:
        if not self.success:
            return f"FAIL {self.error or 'unknown error'}"
        v = sum(self.violation_counts.values()) if self.violation_counts else 0
        suffix = f" ({v} violation(s))" if v else ""
        return f"OK{suffix}"


class BuildingCreated(ArchResult):
    building_id: Optional[str] = None

    def __str__(self) -> str:
        if not self.success:
            return super().__str__()
        return f"OK building_id={self.building_id}"


class FloorAdded(ArchResult):
    floor_id: Optional[str] = None
    level: Optional[int] = None

    def __str__(self) -> str:
        if not self.success:
            return super().__str__()
        return f"OK floor_id={self.floor_id}, level={self.level}"


class RoomAdded(ArchResult):
    room_id: Optional[str] = None
    room_type: Optional[str] = None
    level: Optional[int] = None

    def __str__(self) -> str:
        if not self.success:
            return super().__str__()
        return f"OK {self.room_type} '{self.room_id}' on level {self.level}"


class RoomRemoved(ArchResult):
    removed: Optional[str] = None

    def __str__(self) -> str:
        if not self.success:
            return super().__str__()
        return f"OK removed room '{self.removed}'"


class OpeningAdded(ArchResult):
    opening_id: Optional[str] = None
    opening_type: Optional[str] = None
    room_a: Optional[str] = None
    room_b: Optional[str] = None

    def __str__(self) -> str:
        if not self.success:
            return super().__str__()
        between = f"{self.room_a}↔{self.room_b}" if self.room_b else f"{self.room_a} (exterior)"
        return f"OK {self.opening_type} '{self.opening_id}' {between}"
