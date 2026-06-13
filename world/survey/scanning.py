"""
Orbital survey scan mechanics.

v0.1 scope:
    - `survey scan` runs from the caller's current ship
    - current ship must be in orbit
    - caller must have crew+/owner/admin access to operate the ship
    - scan writes mutable SurveyCoverage rows for the caller
    - scan uses a deterministic, capped square surface footprint
    - scan returns a semantic report suitable for screen-reader users

This deliberately does not create SurveyDataset records directly. Datasets are
still exported/snapshotted with `survey export <name>`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from world.space.models import find_body, find_system_object, read_system_data
from world.space.ship_access import ACTION_OPERATE, require_ship_access
from world.space.shipstate import get_current_ship_for_caller, read_ship_location
from world.survey.models import SCAN_TERRAIN, SurveyCoverage
from world.survey.scan_reports import compact_tile_data, render_orbital_scan_report
from world.survey.services import actor_owner_key, upsert_coverage_tile


DEFAULT_SCAN_RADIUS = 1
DEFAULT_SCAN_RESOLUTION = 1
DEFAULT_SCAN_QUALITY = 100
MAX_SCAN_RADIUS = 3
MAX_SCAN_RESOLUTION = 3


def _as_dict(value: Any) -> dict[str, Any]:
    """Return value as plain dict if mapping-like, else empty dict."""
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ship_name(ship: Any) -> str:
    """Best-effort ship display name."""
    try:
        name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")
    except Exception:
        name = getattr(ship, "key", "Unknown ship")

    return str(name).replace("Ship: ", "", 1)


def _stable_int(*parts: Any) -> int:
    """Return a deterministic positive int from arbitrary parts."""
    payload = "::".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _body_grid_size(body: dict[str, Any]) -> tuple[int, int]:
    """
    Return approximate surface grid size.

    Current surface generation is tolerant of arbitrary integer coords, but
    using a bounded footprint gives us cleaner future compatibility. If no
    explicit dimensions exist, use the existing prototype's rough 1000x1000
    Earth-size design assumption.
    """
    for key_x, key_y in (
        ("surface_width", "surface_height"),
        ("map_width", "map_height"),
        ("grid_width", "grid_height"),
    ):
        try:
            width = int(body.get(key_x))
            height = int(body.get(key_y))
            if width > 0 and height > 0:
                return width, height
        except Exception:
            pass

    return 1000, 1000


def _scan_center_from_state(system_name: str, body_id: str, state: dict[str, Any], body: dict[str, Any]) -> tuple[int, int]:
    """
    Pick a deterministic scan center for an orbiting ship.

    Priority:
        1. last_surface_coordinates, if the ship just took off from a known tile
        2. state["coordinates"], if it already contains x/y
        3. stable pseudo-random coordinate from system/body/ship context
    """
    last_surface = _as_dict(state.get("last_surface_coordinates"))
    if last_surface.get("x") is not None and last_surface.get("y") is not None:
        return int(last_surface["x"]), int(last_surface["y"])

    coords = _as_dict(state.get("coordinates"))
    if coords.get("x") is not None and coords.get("y") is not None:
        return int(coords["x"]), int(coords["y"])

    width, height = _body_grid_size(body)
    seed_value = _stable_int(system_name, body_id, state.get("source_ship_id"), state.get("body_name"))
    return seed_value % width, (seed_value // width) % height


def _surface_tile_payload(body: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    """
    Return lightweight deterministic tile payload for survey coverage.
    """
    return {
        "x": int(x),
        "y": int(y),
    }


def _scan_tile_data(system_data: dict[str, Any], body: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    """
    Build the stored data payload for a scanned tile.

    Prefer generated surface view data if available so the scan records terrain
    details that match the room generator. Normalize prose-only generator output
    into compact fields for map and scan-report use.
    """
    try:
        from world.surface.generator import compose_surface_room

        view = compose_surface_room(system_data, body, int(x), int(y))
        if hasattr(view, "to_dict"):
            view = view.to_dict()

        if isinstance(view, Mapping):
            generated = dict(view)
            raw = {
                "terrain": (
                    generated.get("terrain_name")
                    or generated.get("terrain")
                    or generated.get("terrain_label")
                    or generated.get("name")
                ),
                "elevation_m": generated.get("elevation_m") or generated.get("elevation"),
                "temperature_k": generated.get("temperature_k") or generated.get("temperature"),
                "radiation": generated.get("radiation"),
                "gravity": generated.get("gravity"),
                "summary": generated.get("description") or generated.get("summary") or generated.get("desc"),
            }
            return compact_tile_data(raw)
    except Exception:
        pass

    return _surface_tile_payload(body, x, y)


def _scan_points(center_x: int, center_y: int, radius: int) -> list[tuple[int, int]]:
    """Return square scan footprint around center."""
    points = []
    for y in range(center_y - radius, center_y + radius + 1):
        for x in range(center_x - radius, center_x + radius + 1):
            points.append((x, y))
    return points


def _clamp_int(value: int, *, minimum: int, maximum: int) -> int:
    """Clamp an integer to a supported range."""
    return max(int(minimum), min(int(maximum), int(value)))


def parse_scan_options(args: str) -> tuple[dict[str, int], str]:
    """
    Parse player-facing survey scan options.

    Supported:
        survey scan
        survey scan radius 2
        survey scan resolution 2
        survey scan radius 2 resolution 2

    Values are capped here as a prototype stand-in for future sensor equipment,
    crew skill, power allocation, and environmental constraints.
    """
    tokens = (args or "").split()
    options = {
        "radius": DEFAULT_SCAN_RADIUS,
        "resolution": DEFAULT_SCAN_RESOLUTION,
    }

    i = 0
    while i < len(tokens):
        token = tokens[i].lower()

        if token in {"radius", "range"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan radius <0-3>"
            try:
                radius = int(tokens[i + 1])
            except ValueError:
                return options, "Scan radius must be a number."

            if radius < 0:
                return options, "Scan radius cannot be negative."

            options["radius"] = _clamp_int(radius, minimum=0, maximum=MAX_SCAN_RADIUS)
            i += 2
            continue

        if token in {"resolution", "res"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan resolution <1-3>"
            try:
                resolution = int(tokens[i + 1])
            except ValueError:
                return options, "Scan resolution must be a number."

            if resolution < 1:
                return options, "Scan resolution must be at least 1."

            options["resolution"] = _clamp_int(resolution, minimum=1, maximum=MAX_SCAN_RESOLUTION)
            i += 2
            continue

        return (
            options,
            "Usage: survey scan [radius <0-3>] [resolution <1-3>]",
        )

    return options, ""


def _coverage_exists(owner_scope: str, owner_id: int, system_name: str, body_id: str, x: int, y: int, scan_type: str) -> bool:
    """Return whether a matching coverage row already exists."""
    return SurveyCoverage.objects.filter(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
        system_name=str(system_name),
        body_id=str(body_id),
        x=int(x),
        y=int(y),
        scan_type=str(scan_type),
    ).exists()


def run_orbital_survey_scan(
    caller,
    *,
    radius: int = DEFAULT_SCAN_RADIUS,
    resolution: int = DEFAULT_SCAN_RESOLUTION,
) -> str:
    """
    Run an orbital terrain survey scan from caller's current ship.

    Returns a user-facing semantic scan report.
    """
    ship = get_current_ship_for_caller(caller)
    if ship is None:
        return "No current ship selected. Use 'ship board <ship>' first."

    allowed, error = require_ship_access(caller, ship, ACTION_OPERATE)
    if not allowed:
        return error

    state = read_ship_location(ship) or {}
    if state.get("mode") != "orbiting":
        return "Survey scan requires the ship to be in orbit around a survey target."

    system_name = state.get("system")
    body_id = state.get("body_id")
    body_name = state.get("body_name") or body_id

    if not system_name or not body_id:
        return "The current ship is orbiting, but its survey target is incomplete."

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        return f"No imported system named '{system_name}' was found."

    system_data = read_system_data(system_obj)
    if not system_data:
        return f"System '{system_name}' has no stored system data."

    body = find_body(system_data, str(body_id))
    if body is None:
        return f"No body id '{body_id}' was found in {system_name}."

    owner_scope, owner_id = actor_owner_key(caller)
    center_x, center_y = _scan_center_from_state(str(system_name), str(body_id), state, body)
    radius = _clamp_int(int(radius), minimum=0, maximum=MAX_SCAN_RADIUS)
    resolution = _clamp_int(int(resolution), minimum=1, maximum=MAX_SCAN_RESOLUTION)
    points = _scan_points(center_x, center_y, radius)

    records: list[dict[str, Any]] = []
    created_count = 0
    updated_count = 0

    for x, y in points:
        existed = _coverage_exists(
            owner_scope,
            owner_id,
            str(system_name),
            str(body_id),
            int(x),
            int(y),
            SCAN_TERRAIN,
        )

        data = _scan_tile_data(system_data, body, int(x), int(y))
        data.update(
            {
                "scan_method": "orbital_ship_survey",
                "scan_center": {"x": center_x, "y": center_y},
                "scan_radius": radius,
                "scan_resolution": resolution,
                "source_ship_name": _ship_name(ship),
            }
        )

        upsert_coverage_tile(
            owner_scope=owner_scope,
            owner_id=owner_id,
            system_name=str(system_name),
            body_id=str(body_id),
            body_name=str(body_name or ""),
            x=int(x),
            y=int(y),
            scan_type=SCAN_TERRAIN,
            resolution=resolution,
            quality=DEFAULT_SCAN_QUALITY,
            source_ship_id=int(ship.id),
            data=data,
        )

        if existed:
            updated_count += 1
        else:
            created_count += 1

        records.append(
            {
                "x": int(x),
                "y": int(y),
                "data": data,
                "resolution": resolution,
                "quality": DEFAULT_SCAN_QUALITY,
                "existed": existed,
            }
        )

    return render_orbital_scan_report(
        ship_name=_ship_name(ship),
        body_name=str(body_name or body_id),
        center_x=center_x,
        center_y=center_y,
        radius=int(radius),
        records=records,
        created_count=created_count,
        updated_count=updated_count,
    )
