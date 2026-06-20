"""
Survey route/readout helpers.

This is intentionally a planning/readout tool, not movement automation. The
first pass samples a straight grid line between two surface coordinates and
summarizes what the caller already knows along that route.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from world.survey.map_styles import terrain_label_from_data
from world.survey.models import SurveyCoverage
from world.survey.services import actor_owner_key


MAX_ROUTE_POINTS = 250


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Best-effort integer conversion."""
    try:
        return int(value)
    except Exception:
        return default


def _coverage_queryset(owner_scope: str, owner_id: int):
    """Return coverage queryset for one owner."""
    return SurveyCoverage.objects.filter(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
    )


def _current_ship_body(caller: Any) -> tuple[str, str, str] | None:
    """Return current ship orbital body, if available."""
    try:
        from world.space.shipstate import get_current_ship_for_caller, read_ship_location

        ship = get_current_ship_for_caller(caller)
        if ship is None:
            return None

        state = read_ship_location(ship) or {}
        if state.get("mode") != "orbiting":
            return None

        system_name = state.get("system")
        body_id = state.get("body_id")
        body_name = state.get("body_name") or body_id

        if system_name and body_id:
            return str(system_name), str(body_id), str(body_name or body_id)
    except Exception:
        pass

    return None


def _surface_room_body(caller: Any) -> tuple[str, str, str, int | None, int | None] | None:
    """Return current generated surface body/coords, if available."""
    try:
        from world.surface.models import get_surface_address

        address = get_surface_address(caller.location) or {}
        system_name = address.get("system_name")
        body_id = address.get("body_id")
        body_name = address.get("body_name") or body_id
        x = _safe_int(address.get("x"))
        y = _safe_int(address.get("y"))

        if system_name and body_id:
            return str(system_name), str(body_id), str(body_name or body_id), x, y
    except Exception:
        pass

    return None


def _choose_body(caller: Any, owner_scope: str, owner_id: int, body_query: str = "") -> tuple[str, str, str] | None:
    """Choose a route body using explicit query, current context, or coverage."""
    qs = _coverage_queryset(owner_scope, owner_id)
    if not qs.exists():
        return None

    body_query = (body_query or "").strip().lower()
    if body_query:
        rows = list(qs.order_by("system_name", "body_id", "body_name"))
        for row in rows:
            labels = {
                str(row.body_id).lower(),
                str(row.body_name or "").lower(),
                f"{row.system_name}/{row.body_id}".lower(),
                f"{row.system_name}/{row.body_name or row.body_id}".lower(),
            }
            if body_query in labels or any(body_query in label for label in labels if label):
                return row.system_name, row.body_id, row.body_name or row.body_id

    ship_body = _current_ship_body(caller)
    if ship_body:
        system_name, body_id, body_name = ship_body
        if qs.filter(system_name=system_name, body_id=body_id).exists():
            return system_name, body_id, body_name

    surface_body = _surface_room_body(caller)
    if surface_body:
        system_name, body_id, body_name, _x, _y = surface_body
        if qs.filter(system_name=system_name, body_id=body_id).exists():
            return system_name, body_id, body_name

    counts = Counter()
    labels = {}
    for row in qs.iterator():
        key = (row.system_name, row.body_id)
        counts[key] += 1
        labels[key] = row.body_name or row.body_id

    if not counts:
        return None

    (system_name, body_id), _count = counts.most_common(1)[0]
    return system_name, body_id, labels.get((system_name, body_id), body_id)


def _line_points(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    """Return integer grid points on a Bresenham line."""
    x1 = int(x1)
    y1 = int(y1)
    x2 = int(x2)
    y2 = int(y2)
    points: list[tuple[int, int]] = []

    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x = x1
    y = y1

    while True:
        points.append((x, y))
        if x == x2 and y == y2:
            break

        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy

        if len(points) > MAX_ROUTE_POINTS:
            break

    return points


def _list_values(value: Any) -> list[str]:
    """Return normalized string values from scalar/list-like payload data."""
    if not value:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [
        str(item)
        for item in values
        if item is not None and item != "" and str(item).lower() != "none"
    ]


def _tile_terrain(row: SurveyCoverage | None) -> str:
    """Return route terrain label."""
    if row is None:
        return "unknown"
    return terrain_label_from_data(row.data or {}, fallback=row.scan_type or "known terrain")


def _float_or_none(value: Any) -> float | None:
    """Best-effort float conversion."""
    try:
        return float(value)
    except Exception:
        return None


def _format_count_summary(counter: Counter, *, limit: int = 6) -> list[str]:
    """Return formatted count lines."""
    return [f"  {label}: {count}" for label, count in counter.most_common(limit)]


def _format_coord_list(coords: list[tuple[int, int]], *, limit: int = 8) -> str:
    """Format a compact coordinate list."""
    shown = [f"{x},{y}" for x, y in coords[:limit]]
    if len(coords) > limit:
        shown.append(f"+{len(coords) - limit} more")
    return "; ".join(shown)


def _route_start_from_context(caller: Any, body: tuple[str, str, str], body_qs) -> tuple[int, int, str]:
    """Resolve start point for `survey route target <x> <y>`."""
    system_name, body_id, _body_name = body

    try:
        from world.survey.scanning import _resolve_orbital_scan_context, _resolve_scan_center

        context, error = _resolve_orbital_scan_context(caller)
        if not error and context and context["system_name"] == system_name and context["body_id"] == body_id:
            x, y, source, _notes = _resolve_scan_center(
                caller,
                context,
                target_x=None,
                target_y=None,
                target_source="",
            )
            return int(x), int(y), source
    except Exception:
        pass

    surface = _surface_room_body(caller)
    if surface:
        surface_system, surface_body, _name, x, y = surface
        if surface_system == system_name and surface_body == body_id and x is not None and y is not None:
            return int(x), int(y), "current surface position"

    latest = body_qs.order_by("-last_scanned_at", "-id").first()
    if latest is not None:
        return int(latest.x), int(latest.y), "latest surveyed tile"

    first = body_qs.order_by("x", "y").first()
    if first is not None:
        return int(first.x), int(first.y), "first surveyed tile"

    return 0, 0, "origin"


def _parse_route_args(caller: Any, args: str) -> tuple[dict[str, Any] | None, str]:
    """Parse route command args."""
    tokens = (args or "").split()
    if not tokens:
        return None, "Usage: survey route <x1> <y1> <x2> <y2> or survey route target <x> <y>"

    body_query = ""
    if tokens[0].lower() in {"target", "to"}:
        if len(tokens) < 3:
            return None, "Usage: survey route target <x> <y>"
        x2 = _safe_int(tokens[1])
        y2 = _safe_int(tokens[2])
        if x2 is None or y2 is None:
            return None, "Route target coordinates must be numbers."
        body_query = " ".join(tokens[3:]).strip()
        return {
            "mode": "target",
            "x2": x2,
            "y2": y2,
            "body_query": body_query,
        }, ""

    if len(tokens) < 4:
        return None, "Usage: survey route <x1> <y1> <x2> <y2>"

    x1 = _safe_int(tokens[0])
    y1 = _safe_int(tokens[1])
    x2 = _safe_int(tokens[2])
    y2 = _safe_int(tokens[3])
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return None, "Route coordinates must be numbers."

    body_query = " ".join(tokens[4:]).strip()
    return {
        "mode": "explicit",
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "body_query": body_query,
    }, ""


def render_survey_route(caller: Any, args: str = "") -> str:
    """Render a straight-line survey route readout."""
    parsed, error = _parse_route_args(caller, args)
    if error:
        return error

    owner_scope, owner_id = actor_owner_key(caller)
    body = _choose_body(caller, owner_scope, owner_id, body_query=parsed.get("body_query", ""))
    if body is None:
        return "No survey coverage recorded yet."

    system_name, body_id, body_name = body
    body_qs = _coverage_queryset(owner_scope, owner_id).filter(system_name=system_name, body_id=body_id)

    if parsed["mode"] == "target":
        x1, y1, start_source = _route_start_from_context(caller, body, body_qs)
        x2 = int(parsed["x2"])
        y2 = int(parsed["y2"])
    else:
        x1 = int(parsed["x1"])
        y1 = int(parsed["y1"])
        x2 = int(parsed["x2"])
        y2 = int(parsed["y2"])
        start_source = "explicit start"

    points = _line_points(x1, y1, x2, y2)
    truncated = len(points) > MAX_ROUTE_POINTS
    if truncated:
        points = points[:MAX_ROUTE_POINTS]

    route_keys = set(points)
    if not points:
        return "Survey route produced no points."

    x_values = [x for x, _y in points]
    y_values = [y for _x, y in points]
    rows = body_qs.filter(
        x__gte=min(x_values),
        x__lte=max(x_values),
        y__gte=min(y_values),
        y__lte=max(y_values),
    )
    rows_by_coord = {
        (int(row.x), int(row.y)): row
        for row in rows
        if (int(row.x), int(row.y)) in route_keys
    }

    known = []
    unknown = []
    terrain_counts = Counter()
    hazard_coords: list[tuple[int, int]] = []
    rough_coords: list[tuple[int, int]] = []
    low_elev: tuple[float, int, int] | None = None
    high_elev: tuple[float, int, int] | None = None
    resources = Counter()
    anomalies = Counter()
    low_res_coords: list[tuple[int, int]] = []

    for x, y in points:
        row = rows_by_coord.get((x, y))
        if row is None:
            unknown.append((x, y))
            continue

        known.append((x, y))
        data = row.data or {}
        terrain_counts[_tile_terrain(row)] += 1

        if data.get("hazard") or data.get("hazards"):
            hazard_coords.append((x, y))

        roughness_class = str(data.get("roughness_class") or "").lower()
        traversal = data.get("traversal") if isinstance(data.get("traversal"), dict) else {}
        if roughness_class in {"rough", "severe"} or traversal.get("rough_directions") or traversal.get("blocked_directions"):
            rough_coords.append((x, y))

        elevation = _float_or_none(data.get("elevation_m") if data.get("elevation_m") is not None else data.get("elevation"))
        if elevation is not None:
            if low_elev is None or elevation < low_elev[0]:
                low_elev = (elevation, x, y)
            if high_elev is None or elevation > high_elev[0]:
                high_elev = (elevation, x, y)

        for resource in _list_values(data.get("resource_signatures") or data.get("resources")):
            resources[resource] += 1

        for anomaly in _list_values(data.get("anomaly_signatures") or data.get("anomalies")):
            anomalies[anomaly] += 1

        if int(row.resolution or 0) < 2:
            low_res_coords.append((x, y))

    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx * dx + dy * dy)
    unknown_count = len(unknown)
    known_count = len(known)

    lines = [
        f"Survey Route: {system_name}/{body_name}",
        f"From {x1},{y1} to {x2},{y2}.",
        f"Start source: {start_source}.",
        f"Straight-line distance: {distance:.1f} tile units.",
        f"Sampled route: {len(points)} tile(s). Known: {known_count}. Unknown: {unknown_count}.",
    ]

    if truncated:
        lines.append(f"Route readout truncated at {MAX_ROUTE_POINTS} sampled tiles.")

    if terrain_counts:
        lines.append("")
        lines.append("Known terrain along route:")
        lines.extend(_format_count_summary(terrain_counts))

    if low_elev or high_elev:
        lines.append("")
        lines.append("Elevation along known route:")
        if high_elev:
            value, x, y = high_elev
            lines.append(f"  Highest: {value:.0f} m at {x},{y}")
        if low_elev:
            value, x, y = low_elev
            lines.append(f"  Lowest: {value:.0f} m at {x},{y}")

    lines.append("")
    if hazard_coords:
        lines.append(f"Hazard flags: {len(hazard_coords)} known tile(s): {_format_coord_list(hazard_coords)}")
    else:
        lines.append("Hazard flags: none in known route tiles.")

    if rough_coords:
        lines.append(f"Rough/blocked traversal indicators: {len(rough_coords)} tile(s): {_format_coord_list(rough_coords)}")

    if resources:
        lines.append("")
        lines.append("Resource signatures along route:")
        lines.extend(_format_count_summary(resources, limit=5))

    if anomalies:
        lines.append("")
        lines.append("Anomaly candidates along route:")
        lines.extend(_format_count_summary(anomalies, limit=5))

    if unknown:
        lines.append("")
        lines.append(f"Unknown gaps: {_format_coord_list(unknown)}")
        lines.append("Recommended follow-up: scan route gaps or use survey scan target <x> <y> on unknown clusters.")

    if low_res_coords:
        lines.append(f"Low-resolution known tiles: {len(low_res_coords)}. Consider resolution 2+ rescans before travel planning.")

    lines.append("")
    lines.append(f"Useful follow-up: survey map list center {x1} {y1}, survey detail {x2} {y2}")

    return "\n".join(lines)
