"""Formatting helpers for generated planetary surface rooms."""

from __future__ import annotations

from typing import Any, Dict, List


_ORDER = [
    "north",
    "northeast",
    "east",
    "southeast",
    "south",
    "southwest",
    "west",
    "northwest",
]

_ABBREVIATIONS = {
    "north": "n",
    "northeast": "ne",
    "east": "e",
    "southeast": "se",
    "south": "s",
    "southwest": "sw",
    "west": "w",
    "northwest": "nw",
}


def _direction_label(direction: str) -> str:
    return direction.capitalize()


def _exit_label(direction: str) -> str:
    return _ABBREVIATIONS.get(direction, direction)


def format_surface_view(view: Dict[str, Any]) -> str:
    """Format a stored/generated surface view for display."""
    if not view:
        return "No surface data is available for this location."

    sample = view.get("sample", {}) or {}
    directions = view.get("directions", {}) or {}
    title = view.get("title") or sample.get("terrain_label") or "Generated Surface"
    description = view.get("description") or "No surface description is available."
    landed_ship_names = view.get("landed_ship_names", []) or []

    exits: List[str] = []
    blocked: List[str] = []

    for direction in _ORDER:
        profile = directions.get(direction) or {}

        if profile.get("allowed"):
            exits.append(_exit_label(direction))
        else:
            reason = profile.get("blocked_reason")
            if reason:
                blocked.append(f"- {_direction_label(direction)}: {reason}")

    lines = [
        f"|w{title}|n",
        description,
    ]

    """if landed_ship_names:
        lines.append("")
        for ship_name in landed_ship_names:
            lines.append(f"A ship, {ship_name}, rests nearby on its landing struts.")"""

    overlay_descriptions = view.get("surface_overlay_descriptions") or []
    for desc in overlay_descriptions:
        lines.append("")
        lines.append(str(desc))

    if exits:
        lines.append("")
        lines.append(f"Exits: {', '.join(exits)}")
    else:
        lines.append("")
        lines.append("Exits: none")

    if blocked:
        lines.append("")
        lines.append("Obstructions:")
        lines.extend(blocked)

    return "\n".join(lines)


def _format_landed_ship_notices(view: Dict[str, Any]) -> List[str]:
    ship_names = view.get("landed_ship_names") or []
    lines: List[str] = []

    for name in ship_names:
        lines.append(f"A ship, {name}, rests nearby on its landing struts.")

    return lines