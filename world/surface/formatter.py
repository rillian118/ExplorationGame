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
    """
    Format a generated surface room view for display.
    """
    if not view:
        return "There is no generated surface data for this location."

    title = view.get("title", "Unsurveyed Surface")
    description = view.get("description", "The terrain here has not been described.")
    exits = view.get("exits", []) or []
    blocked = view.get("blocked_exits", {}) or {}
    landed_ship_names = view.get("landed_ship_names", []) or []

    lines: List[str] = [
        f"|w{title}|n",
        description,
    ]

    if landed_ship_names:
        lines.append("")
        for ship_name in landed_ship_names:
            lines.append(f"A ship, {ship_name}, rests nearby on its landing struts.")

    if exits:
        lines.append("")
        lines.append("Exits: " + ", ".join(exits))
    else:
        lines.append("")
        lines.append("Exits: none")

    if blocked:
        lines.append("")
        lines.append("Obstructions:")
        for direction, reason in blocked.items():
            lines.append(f"- {direction}: {reason}")

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


def _format_landed_ship_notices(view: Dict[str, Any]) -> List[str]:
    ship_names = view.get("landed_ship_names") or []
    lines: List[str] = []

    for name in ship_names:
        lines.append(f"A ship, {name}, rests nearby on its landing struts.")

    return lines