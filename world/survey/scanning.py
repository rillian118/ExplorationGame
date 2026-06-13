"""
Orbital survey scan mechanics.

v0.1 scope:
    - `survey scan` runs from the caller's current ship
    - current ship must be in orbit
    - caller must have crew+/owner/admin access to operate the ship
    - scan writes mutable SurveyCoverage rows for the caller
    - default scan uses a deterministic, capped square surface footprint
    - band scan advances a resumable horizontal orbital pass one step at a time
    - scan returns a semantic report suitable for screen-reader users

This deliberately does not create SurveyDataset records directly. Datasets are
still exported/snapshotted with `survey export <name>`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from world.space.models import find_body, find_system_object, read_system_data
from world.space.ship_capabilities import (
    CAP_SENSOR_QUALITY,
    CAP_SURVEY_MAX_RADIUS,
    CAP_SURVEY_MAX_RESOLUTION,
    read_ship_capabilities,
)
from world.space.ship_access import ACTION_OPERATE, require_ship_access
from world.space.shipstate import get_current_ship_for_caller, read_ship_location
from world.survey.models import SCAN_TERRAIN, SurveyCoverage
from world.survey.scan_reports import compact_tile_data, render_orbital_scan_report
from world.survey.services import actor_owner_key, upsert_coverage_tile


DEFAULT_SCAN_RADIUS = 1
DEFAULT_SCAN_RESOLUTION = 1
DEFAULT_SCAN_QUALITY = 100
SURVEY_BAND_OPERATION_ATTR = "survey_band_operation"


SCAN_USAGE = (
    "Usage: survey scan [radius <number>] [resolution <number>] or "
    "survey scan band [start, next, status, or clear] [y <number>] "
    "[radius <number>] [resolution <number>]"
)


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


def parse_scan_options(args: str) -> tuple[dict[str, Any], str]:
    """
    Parse player-facing survey scan options.

    Supported:
        survey scan
        survey scan radius 2
        survey scan resolution 2
        survey scan radius 2 resolution 2
        survey scan band
        survey scan band start y 25 radius 1 resolution 2
        survey scan band next
        survey scan band status
        survey scan band clear

    Values are capped later by the current ship's survey capabilities.
    """
    tokens = (args or "").split()
    options = {
        "mode": "footprint",
        "radius": DEFAULT_SCAN_RADIUS,
        "resolution": DEFAULT_SCAN_RESOLUTION,
        "band_action": "next",
        "band_y": None,
    }

    i = 0
    if tokens and tokens[0].lower() in {"band", "bands"}:
        options["mode"] = "band"
        i = 1

        if i < len(tokens) and tokens[i].lower() in {"start", "next", "status", "clear"}:
            options["band_action"] = tokens[i].lower()
            i += 1

    while i < len(tokens):
        token = tokens[i].lower()

        if options["mode"] == "band" and token in {"y", "row", "latitude", "lat"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan band y <number>"
            try:
                options["band_y"] = int(tokens[i + 1])
            except ValueError:
                return options, "Band y coordinate must be a number."
            i += 2
            continue

        if options["mode"] == "band" and options["band_y"] is None:
            try:
                options["band_y"] = int(tokens[i])
                i += 1
                continue
            except ValueError:
                pass

        if token in {"radius", "range"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan radius <number>"
            try:
                radius = int(tokens[i + 1])
            except ValueError:
                return options, "Scan radius must be a number."

            if radius < 0:
                return options, "Scan radius cannot be negative."

            options["radius"] = radius
            i += 2
            continue

        if token in {"resolution", "res"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan resolution <number>"
            try:
                resolution = int(tokens[i + 1])
            except ValueError:
                return options, "Scan resolution must be a number."

            if resolution < 1:
                return options, "Scan resolution must be at least 1."

            options["resolution"] = resolution
            i += 2
            continue

        return options, SCAN_USAGE

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


def _resolve_orbital_scan_context(caller) -> tuple[dict[str, Any] | None, str]:
    """Resolve current ship/orbit/body context for an orbital survey."""
    ship = get_current_ship_for_caller(caller)
    if ship is None:
        return None, "No current ship selected. Use 'ship board <ship>' first."

    allowed, error = require_ship_access(caller, ship, ACTION_OPERATE)
    if not allowed:
        return None, error

    state = read_ship_location(ship) or {}
    if state.get("mode") != "orbiting":
        return None, "Survey scan requires the ship to be in orbit around a survey target."

    system_name = state.get("system")
    body_id = state.get("body_id")
    body_name = state.get("body_name") or body_id

    if not system_name or not body_id:
        return None, "The current ship is orbiting, but its survey target is incomplete."

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        return None, f"No imported system named '{system_name}' was found."

    system_data = read_system_data(system_obj)
    if not system_data:
        return None, f"System '{system_name}' has no stored system data."

    body = find_body(system_data, str(body_id))
    if body is None:
        return None, f"No body id '{body_id}' was found in {system_name}."

    owner_scope, owner_id = actor_owner_key(caller)
    center_x, center_y = _scan_center_from_state(str(system_name), str(body_id), state, body)
    body_width, body_height = _body_grid_size(body)

    return {
        "ship": ship,
        "state": state,
        "system_name": str(system_name),
        "body_id": str(body_id),
        "body_name": str(body_name or body_id),
        "system_data": system_data,
        "body": body,
        "owner_scope": owner_scope,
        "owner_id": owner_id,
        "center_x": int(center_x),
        "center_y": int(center_y),
        "body_width": int(body_width),
        "body_height": int(body_height),
    }, ""


def _ship_scan_limits(ship: Any, radius: int, resolution: int) -> tuple[int, int, int, int, int, list[str]]:
    """Apply ship capability caps to requested radius/resolution."""
    capabilities = read_ship_capabilities(ship)
    max_radius = int(capabilities.get(CAP_SURVEY_MAX_RADIUS, DEFAULT_SCAN_RADIUS))
    max_resolution = int(capabilities.get(CAP_SURVEY_MAX_RESOLUTION, DEFAULT_SCAN_RESOLUTION))
    sensor_quality = int(capabilities.get(CAP_SENSOR_QUALITY, DEFAULT_SCAN_QUALITY))

    requested_radius = int(radius)
    requested_resolution = int(resolution)
    capped_radius = _clamp_int(requested_radius, minimum=0, maximum=max_radius)
    capped_resolution = _clamp_int(requested_resolution, minimum=1, maximum=max_resolution)

    limit_notes = []
    if capped_radius != requested_radius:
        limit_notes.append(f"radius {requested_radius} capped to {capped_radius} by ship capability")
    if capped_resolution != requested_resolution:
        limit_notes.append(f"resolution {requested_resolution} capped to {capped_resolution} by ship capability")

    return capped_radius, capped_resolution, sensor_quality, max_radius, max_resolution, limit_notes


def _write_scan_records(
    context: dict[str, Any],
    points: list[tuple[int, int]],
    *,
    center_x: int,
    center_y: int,
    resolution: int,
    quality: int,
    metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, int]:
    """Write survey coverage rows for scan points and return report records."""
    records: list[dict[str, Any]] = []
    created_count = 0
    updated_count = 0

    owner_scope = context["owner_scope"]
    owner_id = context["owner_id"]
    system_name = context["system_name"]
    body_id = context["body_id"]
    body_name = context["body_name"]
    system_data = context["system_data"]
    body = context["body"]
    ship = context["ship"]

    for x, y in points:
        existed = _coverage_exists(
            owner_scope,
            owner_id,
            system_name,
            body_id,
            int(x),
            int(y),
            SCAN_TERRAIN,
        )

        data = _scan_tile_data(system_data, body, int(x), int(y))
        data.update(
            {
                "scan_center": {"x": center_x, "y": center_y},
                "scan_resolution": resolution,
                "sensor_quality": quality,
                "source_ship_name": _ship_name(ship),
            }
        )
        data.update(metadata)

        upsert_coverage_tile(
            owner_scope=owner_scope,
            owner_id=owner_id,
            system_name=system_name,
            body_id=body_id,
            body_name=body_name,
            x=int(x),
            y=int(y),
            scan_type=SCAN_TERRAIN,
            resolution=resolution,
            quality=quality,
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
                "quality": quality,
                "existed": existed,
            }
        )

    return records, created_count, updated_count


def _bounded_scan_points(center_x: int, center_y: int, radius: int, width: int, height: int) -> list[tuple[int, int]]:
    """Return footprint points clipped to body grid bounds."""
    points = []
    seen = set()
    for x, y in _scan_points(center_x, center_y, radius):
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        key = (int(x), int(y))
        if key in seen:
            continue
        seen.add(key)
        points.append(key)
    return points


def _read_band_operation(caller: Any) -> dict[str, Any]:
    """Read caller's active resumable band survey operation."""
    try:
        raw = caller.attributes.get(SURVEY_BAND_OPERATION_ATTR)
    except Exception:
        raw = None

    return dict(raw) if isinstance(raw, Mapping) else {}


def _write_band_operation(caller: Any, operation: dict[str, Any]) -> None:
    """Persist caller's active band survey operation."""
    caller.attributes.add(SURVEY_BAND_OPERATION_ATTR, dict(operation))


def _clear_band_operation(caller: Any) -> None:
    """Clear caller's active band survey operation."""
    try:
        caller.attributes.remove(SURVEY_BAND_OPERATION_ATTR)
    except Exception:
        pass


def _format_band_operation(operation: dict[str, Any]) -> str:
    """Render compact band operation status."""
    if not operation:
        return "No active orbital band survey operation."

    next_x = int(operation.get("next_x", 0))
    x_max = int(operation.get("x_max", 0))
    complete = next_x > x_max
    status = "complete" if complete else "in progress"

    lines = [
        "Orbital band survey operation",
        f"  Status: {status}",
        f"  Body: {operation.get('system_name')}/{operation.get('body_name') or operation.get('body_id')}",
        f"  Band y: {operation.get('band_y')}",
        f"  Radius per step: {operation.get('radius')}",
        f"  Resolution: {operation.get('resolution')}",
        f"  Next center x: {next_x if not complete else 'none'}",
        f"  Final x: {x_max}",
    ]
    return "\n".join(lines)


def run_orbital_survey_scan(
    caller,
    *,
    radius: int = DEFAULT_SCAN_RADIUS,
    resolution: int = DEFAULT_SCAN_RESOLUTION,
    mode: str = "footprint",
    band_action: str = "next",
    band_y: int | None = None,
) -> str:
    """
    Run an orbital terrain survey scan from caller's current ship.

    Returns a user-facing semantic scan report.
    """
    if mode == "band":
        return run_orbital_band_survey_step(
            caller,
            action=band_action,
            band_y=band_y,
            radius=radius,
            resolution=resolution,
        )

    context, error = _resolve_orbital_scan_context(caller)
    if error:
        return error

    ship = context["ship"]
    center_x = context["center_x"]
    center_y = context["center_y"]
    radius, resolution, sensor_quality, max_radius, max_resolution, limit_notes = _ship_scan_limits(
        ship,
        int(radius),
        int(resolution),
    )
    points = _scan_points(center_x, center_y, radius)

    records, created_count, updated_count = _write_scan_records(
        context,
        points,
        center_x=center_x,
        center_y=center_y,
        resolution=resolution,
        quality=sensor_quality,
        metadata={
            "scan_method": "orbital_ship_survey",
            "scan_radius": radius,
            "ship_survey_max_radius": max_radius,
            "ship_survey_max_resolution": max_resolution,
        },
    )

    return render_orbital_scan_report(
        ship_name=_ship_name(ship),
        body_name=context["body_name"],
        center_x=center_x,
        center_y=center_y,
        radius=int(radius),
        records=records,
        created_count=created_count,
        updated_count=updated_count,
        limit_notes=limit_notes,
    )


def run_orbital_band_survey_step(
    caller,
    *,
    action: str = "next",
    band_y: int | None = None,
    radius: int = DEFAULT_SCAN_RADIUS,
    resolution: int = DEFAULT_SCAN_RESOLUTION,
) -> str:
    """
    Run or manage one resumable orbital horizontal-band survey step.

    Each step writes normal SurveyCoverage rows before advancing the stored
    operation cursor. This makes the operation interruptible: completed steps
    remain useful even if the player stops, disconnects, or changes activity.
    """
    action = (action or "next").lower()

    if action == "clear":
        _clear_band_operation(caller)
        return "Cleared active orbital band survey operation."

    if action == "status":
        return _format_band_operation(_read_band_operation(caller))

    context, error = _resolve_orbital_scan_context(caller)
    if error:
        return error

    ship = context["ship"]
    body_width = max(1, int(context["body_width"]))
    body_height = max(1, int(context["body_height"]))

    operation = _read_band_operation(caller)
    must_start = action == "start" or not operation

    if not must_start:
        if (
            operation.get("system_name") != context["system_name"]
            or operation.get("body_id") != context["body_id"]
            or int(operation.get("source_ship_id") or 0) != int(ship.id)
        ):
            return (
                "An active orbital band survey targets a different ship or body. "
                "Use 'survey scan band status', 'survey scan band clear', or "
                "'survey scan band start' to begin a new pass."
            )

    if must_start:
        radius, resolution, sensor_quality, max_radius, max_resolution, limit_notes = _ship_scan_limits(
            ship,
            int(radius),
            int(resolution),
        )
        requested_y = int(band_y) if band_y is not None else int(context["center_y"])
        clipped_y = _clamp_int(requested_y, minimum=0, maximum=body_height - 1)
        if clipped_y != requested_y:
            limit_notes.append(f"band y {requested_y} clipped to {clipped_y} by body bounds")

        operation = {
            "system_name": context["system_name"],
            "body_id": context["body_id"],
            "body_name": context["body_name"],
            "source_ship_id": int(ship.id),
            "source_ship_name": _ship_name(ship),
            "band_y": clipped_y,
            "next_x": 0,
            "x_max": body_width - 1,
            "radius": radius,
            "resolution": resolution,
            "quality": sensor_quality,
            "max_radius": max_radius,
            "max_resolution": max_resolution,
            "body_width": body_width,
            "body_height": body_height,
            "limit_notes": limit_notes,
        }
    else:
        radius = int(operation.get("radius", DEFAULT_SCAN_RADIUS))
        resolution = int(operation.get("resolution", DEFAULT_SCAN_RESOLUTION))
        sensor_quality = int(operation.get("quality", DEFAULT_SCAN_QUALITY))
        max_radius = int(operation.get("max_radius", radius))
        max_resolution = int(operation.get("max_resolution", resolution))
        limit_notes = list(operation.get("limit_notes") or [])

    next_x = int(operation.get("next_x", 0))
    x_max = int(operation.get("x_max", body_width - 1))
    band_center_y = int(operation.get("band_y", context["center_y"]))

    if next_x > x_max:
        _clear_band_operation(caller)
        return "Orbital band survey operation is already complete."

    center_x = next_x
    points = _bounded_scan_points(center_x, band_center_y, radius, body_width, body_height)
    if not points:
        return "Band survey step produced no valid surface points."

    stride = max(1, radius * 2 + 1)
    following_x = center_x + stride
    is_complete = following_x > x_max

    records, created_count, updated_count = _write_scan_records(
        context,
        points,
        center_x=center_x,
        center_y=band_center_y,
        resolution=resolution,
        quality=sensor_quality,
        metadata={
            "scan_method": "orbital_band_survey",
            "scan_shape": "horizontal_band_step",
            "scan_radius": radius,
            "ship_survey_max_radius": max_radius,
            "ship_survey_max_resolution": max_resolution,
            "band_y": band_center_y,
            "band_step_center_x": center_x,
            "band_step_stride": stride,
            "band_body_width": body_width,
            "band_operation_complete": is_complete,
        },
    )

    operation["next_x"] = following_x
    if is_complete:
        _clear_band_operation(caller)
    else:
        _write_band_operation(caller, operation)

    progress_end = min(following_x - 1, x_max)
    progress_line = f"Band progress: scanned through x {progress_end} of {x_max}."
    if is_complete:
        next_line = "Band operation complete."
    else:
        next_line = f"Next step: survey scan band next (center x {following_x})."

    return render_orbital_scan_report(
        ship_name=_ship_name(ship),
        body_name=context["body_name"],
        center_x=center_x,
        center_y=band_center_y,
        radius=int(radius),
        records=records,
        created_count=created_count,
        updated_count=updated_count,
        limit_notes=limit_notes,
        title="Orbital band terrain survey step complete.",
        footprint_label=(
            f"Band step: y {band_center_y}, center x {center_x}, "
            f"radius {radius}, {len(records)} tile(s)"
        ),
        detail_lines=[progress_line, next_line],
    )
