"""
Orbital survey scan mechanics.

v0.1 scope:
    - `survey scan` runs from the caller's current ship
    - current ship must be in orbit
    - caller must have crew+/owner/admin access to operate the ship
    - scan writes mutable SurveyCoverage rows for the caller
    - scan uses a deterministic 3x3 surface footprint

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
from world.survey.models import SCAN_TERRAIN
from world.survey.services import actor_owner_key, upsert_coverage_tile


DEFAULT_SCAN_RADIUS = 1
DEFAULT_SCAN_RESOLUTION = 1
DEFAULT_SCAN_QUALITY = 100


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

    This uses the existing surface generator when available and falls back to a
    minimal payload otherwise.
    """
    try:
        from world.surface.generator import compose_surface_room

        # compose_surface_room needs full system_data too, so this fallback is
        # intentionally handled by caller where system_data is available.
    except Exception:
        pass

    return {
        "x": int(x),
        "y": int(y),
    }


def _scan_tile_data(system_data: dict[str, Any], body: dict[str, Any], x: int, y: int) -> dict[str, Any]:
    """
    Build the stored data payload for a scanned tile.

    Prefer generated surface view data if available so the scan records terrain
    details that match the room generator.
    """
    try:
        from world.surface.generator import compose_surface_room

        view = compose_surface_room(system_data, body, int(x), int(y))
        if hasattr(view, "to_dict"):
            view = view.to_dict()

        if isinstance(view, Mapping):
            data = dict(view)
            # Keep the coverage row compact enough for frequent use.
            return {
                "terrain": data.get("terrain_name") or data.get("terrain") or data.get("name"),
                "elevation_m": data.get("elevation_m") or data.get("elevation"),
                "temperature_k": data.get("temperature_k") or data.get("temperature"),
                "radiation": data.get("radiation"),
                "summary": data.get("description") or data.get("summary"),
            }
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


def run_orbital_survey_scan(caller, *, radius: int = DEFAULT_SCAN_RADIUS) -> str:
    """
    Run an orbital terrain survey scan from caller's current ship.

    Returns a user-facing status message.
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
    points = _scan_points(center_x, center_y, int(radius))

    created_or_updated = 0
    for x, y in points:
        data = _scan_tile_data(system_data, body, int(x), int(y))
        data.update(
            {
                "scan_method": "orbital_ship_survey",
                "scan_center": {"x": center_x, "y": center_y},
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
            resolution=DEFAULT_SCAN_RESOLUTION,
            quality=DEFAULT_SCAN_QUALITY,
            source_ship_id=int(ship.id),
            data=data,
        )
        created_or_updated += 1

    return (
        f"{_ship_name(ship)} completes an orbital terrain survey of "
        f"{body_name} centered on ({center_x}, {center_y}). "
        f"{created_or_updated} tiles recorded."
    )
