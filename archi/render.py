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


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RenderResult:
    success: bool
    image_path: str | None = None
    image_url: str | None = None
    prompt_used: str = ""
    estimated_cost: float = 0.0
    quality: str = "free"
    error: str | None = None


# ---------------------------------------------------------------------------
# Pollinations.ai (free tier)
# ---------------------------------------------------------------------------

_POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"


def _generate_pollinations(prompt: str, output_path: str) -> RenderResult:
    """Generate an image via Pollinations.ai — free, no key needed."""
    encoded = quote(prompt)
    url = f"{_POLLINATIONS_BASE}/{encoded}?width=1024&height=768&nologo=true"
    try:
        urlretrieve(url, output_path)
        return RenderResult(
            success=True,
            image_path=output_path,
            image_url=url,
            prompt_used=prompt,
            estimated_cost=0.0,
            quality="free",
        )
    except Exception as e:
        return RenderResult(success=False, error=str(e), prompt_used=prompt)


# ---------------------------------------------------------------------------
# fal.ai (paid tiers)
# ---------------------------------------------------------------------------

_FAL_ENDPOINTS = {
    "fast": "fal-ai/flux/dev",
    "high": "fal-ai/flux-pro/v1.1",
}

_FAL_COST_PER_IMAGE = {
    "fast": 0.01,
    "high": 0.05,
}


def _generate_fal(prompt: str, quality: str, output_path: str) -> RenderResult:
    """Generate an image via fal.ai Flux models."""
    try:
        import fal_client
    except ImportError:
        return RenderResult(
            success=False,
            error=(
                "fal-client not installed. "
                "Install with: pip install fal-client"
            ),
            prompt_used=prompt,
            quality=quality,
        )

    endpoint = _FAL_ENDPOINTS[quality]
    cost = _FAL_COST_PER_IMAGE[quality]

    def _progress(update):
        if hasattr(update, "logs"):
            for log in update.logs:
                print(f"    {log['message']}", file=sys.stderr)

    try:
        result = fal_client.subscribe(
            endpoint,
            arguments={
                "prompt": prompt,
                "image_size": {"width": 1024, "height": 768},
            },
            with_logs=True,
            on_queue_update=_progress,
        )
        image_url = result["images"][0]["url"]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(image_url, output_path)

        return RenderResult(
            success=True,
            image_path=output_path,
            image_url=image_url,
            prompt_used=prompt,
            estimated_cost=cost,
            quality=quality,
        )
    except Exception as e:
        return RenderResult(
            success=False, error=str(e),
            prompt_used=prompt, quality=quality,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _ensure_render_dir() -> Path:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    return RENDER_DIR


def _make_filename(room_type: str, style: str, suffix: str = ".png") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{room_type}_{style}_{ts}{suffix}"


def generate_image(
    prompt: str,
    quality: str = "free",
    output_path: str | None = None,
) -> RenderResult:
    """Generate an image using the specified quality tier.

    - "free": Pollinations.ai (no API key)
    - "fast": fal.ai Flux dev (requires FAL_KEY)
    - "high": fal.ai Flux Pro (requires FAL_KEY)
    """
    if output_path is None:
        _ensure_render_dir()
        output_path = str(RENDER_DIR / _make_filename("render", "image"))

    if quality == "free":
        return _generate_pollinations(prompt, output_path)

    # Paid tiers — check for API key
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key:
        return RenderResult(
            success=False,
            error=(
                "FAL_KEY environment variable not set. "
                "The free tier requires no key — use quality='free'. "
                "For fast/high quality, get your key at https://fal.ai/dashboard/keys"
            ),
            prompt_used=prompt,
            quality=quality,
        )

    return _generate_fal(prompt, quality, output_path)
