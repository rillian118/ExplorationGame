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

    lines = [f"|w{title}|n", description]

    if exits:
        lines.append(f"Exits: {', '.join(exits)}")
    else:
        lines.append("Exits: none")

    if blocked:
        lines.append("")
        lines.append("Obstructions:")
        lines.extend(blocked)

    return "\n".join(lines)


def format_surface_sample(sample: Dict[str, Any]) -> str:
    """Format raw environmental readings for debugging/admin preview."""
    if not sample:
        return "No surface sample available."

    return "\n".join(
        [
            f"Body: {sample.get('body_name', 'unknown')}",
            f"Coordinate: {sample.get('x')}, {sample.get('y')}",
            f"Terrain: {sample.get('terrain_label', 'unknown')}",
            f"Elevation: {sample.get('elevation_m', 'unknown')} m",
            f"Roughness: {sample.get('roughness', 'unknown')}",
            f"Gravity: {sample.get('gravity_g', 'unknown')}g",
            f"Temperature: {sample.get('temperature_k', 'unknown')} K",
            f"Radiation: {sample.get('radiation', 'unknown')}",
        ]
    )
