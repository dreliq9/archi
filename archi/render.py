"""AI image generation for interior design renders.

Supports three quality tiers:
- "free": Pollinations.ai (no API key needed)
- "fast": fal.ai Flux dev (requires FAL_KEY)
- "high": fal.ai Flux Pro (requires FAL_KEY)
"""

from __future__ import annotations

import os
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlretrieve

from archi.graph.model import BuildingGraph, NodeType, OpeningType


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------

RENDER_DIR = Path.home() / "Desktop" / "archi" / "renders"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

STYLES = [
    "modern", "farmhouse", "mid-century", "scandinavian",
    "industrial", "minimalist", "traditional", "bohemian",
]

DEFAULT_STYLE = "modern"


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------

def _get_openings_for_room(graph: BuildingGraph, room_id: str) -> list[dict]:
    """Find all openings connected to a room (edges go opening → room)."""
    openings = []
    for nid, props in graph.get_all_nodes(NodeType.OPENING).items():
        for edge in graph.get_edges(nid):
            if edge["target"] == room_id and edge["edge_type"] == "connects":
                openings.append(props)
                break
    return openings


def compose_prompt(
    graph: BuildingGraph,
    room_id: str,
    style: str = DEFAULT_STYLE,
    entering_from: str | None = None,
) -> str:
    """Build an image generation prompt from room graph data."""
    props = graph.get_node(room_id)
    room_type = props.get("room_type")
    room_name = room_type.value.replace("_", " ") if room_type else "room"
    width = props.get("width", 0)
    depth = props.get("depth", 0)

    header = (
        f"Interior photograph of a {room_name}, "
        f"{width}ft x {depth}ft, {style} style."
    )
    if entering_from:
        header += f" Viewed entering from the {entering_from}."

    parts = [header]

    # Furniture
    furniture_ids = graph.get_furniture_in_room(room_id)
    if furniture_ids:
        descriptions = []
        for fid in furniture_ids:
            fprops = graph.get_node(fid)
            ft = fprops.get("furniture_type")
            name = ft.value.replace("_", " ") if ft else "furniture"
            descriptions.append(name)
        parts.append(", ".join(descriptions) + ".")

    # Openings
    openings = _get_openings_for_room(graph, room_id)
    if openings:
        opening_descs = []
        for oprops in openings:
            ot = oprops.get("opening_type")
            name = ot.value.replace("_", " ") if ot else "opening"
            opening_descs.append(name)
        parts.append(", ".join(opening_descs) + ".")

    parts.append("Photorealistic interior design photography, natural lighting.")
    return " ".join(parts)
