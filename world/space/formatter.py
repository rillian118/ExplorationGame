"""Text formatters for system and body displays."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from collections.abc import Mapping

AU_IN_KM = 149_597_870.7


def _system_data(system_or_obj: Any) -> Dict[str, Any]:
    """
    Accept either raw system data, an Evennia _SaverDict, or a SpaceSystemObject.
    """
    if system_or_obj is None:
        return {}

    if isinstance(system_or_obj, Mapping):
        return dict(system_or_obj)

    try:
        data = system_or_obj.attributes.get("system_data")
        if isinstance(data, Mapping):
            return dict(data)
    except Exception:
        pass

    try:
        data = system_or_obj.db.system_data
        if isinstance(data, Mapping):
            return dict(data)
    except Exception:
        pass

    try:
        data = system_or_obj.system_data
        if isinstance(data, Mapping):
            return dict(data)
    except Exception:
        pass

    return {}


def _system_key(system_or_obj: Any) -> str:
    return getattr(system_or_obj, "key", "Unnamed system")


def _get_body_name(body: Dict[str, Any]) -> str:
    return body.get("name") or body.get("id") or "Unnamed body"


def _get_body_kind(body: Dict[str, Any]) -> str:
    return body.get("kind") or "body"


def _get_body_classification(body: Dict[str, Any]) -> str:
    return body.get("classification") or "unclassified"


def format_period(days: Optional[float]) -> str:
    """Format an orbital period stored in days."""
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

    Stars do not show an orbit. Moons show kilometers because their AU values
    are too small to display meaningfully as AU.
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
    """Format a compact one-line body summary for system body lists."""
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


def _children_by_parent(
    bodies: Iterable[Dict[str, Any]],
) -> Dict[Optional[str], List[Dict[str, Any]]]:
    grouped: Dict[Optional[str], List[Dict[str, Any]]] = {}

    for body in bodies:
        orbit = body.get("orbit") or {}
        parent_id = orbit.get("parent_id")
        grouped.setdefault(parent_id, []).append(body)

    return grouped


def format_system_list(system_objects: Iterable[Any]) -> str:
    """
    Format the imported system list.
    """
    rows = []

    for obj in system_objects:
        data = _system_data(obj)
        name = data.get("name") or getattr(obj, "key", "Unnamed system")
        seed = data.get("seed", "unknown")
        count = len(data.get("bodies", []) or [])
        rows.append((name, seed, count))

    if not rows:
        return "No generated systems have been imported yet."

    rows.sort(key=lambda row: str(row[0]).lower())

    lines = ["|wImported Stellar Systems|n"]
    for name, seed, count in rows:
        lines.append(f"- {name}    seed={seed}    bodies={count}")

    return "\n".join(lines)

def format_system_summary(system_data: Dict[str, Any]) -> str:
    """Format a short overview of a stellar system."""
    system_data = _system_data(system_data)

    name = system_data.get("name", "Unknown System")
    seed = system_data.get("seed", "unknown")
    bodies = list(system_data.get("bodies", []) or [])
    primary_id = system_data.get("primary_body_id")
    primary = next((body for body in bodies if body.get("id") == primary_id), None)

    lines = [
        f"|w{name}|n",
        f"Seed: {seed}",
        f"Known bodies: {len(bodies)}",
    ]

    if primary:
        lines.append(
            f"Primary: {_get_body_name(primary)} ({_get_body_classification(primary)})"
        )
    else:
        lines.append("Primary: unknown")

    notes = system_data.get("generation_notes") or []
    if notes:
        lines.append("")
        lines.append("Generation notes:")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def format_body_list(system_data: Dict[str, Any]) -> str:
    """Format the known bodies in a system as a parent/child tree."""
    system_data = _system_data(system_data)

    name = system_data.get("name", "Unknown System")
    bodies = list(system_data.get("bodies", []) or [])
    grouped = _children_by_parent(bodies)

    lines = [f"|w{name}: Known Orbital Bodies|n"]

    def emit(parent_id: Optional[str], depth: int = 0) -> None:
        children = grouped.get(parent_id, [])
        children.sort(
            key=lambda body: (
                (body.get("orbit") or {}).get("semi_major_axis_au") or 0.0,
                body.get("name", ""),
            )
        )

        for body in children:
            lines.append(format_body_summary_line(body, indent=2 * depth))
            emit(body.get("id"), depth + 1)

    emit(None)

    if len(lines) == 1:
        lines.append("No bodies recorded.")

    return "\n".join(lines)


def format_body_detail(system_data: Dict[str, Any], body: Dict[str, Any]) -> str:
    """
    Format a detailed view for a single stellar body.

    Signature matches the command code:
        format_body_detail(system_data, body)
    """
    system_data = _system_data(system_data)

    name = _get_body_name(body)
    kind = _get_body_kind(body)
    classification = _get_body_classification(body)
    summary = body.get("summary") or "No summary available."
    orbit = body.get("orbit") or {}
    tags = ", ".join(body.get("survey_tags") or []) or "none"

    lines: List[str] = [
        f"|w{name}|n",
        f"System: {system_data.get('name', 'Unknown System')}",
        f"ID: {body.get('id', 'unknown')}",
        f"Kind: {kind}",
        f"Classification: {classification}",
    ]

    if kind.lower() != "star":
        lines.extend(
            [
                f"Orbit radius: {format_orbital_distance(body)}",
                f"Orbital period: {format_period(orbit.get('orbital_period_days'))}",
                f"Current angle: {orbit.get('angle_degrees', '—')} degrees",
            ]
        )

    lines.extend(
        [
            f"Survey difficulty: {body.get('survey_difficulty', 1)}",
            f"Survey tags: {tags}",
        ]
    )

    radius = body.get("radius_km")
    mass = body.get("mass_earth")
    temperature = body.get("temperature_k")

    if radius is not None or mass is not None or temperature is not None:
        lines.append("")
        lines.append("Physical readings:")

        if radius is not None:
            lines.append(f"  Radius: {float(radius):,.0f} km")
        if mass is not None:
            lines.append(f"  Mass: {float(mass):.3g} Earth masses")
        if temperature is not None:
            lines.append(f"  Temperature: {float(temperature):,.0f} K")

    if summary:
        lines.extend(["", summary])

    return "\n".join(lines)
