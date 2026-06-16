"""
Shared terrain symbols and color styling for survey visuals.

The planet generator prototype uses richer ANSI palettes. Runtime survey
commands use Evennia color markup instead so the output works inside the MUD.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


TERRAIN_RE = re.compile(r"terrain here is\s+([^,.]+)", re.IGNORECASE)


@dataclass(frozen=True)
class TerrainStyle:
    keys: tuple[str, ...]
    symbol: str
    color: str
    bright_color: str
    label: str


TERRAIN_STYLES: tuple[TerrainStyle, ...] = (
    TerrainStyle(("lava", "molten", "magma", "flow"), "~", "|r", "|R", "lava or active flow"),
    TerrainStyle(("volcanic", "ash", "basalt"), "!", "|r", "|R", "volcanic terrain"),
    TerrainStyle(("deep liquid", "ocean", "sea", "water", "liquid"), "~", "|b", "|B", "liquid terrain"),
    TerrainStyle(("shallow liquid", "wetland", "marsh", "swamp"), ",", "|c", "|C", "shallow liquid"),
    TerrainStyle(("ice", "polar", "snow", "glacier", "frozen"), "*", "|C", "|W", "ice or polar terrain"),
    TerrainStyle(("mountain", "peak", "alpine"), "^", "|w", "|W", "mountains"),
    TerrainStyle(("highland", "upland", "ridge", "hill"), "#", "|y", "|Y", "highlands or uplands"),
    TerrainStyle(("crater", "impact"), "o", "|m", "|M", "crater terrain"),
    TerrainStyle(("basin", "depression"), "_", "|c", "|C", "basin terrain"),
    TerrainStyle(("desert", "dust", "sand", "dune", "arid"), ":", "|y", "|Y", "dust, sand, or desert"),
    TerrainStyle(("forest", "jungle", "vegetation", "flora"), "*", "|g", "|G", "vegetation"),
    TerrainStyle(("city", "settlement", "urban", "structure"), "#", "|w", "|W", "settlement or structure"),
    TerrainStyle(("plain", "plains", "open", "lowland", "flat"), ".", "|g", "|G", "open plains or lowlands"),
)


UNKNOWN_SYMBOL = "?"
CENTER_SYMBOL = "@"
HAZARD_SYMBOL = "!"


def colorize_symbol(symbol: str, color_code: str, *, color: bool = True) -> str:
    """Return an Evennia-colored symbol, or a plain symbol when color is off."""
    if not color:
        return symbol
    return f"{color_code}{symbol}|n"


def _value(data: dict[str, Any], *keys: str):
    """Return first non-empty value from data."""
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def _payload(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return a plain dict for mapping-like tile data."""
    if isinstance(data, Mapping):
        return dict(data)
    return {}


def parse_terrain_from_summary(summary: str) -> str | None:
    """Extract a compact terrain label from generated room prose."""
    if not summary:
        return None

    match = TERRAIN_RE.search(str(summary))
    if match:
        return match.group(1).strip().lower()

    return None


def terrain_label_from_data(data: dict[str, Any] | None, *, fallback: str = "unknown terrain") -> str:
    """Return a compact, normalized terrain label from stored survey data."""
    tile_data = _payload(data)
    terrain = _value(tile_data, "terrain", "terrain_name", "terrain_label", "name")

    if not terrain:
        terrain = parse_terrain_from_summary(str(_value(tile_data, "summary", "description", "desc") or ""))

    if not terrain:
        return fallback

    label = str(terrain).strip()
    if len(label) > 80:
        parsed = parse_terrain_from_summary(label)
        if parsed:
            return parsed
        label = label[:77].rstrip() + "..."

    return label.lower()


def has_hazard(data: dict[str, Any] | None) -> bool:
    """Return whether a tile payload carries explicit hazard data."""
    tile_data = _payload(data)
    if tile_data.get("hazard"):
        return True
    hazards = tile_data.get("hazards")
    return bool(hazards)


def terrain_style_for_label(label: str) -> TerrainStyle | None:
    """Return the first matching visual style for a terrain label."""
    normalized = str(label or "").lower()
    for style in TERRAIN_STYLES:
        if any(key in normalized for key in style.keys):
            return style
    return None


def tile_symbol(
    data: dict[str, Any] | None = None,
    *,
    terrain_label: str | None = None,
    color: bool = True,
    is_center: bool = False,
    is_unknown: bool = False,
    is_hazard: bool = False,
    is_new: bool = False,
) -> str:
    """Return a one-character terrain symbol with optional Evennia color."""
    if is_center:
        return colorize_symbol(CENTER_SYMBOL, "|W", color=color)

    if is_unknown:
        return colorize_symbol(UNKNOWN_SYMBOL, "|x", color=color)

    if is_hazard or has_hazard(data):
        return colorize_symbol(HAZARD_SYMBOL, "|R", color=color)

    label = terrain_label or terrain_label_from_data(data, fallback="known terrain")
    style = terrain_style_for_label(label)
    if style is None:
        return colorize_symbol(".", "|w", color=color)

    color_code = style.bright_color if is_new else style.color
    return colorize_symbol(style.symbol, color_code, color=color)


def render_visual_legend(*, color: bool = True, include_scan_changes: bool = False) -> str:
    """Render the compact terrain legend used by survey visual maps."""
    entries = [
        (CENTER_SYMBOL, "|W", "scan center"),
        (UNKNOWN_SYMBOL, "|x", "unknown"),
        (".", "|g", "plains/open"),
        (":", "|y", "dust/desert"),
        ("#", "|y", "uplands/highlands"),
        ("^", "|w", "mountains"),
        ("o", "|m", "craters"),
        ("_", "|c", "basins"),
        ("~", "|b", "liquid/flow"),
        ("*", "|C", "ice/polar"),
        (HAZARD_SYMBOL, "|R", "hazard"),
    ]

    parts = [f"{colorize_symbol(symbol, code, color=color)}={label}" for symbol, code, label in entries]
    lines = ["Legend: " + ", ".join(parts)]
    if include_scan_changes:
        lines.append("Bright terrain symbols mark newly mapped tiles; normal symbols mark updated or known tiles.")
    return "\n".join(lines)
