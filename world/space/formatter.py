"""Text formatters for system and body displays."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _fmt_au(value: Any) -> str:
    try:
        return f"{float(value):.2f} AU"
    except (TypeError, ValueError):
        return "—"


def _fmt_period(value: Any) -> str:
    try:
        days = float(value)
    except (TypeError, ValueError):
        return "—"
    if days >= 730:
        return f"{days / 365.25:.1f} years"
    return f"{days:.1f} days"


def _children_by_parent(bodies: Iterable[Dict[str, Any]]) -> Dict[Optional[str], List[Dict[str, Any]]]:
    grouped: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for body in bodies:
        orbit = body.get("orbit") or {}
        parent_id = orbit.get("parent_id")
        grouped.setdefault(parent_id, []).append(body)
    return grouped


def format_system_summary(system_data: Dict[str, Any]) -> str:
    name = system_data.get("name", "Unknown System")
    seed = system_data.get("seed", "unknown")
    bodies = list(system_data.get("bodies", []) or [])
    primary_id = system_data.get("primary_body_id")
    primary = next((body for body in bodies if body.get("id") == primary_id), None)

    lines = [f"|w{name}|n", f"Seed: {seed}", f"Known bodies: {len(bodies)}"]
    if primary:
        lines.append(
            f"Primary: {primary.get('name', 'Unknown')} ({primary.get('classification', primary.get('kind', 'unknown'))})"
        )
    return "\n".join(lines)


def format_body_list(system_data: Dict[str, Any]) -> str:
    name = system_data.get("name", "Unknown System")
    bodies = list(system_data.get("bodies", []) or [])
    grouped = _children_by_parent(bodies)

    lines = [f"|w{name}: Known Orbital Bodies|n"]

    def emit(parent_id: Optional[str], depth: int = 0) -> None:
        children = grouped.get(parent_id, [])
        children.sort(key=lambda b: ((b.get("orbit") or {}).get("semi_major_axis_au") or 0.0, b.get("name", "")))
        for body in children:
            orbit = body.get("orbit") or {}
            indent = "  " * depth
            kind = body.get("kind", "body")
            classification = body.get("classification", "unknown")
            distance = _fmt_au(orbit.get("semi_major_axis_au"))
            period = _fmt_period(orbit.get("orbital_period_days"))
            lines.append(f"{indent}- {body.get('name', 'Unknown')} [{kind}; {classification}] orbit={distance}, period={period}")
            emit(body.get("id"), depth + 1)

    emit(None)
    if len(lines) == 1:
        lines.append("No bodies recorded.")
    return "\n".join(lines)


def format_body_detail(system_data: Dict[str, Any], body: Dict[str, Any]) -> str:
    orbit = body.get("orbit") or {}
    tags = ", ".join(body.get("survey_tags") or []) or "none"
    lines = [
        f"|w{body.get('name', 'Unknown Body')}|n",
        f"System: {system_data.get('name', 'Unknown System')}",
        f"ID: {body.get('id', 'unknown')}",
        f"Kind: {body.get('kind', 'unknown')}",
        f"Classification: {body.get('classification', 'unknown')}",
        f"Orbit radius: {_fmt_au(orbit.get('semi_major_axis_au'))}",
        f"Orbital period: {_fmt_period(orbit.get('orbital_period_days'))}",
        f"Current angle: {orbit.get('angle_degrees', '—')} degrees",
        f"Survey difficulty: {body.get('survey_difficulty', 1)}",
        f"Survey tags: {tags}",
    ]
    summary = body.get("summary")
    if summary:
        lines.extend(["", summary])
    return "\n".join(lines)


def format_system_list(system_objects: Iterable[Any]) -> str:
    rows = []
    for obj in system_objects:
        data = obj.db.system_data or {}
        rows.append((data.get("name", obj.key), data.get("seed", "unknown"), len(data.get("bodies", []) or [])))

    if not rows:
        return "No generated systems have been imported yet."

    rows.sort(key=lambda row: str(row[0]).lower())
    lines = ["|wImported Stellar Systems|n"]
    for name, seed, count in rows:
        lines.append(f"- {name}    seed={seed}    bodies={count}")
    return "\n".join(lines)
