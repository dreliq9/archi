"""Canonical unit conventions and conversion helpers for archi.

The semantic/layout graph uses feet for linear floor-plan geometry and square
feet for room areas. Component-scale dimensions (openings, furniture,
clearances, structural spans) use inches. Keeping these domains explicit
prevents silent feet/inches comparisons at rule and export boundaries.
"""

from __future__ import annotations

FEET_TO_INCHES = 12.0
SQFT_TO_SQIN = FEET_TO_INCHES ** 2

LAYOUT_LENGTH_UNIT = "ft"
AREA_UNIT = "sqft"
COMPONENT_LENGTH_UNIT = "in"


def feet_to_inches(value: float) -> float:
    return value * FEET_TO_INCHES


def inches_to_feet(value: float) -> float:
    return value / FEET_TO_INCHES


def sqft_to_sqin(value: float) -> float:
    return value * SQFT_TO_SQIN


def sqin_to_sqft(value: float) -> float:
    return value / SQFT_TO_SQIN
