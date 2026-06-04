"""Text formatters for system and body displays."""
"""
Formatting helpers for player-facing stellar system output.

This module intentionally keeps presentation logic separate from command logic.
The storage layer keeps raw values such as AU and days; this layer decides how
those values should be displayed to players.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


AU_IN_KM = 149_597_870.7


def _get_body_name(body: Dict[str, Any]) -> str:
    return body.get("name") or body.get("id") or "Unnamed body"


def _get_body_kind(body: Dict[str, Any]) -> str:
    return body.get("kind") or "body"


def _get_body_classification(body: Dict[str, Any]) -> str:
    return body.get("classification") or "unclassified"


def format_period(days: Optional[float]) -> str:
    """
    Format an orbital period stored in days.

    Examples:
        27.0    -> 27.0 days
        410.0   -> 1.12 years
        4320.0  -> 11.83 years
    """
    if days is None:
        return "unknown period"

    try:
        days = float(days)
    except (TypeError, ValueError):
        return "unknown period"

    if days <= 0:
        return "stationary"

    if days < 365.25:
        return f"{days:.1f} days"

    years = days / 365.25
    return f"{years:.2f} years"


def format_orbital_distance(body: Dict[str, Any]) -> str:
    """
    Format orbital distance based on body type.

    Stars generally do not display an orbit.
    Planets and belts display AU.
    Moons display kilometers because their AU values are very small.
    """
    orbit = body.get("orbit") or {}
    axis_au = orbit.get("semi_major_axis_au")
    kind = _get_body_kind(body).lower()

    if axis_au is None:
        return "unknown orbit"

    try:
        axis_au = float(axis_au)
    except (TypeError, ValueError):
        return "unknown orbit"

    if kind == "star":
        return ""

    if kind == "moon":
        km = axis_au * AU_IN_KM
        if km >= 1_000_000:
            return f"{km / 1_000_000:.2f} million km"
        return f"{km:,.0f} km"

    if axis_au < 0.01:
        km = axis_au * AU_IN_KM
        return f"{km:,.0f} km"

    return f"{axis_au:.2f} AU"


def format_body_summary_line(body: Dict[str, Any], indent: int = 0) -> str:
    """
    Format a compact one-line body summary for system body lists.
    """
    prefix = " " * indent
    name = _get_body_name(body)
    kind = _get_body_kind(body)
    classification = _get_body_classification(body)

    if kind.lower() == "star":
        return f"{prefix}- {name} [{kind}; {classification}]"

    orbit = body.get("orbit") or {}
    distance = format_orbital_distance(body)
    period = format_period(orbit.get("orbital_period_days"))

    return (
        f"{prefix}- {name} [{kind}; {classification}] "
        f"orbit={distance}, period={period}"
    )


def format_system_list(systems: Iterable[Dict[str, Any]]) -> str:
    """
    Format the imported system list.
    """
    systems = list(systems)

    lines: List[str] = ["Imported Stellar Systems"]

    if not systems:
        lines.append("No stellar systems have been imported yet.")
        return "\n".join(lines)

    for system in systems:
        name = system.get("name", "Unnamed system")
        seed = system.get("seed", "unknown")
        bodies = system.get("bodies", [])
        lines.append(f"- {name} seed={seed} bodies={len(bodies)}")

    return "\n".join(lines)


def format_system_scan(system: Dict[str, Any]) -> str:
    """
    Format a short overview of a stellar system.
    """
    name = system.get("name", "Unnamed system")
    seed = system.get("seed", "unknown")
    bodies = system.get("bodies", [])
    primary_body_id = system.get("primary_body_id")

    primary = None
    for body in bodies:
        if body.get("id") == primary_body_id:
            primary = body
            break

    lines: List[str] = [
        name,
        f"Seed: {seed}",
        f"Known bodies: {len(bodies)}",
    ]

    if primary:
        primary_name = _get_body_name(primary)
        primary_class = _get_body_classification(primary)
        lines.append(f"Primary: {primary_name} ({primary_class})")
    else:
        lines.append("Primary: unknown")

    notes = system.get("generation_notes") or []
    if notes:
        lines.append("")
        lines.append("Generation notes:")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def _build_body_lookup(system: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {body.get("id"): body for body in system.get("bodies", []) if body.get("id")}


def _find_children(parent: Dict[str, Any], lookup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    child_ids = parent.get("children") or []
    return [lookup[child_id] for child_id in child_ids if child_id in lookup]


def format_system_bodies(system: Dict[str, Any]) -> str:
    """
    Format the known bodies in a system as a parent/child tree.
    """
    name = system.get("name", "Unnamed system")
    bodies = system.get("bodies", [])
    primary_body_id = system.get("primary_body_id")

    lookup = _build_body_lookup(system)
    primary = lookup.get(primary_body_id)

    lines: List[str] = [f"{name}: Known Orbital Bodies"]

    if not bodies:
        lines.append("No known bodies.")
        return "\n".join(lines)

    if not primary:
        for body in bodies:
            lines.append(format_body_summary_line(body))
        return "\n".join(lines)

    lines.append(format_body_summary_line(primary))

    primary_children = [
        body
        for body in bodies
        if (body.get("orbit") or {}).get("parent_id") == primary_body_id
    ]

    primary_children.sort(
        key=lambda body: (body.get("orbit") or {}).get("semi_major_axis_au") or 0
    )

    for body in primary_children:
        lines.append(format_body_summary_line(body, indent=2))

        for child in _find_children(body, lookup):
            lines.append(format_body_summary_line(child, indent=4))

    return "\n".join(lines)


def format_body_detail(body: Dict[str, Any]) -> str:
    """
    Format a detailed view for a single stellar body.
    """
    name = _get_body_name(body)
    kind = _get_body_kind(body)
    classification = _get_body_classification(body)
    summary = body.get("summary") or "No summary available."

    lines: List[str] = [
        name,
        f"Type: {kind}",
        f"Classification: {classification}",
        f"Summary: {summary}",
    ]

    orbit = body.get("orbit")
    if orbit and kind.lower() != "star":
        lines.append("")
        lines.append("Orbit:")
        lines.append(f"  Parent ID: {orbit.get('parent_id', 'unknown')}")
        lines.append(f"  Distance: {format_orbital_distance(body)}")
        lines.append(f"  Period: {format_period(orbit.get('orbital_period_days'))}")

        angle = orbit.get("angle_degrees")
        if angle is not None:
            lines.append(f"  Current angle: {float(angle):.1f} degrees")

    radius = body.get("radius_km")
    mass = body.get("mass_earth")
    temperature = body.get("temperature_k")
    survey_difficulty = body.get("survey_difficulty")

    lines.append("")
    lines.append("Physical readings:")

    if radius is not None:
        lines.append(f"  Radius: {float(radius):,.0f} km")
    if mass is not None:
        lines.append(f"  Mass: {float(mass):.3g} Earth masses")
    if temperature is not None:
        lines.append(f"  Temperature: {float(temperature):,.0f} K")
    if survey_difficulty is not None:
        lines.append(f"  Survey difficulty: {survey_difficulty}")

    return "\n".join(lines)