"""
Orbital survey scan mechanics.

v0.1 scope:
    - `survey scan` runs from the caller's current ship
    - current ship must be in orbit
    - caller must have crew+/owner/admin access to operate the ship
    - scan writes mutable SurveyCoverage rows for the caller
    - default scan uses a deterministic, capped square surface footprint
    - band scan advances a resumable timed horizontal orbital pass
    - scan returns a semantic report suitable for screen-reader users

This deliberately does not create SurveyDataset records directly. Datasets are
still exported/snapshotted with `survey export <name>`.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Mapping
from typing import Any

from world.player.preferences import get_player_preference
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
SURVEY_TARGET_ATTR = "survey_scan_target"
SURVEY_BAND_OPERATION_ATTR = "survey_band_operation"
SURVEY_BAND_SCRIPT_KEY = "orbital_band_survey_timer"
SURVEY_BAND_SCRIPT_PATH = "world.survey.scripts.OrbitalBandSurveyScript"
DEFAULT_BAND_STEP_SECONDS = 60
MIN_BAND_STEP_SECONDS = 5
MAX_BAND_STEP_SECONDS = 3600

RESOLUTION_TIER_LABELS = {
    1: "terrain pass",
    2: "environment pass",
    3: "analysis pass",
}

RESOLUTION_LAYER_LABELS = {
    1: ("terrain", "elevation", "temperature", "radiation"),
    2: ("hazards", "roughness", "traversal"),
    3: ("resources", "anomalies", "site notes"),
}


SCAN_USAGE = (
    "Usage: survey scan [target <x> <y>] [radius <number>] [resolution <number>] or "
    "survey scan band [start, status, pause, resume, step, or cancel] "
    "[y <number>] [radius <number>] [resolution <number>] [interval <seconds>]"
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


def _first_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    """Return the first non-empty value from a mapping."""
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    """Return value as a list without splitting strings."""
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _float_or_none(value: Any) -> float | None:
    """Best-effort float conversion."""
    try:
        return float(value)
    except Exception:
        return None


def _compact_generated_payload(generated: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    """Flatten generated surface data into survey-friendly fields."""
    terrain_code = _first_value(sample, "terrain")
    terrain_label = _first_value(sample, "terrain_label", "terrain_name", "name")

    raw = {
        "x": _first_value(sample, "x"),
        "y": _first_value(sample, "y"),
        "terrain": terrain_label or terrain_code or _first_value(generated, "terrain", "terrain_label", "name"),
        "terrain_code": terrain_code,
        "terrain_label": terrain_label,
        "elevation_m": _first_value(sample, "elevation_m", "elevation"),
        "temperature_k": _first_value(sample, "temperature_k", "temperature"),
        "radiation": _first_value(sample, "radiation"),
        "gravity": _first_value(sample, "gravity_g", "gravity"),
        "summary": _first_value(generated, "description", "summary", "desc"),
        "surface_title": _first_value(generated, "title"),
    }

    compact = compact_tile_data(
        {key: value for key, value in raw.items() if value is not None and value != ""}
    )

    feature_tags = _as_list(_first_value(sample, "feature_tags", "tags"))
    if feature_tags:
        compact["feature_tags"] = [str(tag) for tag in feature_tags]

    return compact


def _resolution_tier(resolution: int) -> str:
    """Return a player-facing resolution tier label."""
    return RESOLUTION_TIER_LABELS.get(min(max(1, int(resolution)), 3), "analysis pass")


def _resolution_layers(resolution: int) -> list[str]:
    """Return scan data layers revealed at this resolution."""
    layers: list[str] = []
    for tier in range(1, min(max(1, int(resolution)), 3) + 1):
        layers.extend(RESOLUTION_LAYER_LABELS[tier])
    return layers


def _temperature_band(temp_k: float | None) -> str | None:
    """Return coarse temperature band."""
    if temp_k is None:
        return None
    if temp_k >= 750:
        return "thermal rupture"
    if temp_k >= 330:
        return "hot"
    if temp_k <= 120:
        return "cryogenic"
    if temp_k <= 180:
        return "frozen"
    if temp_k <= 240:
        return "cold"
    return "nominal"


def _radiation_band(radiation: float | None) -> str | None:
    """Return coarse radiation band."""
    if radiation is None:
        return None
    if radiation >= 1.0:
        return "hard"
    if radiation >= 0.65:
        return "elevated"
    if radiation >= 0.35:
        return "noticeable"
    return "low"


def _gravity_band(gravity_g: float | None) -> str | None:
    """Return coarse gravity band."""
    if gravity_g is None:
        return None
    if gravity_g >= 1.4:
        return "high"
    if gravity_g <= 0.35:
        return "low"
    if gravity_g <= 0.75:
        return "light"
    return "nominal"


def _roughness_class(roughness: float | None) -> str | None:
    """Return coarse terrain roughness class."""
    if roughness is None:
        return None
    if roughness >= 0.78:
        return "severe"
    if roughness >= 0.58:
        return "rough"
    if roughness >= 0.35:
        return "broken"
    return "smooth"


def _add_unique(values: list[str], value: str) -> None:
    """Append a string if it is not already present."""
    if value and value not in values:
        values.append(value)


def _derive_hazards(data: dict[str, Any]) -> tuple[list[str], int, str]:
    """Derive first-pass hazard tags from known surface readings."""
    hazards: list[str] = []
    score = 0

    terrain = str(data.get("terrain_code") or data.get("terrain") or "").lower()
    tags = {str(tag).lower() for tag in _as_list(data.get("feature_tags"))}
    temp_k = _float_or_none(data.get("temperature_k") or data.get("temperature"))
    radiation = _float_or_none(data.get("radiation"))
    gravity = _float_or_none(data.get("gravity") or data.get("gravity_g"))
    roughness = _float_or_none(data.get("roughness"))

    if "lava" in terrain or "thermal" in terrain:
        _add_unique(hazards, "active thermal terrain")
        score += 75
    if "unlandable" in terrain:
        _add_unique(hazards, "unlandable surface")
        score += 90
    if "steep" in tags:
        _add_unique(hazards, "steep terrain")
        score += 25
    if "rough" in tags:
        _add_unique(hazards, "broken ground")
        score += 18

    if temp_k is not None:
        if temp_k >= 750:
            _add_unique(hazards, "thermal rupture exposure")
            score += 80
        elif temp_k >= 330:
            _add_unique(hazards, "heat stress")
            score += 35
        elif temp_k <= 120:
            _add_unique(hazards, "cryogenic exposure")
            score += 45
        elif temp_k <= 180:
            _add_unique(hazards, "severe cold")
            score += 25

    if radiation is not None:
        if radiation >= 1.0:
            _add_unique(hazards, "hard radiation")
            score += 55
        elif radiation >= 0.65:
            _add_unique(hazards, "elevated radiation")
            score += 25

    if roughness is not None:
        if roughness >= 0.78:
            _add_unique(hazards, "severe surface roughness")
            score += 28
        elif roughness >= 0.58:
            _add_unique(hazards, "rough traversal")
            score += 12

    if gravity is not None:
        if gravity >= 1.4:
            _add_unique(hazards, "high-gravity fatigue")
            score += 20
        elif gravity <= 0.35:
            _add_unique(hazards, "low-gravity footing")
            score += 12

    score = max(0, min(100, score))
    if score >= 75:
        level = "severe"
    elif score >= 45:
        level = "high"
    elif score >= 20:
        level = "elevated"
    elif hazards:
        level = "low"
    else:
        level = "none"

    return hazards, score, level


def _direction_summary(directions: Mapping[str, Any]) -> dict[str, list[str]]:
    """Summarize generated movement profiles for survey readouts."""
    blocked: list[str] = []
    rough: list[str] = []
    easy: list[str] = []

    for direction, raw_profile in directions.items():
        profile = _as_dict(raw_profile)
        if not profile:
            continue

        if profile.get("allowed") is False:
            blocked.append(str(direction))
            continue

        severity = str(profile.get("severity") or "").lower()
        if severity == "rough":
            rough.append(str(direction))
        elif severity == "easy":
            easy.append(str(direction))

    return {
        "blocked_directions": blocked,
        "rough_directions": rough,
        "easy_directions": easy[:4],
    }


def _signature_confidence(system_name: str, body_id: str, x: int, y: int, signature: str, quality: int) -> str:
    """Return deterministic confidence for a survey signature."""
    roll = (_stable_int(system_name, body_id, x, y, signature) % 100) + int(quality) // 5
    if roll >= 90:
        return "strong"
    if roll >= 55:
        return "moderate"
    return "trace"


def _resource_signatures(
    system_data: dict[str, Any],
    body: dict[str, Any],
    x: int,
    y: int,
    data: dict[str, Any],
    quality: int,
) -> list[str]:
    """Return deterministic first-pass resource signatures."""
    system_name = str(system_data.get("name", "Unknown System"))
    body_id = str(body.get("id", data.get("body_id", "unknown-body")))
    classification = str(body.get("classification", "")).lower()
    terrain = str(data.get("terrain_code") or data.get("terrain") or "").lower()
    tags = {str(tag).lower() for tag in _as_list(data.get("feature_tags"))}
    temp_band = str(data.get("temperature_band") or "").lower()
    radiation_band = str(data.get("radiation_band") or "").lower()

    candidates: list[str] = []
    if any(key in terrain for key in ("basalt", "lava", "mountain", "highland", "upland", "crater")):
        candidates.extend(["silicate outcrops", "metal-bearing regolith"])
    if any(key in terrain for key in ("ice", "frozen")) or "ice" in tags or temp_band in {"frozen", "cryogenic"}:
        candidates.append("volatile ice")
    if "dust" in terrain or "plain" in terrain:
        candidates.append("fine regolith")
    if "rocky" in classification or "moon" in str(body.get("kind", "")).lower():
        candidates.append("exposed mineral veins")
    if radiation_band in {"elevated", "hard"}:
        candidates.append("irradiated surface deposits")

    if not candidates:
        candidates.append("general regolith sample")

    signatures: list[str] = []
    for candidate in candidates:
        confidence = _signature_confidence(system_name, body_id, x, y, candidate, quality)
        _add_unique(signatures, f"{confidence} {candidate}")

    return signatures[:4]


def _anomaly_signatures(
    system_data: dict[str, Any],
    body: dict[str, Any],
    x: int,
    y: int,
    data: dict[str, Any],
    quality: int,
) -> list[str]:
    """Return deterministic first-pass anomaly signatures."""
    system_name = str(system_data.get("name", "Unknown System"))
    body_id = str(body.get("id", data.get("body_id", "unknown-body")))
    terrain = str(data.get("terrain_code") or data.get("terrain") or "").lower()
    roughness = _float_or_none(data.get("roughness"))
    radiation = _float_or_none(data.get("radiation"))
    temp_k = _float_or_none(data.get("temperature_k") or data.get("temperature"))

    anomalies: list[str] = []
    if radiation is not None and radiation >= 1.0:
        _add_unique(anomalies, "radiation discontinuity")
    if temp_k is not None and (temp_k >= 750 or temp_k <= 120):
        _add_unique(anomalies, "thermal irregularity")
    if roughness is not None and roughness >= 0.78 and any(key in terrain for key in ("crater", "mountain")):
        _add_unique(anomalies, "subsurface density contrast")

    roll = (_stable_int(system_name, body_id, x, y, "survey-anomaly") % 100)
    threshold = 6 + min(12, int(quality) // 10)
    if roll < threshold:
        choices = [
            "albedo discontinuity",
            "magnetic scatter",
            "shallow void return",
            "reflective inclusion",
        ]
        index = _stable_int(system_name, body_id, x, y, "survey-anomaly-kind") % len(choices)
        _add_unique(anomalies, choices[index])

    return anomalies[:3]


def _apply_resolution_layers(
    data: dict[str, Any],
    system_data: dict[str, Any],
    body: dict[str, Any],
    x: int,
    y: int,
    *,
    resolution: int,
    quality: int,
    sample: dict[str, Any] | None = None,
    directions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Add resolution-gated survey layers to a tile payload."""
    resolution = max(1, int(resolution))
    quality = max(1, int(quality))
    sample = sample or {}
    enriched = dict(data or {})

    enriched["survey_resolution"] = resolution
    enriched["scan_resolution_tier"] = _resolution_tier(resolution)
    enriched["scan_layers"] = _resolution_layers(resolution)

    if resolution >= 2:
        roughness = _first_value(sample, "roughness")
        if roughness is not None:
            enriched["roughness"] = roughness

        temp_k = _float_or_none(enriched.get("temperature_k") or enriched.get("temperature"))
        radiation = _float_or_none(enriched.get("radiation"))
        gravity = _float_or_none(enriched.get("gravity") or enriched.get("gravity_g"))
        roughness_value = _float_or_none(enriched.get("roughness"))

        temp_band = _temperature_band(temp_k)
        radiation_band = _radiation_band(radiation)
        gravity_band = _gravity_band(gravity)
        roughness_label = _roughness_class(roughness_value)

        if temp_band:
            enriched["temperature_band"] = temp_band
        if radiation_band:
            enriched["radiation_band"] = radiation_band
        if gravity_band:
            enriched["gravity_band"] = gravity_band
        if roughness_label:
            enriched["roughness_class"] = roughness_label

        hazards, hazard_score, hazard_level = _derive_hazards(enriched)
        enriched["hazard_score"] = hazard_score
        enriched["hazard_level"] = hazard_level
        if hazards:
            enriched["hazards"] = hazards
            enriched["hazard"] = hazard_level

        if directions:
            enriched["traversal"] = _direction_summary(directions)

    if resolution >= 3:
        resources = _resource_signatures(system_data, body, x, y, enriched, quality)
        if resources:
            enriched["resource_signatures"] = resources

        anomalies = _anomaly_signatures(system_data, body, x, y, enriched, quality)
        if anomalies:
            enriched["anomaly_signatures"] = anomalies

        notes = []
        if enriched.get("hazard_level") in {"high", "severe"}:
            notes.append("high-resolution pass recommends remote verification before landing.")
        if enriched.get("resource_signatures"):
            notes.append("resource signatures are candidates, not confirmed extractable deposits.")
        if enriched.get("anomaly_signatures"):
            notes.append("anomaly signatures merit a focused follow-up survey.")
        if notes:
            enriched["survey_notes"] = notes

    return enriched


def _scan_tile_data(
    system_data: dict[str, Any],
    body: dict[str, Any],
    x: int,
    y: int,
    *,
    resolution: int,
    quality: int,
) -> dict[str, Any]:
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
            sample = _as_dict(generated.get("sample"))
            directions = _as_dict(generated.get("directions"))
            compact = _compact_generated_payload(generated, sample)
            return _apply_resolution_layers(
                compact,
                system_data,
                body,
                int(x),
                int(y),
                resolution=resolution,
                quality=quality,
                sample=sample,
                directions=directions,
            )
    except Exception:
        pass

    return _apply_resolution_layers(
        _surface_tile_payload(body, x, y),
        system_data,
        body,
        int(x),
        int(y),
        resolution=resolution,
        quality=quality,
    )


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


def _include_visual_scan_footprint(caller: Any) -> bool:
    """Return whether scan reports should include the visual footprint."""
    try:
        return get_player_preference(caller, "survey_map", default="visual") == "visual"
    except Exception:
        return True


def _read_survey_target(caller: Any) -> dict[str, Any]:
    """Read caller's saved orbital survey target."""
    try:
        raw = caller.attributes.get(SURVEY_TARGET_ATTR)
    except Exception:
        raw = None

    return dict(raw) if isinstance(raw, Mapping) else {}


def _write_survey_target(caller: Any, target: dict[str, Any]) -> None:
    """Persist caller's saved orbital survey target."""
    caller.attributes.add(SURVEY_TARGET_ATTR, dict(target))


def _clear_survey_target(caller: Any) -> None:
    """Clear caller's saved orbital survey target."""
    try:
        caller.attributes.remove(SURVEY_TARGET_ATTR)
    except Exception:
        pass


def _target_matches_context(target: dict[str, Any], context: dict[str, Any]) -> bool:
    """Return whether a saved target still applies to the current orbital body."""
    try:
        return (
            str(target.get("system_name")) == context["system_name"]
            and str(target.get("body_id")) == context["body_id"]
            and int(target.get("source_ship_id") or 0) == int(context["ship"].id)
        )
    except Exception:
        return False


def _parse_int_token(token: str, label: str) -> tuple[int | None, str]:
    """Parse a coordinate token."""
    try:
        return int(token), ""
    except Exception:
        return None, f"{label} coordinate must be a number."


def _parse_target_coordinates(tokens: list[str], start: int) -> tuple[int | None, int | None, int, str]:
    """Parse x/y target coordinates from tokens starting at index."""
    if start >= len(tokens):
        return None, None, start, "Usage: survey scan target <x> <y>"

    token = tokens[start].lower()
    if token in {"x", "cx", "lon", "longitude"}:
        if start + 3 >= len(tokens):
            return None, None, start, "Usage: survey scan target x <number> y <number>"
        x, error = _parse_int_token(tokens[start + 1], "Target x")
        if error:
            return None, None, start, error
        if tokens[start + 2].lower() not in {"y", "cy", "lat", "latitude"}:
            return None, None, start, "Usage: survey scan target x <number> y <number>"
        y, error = _parse_int_token(tokens[start + 3], "Target y")
        if error:
            return None, None, start, error
        return x, y, start + 4, ""

    if start + 1 >= len(tokens):
        return None, None, start, "Usage: survey scan target <x> <y>"

    x, error = _parse_int_token(tokens[start], "Target x")
    if error:
        return None, None, start, error

    y, error = _parse_int_token(tokens[start + 1], "Target y")
    if error:
        return None, None, start, error

    return x, y, start + 2, ""


def parse_scan_options(args: str) -> tuple[dict[str, Any], str]:
    """
    Parse player-facing survey scan options.

    Supported:
        survey scan
        survey scan target 10 25
        survey scan at 10 25 radius 2
        survey scan radius 2
        survey scan resolution 2
        survey scan radius 2 resolution 2
        survey scan band
        survey scan band start y 25 radius 1 resolution 2
        survey scan band status
        survey scan band pause
        survey scan band resume
        survey scan band step
        survey scan band cancel

    Values are capped later by the current ship's survey capabilities.
    """
    tokens = (args or "").split()
    options = {
        "mode": "footprint",
        "radius": DEFAULT_SCAN_RADIUS,
        "resolution": DEFAULT_SCAN_RESOLUTION,
        "band_action": "status",
        "band_y": None,
        "target_x": None,
        "target_y": None,
        "target_source": "",
        "interval": None,
    }

    i = 0
    if tokens and tokens[0].lower() in {"band", "bands"}:
        options["mode"] = "band"
        i = 1

        if i < len(tokens) and tokens[i].lower() in {
            "start",
            "status",
            "pause",
            "resume",
            "cancel",
            "clear",
            "step",
            "next",
        }:
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

        if options["mode"] == "footprint" and token in {
            "target",
            "at",
            "center",
            "centre",
            "coord",
            "coords",
            "coordinate",
            "coordinates",
        }:
            x, y, next_i, error = _parse_target_coordinates(tokens, i + 1)
            if error:
                return options, error
            options["target_x"] = x
            options["target_y"] = y
            options["target_source"] = "command target"
            i = next_i
            continue

        if options["mode"] == "footprint" and token in {"x", "cx", "lon", "longitude"}:
            x, y, next_i, error = _parse_target_coordinates(tokens, i)
            if error:
                return options, error
            options["target_x"] = x
            options["target_y"] = y
            options["target_source"] = "command target"
            i = next_i
            continue

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

        if options["mode"] == "band" and token in {"interval", "seconds", "time"}:
            if i + 1 >= len(tokens):
                return options, "Usage: survey scan band start interval <seconds>"
            try:
                interval = int(tokens[i + 1])
            except ValueError:
                return options, "Band survey interval must be a number of seconds."

            if interval < MIN_BAND_STEP_SECONDS:
                return options, f"Band survey interval must be at least {MIN_BAND_STEP_SECONDS} seconds."

            options["interval"] = min(interval, MAX_BAND_STEP_SECONDS)
            i += 2
            continue

        return options, SCAN_USAGE

    return options, ""


def _coverage_record(
    owner_scope: str,
    owner_id: int,
    system_name: str,
    body_id: str,
    x: int,
    y: int,
    scan_type: str,
) -> SurveyCoverage | None:
    """Return an existing matching coverage row, if present."""
    try:
        return SurveyCoverage.objects.get(
            owner_scope=owner_scope,
            owner_id=int(owner_id),
            system_name=str(system_name),
            body_id=str(body_id),
            x=int(x),
            y=int(y),
            scan_type=str(scan_type),
        )
    except SurveyCoverage.DoesNotExist:
        return None


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


def _clamp_target_to_context(
    context: dict[str, Any],
    x: int,
    y: int,
) -> tuple[int, int, list[str]]:
    """Clamp target coordinates to the current body's survey grid."""
    body_width = max(1, int(context["body_width"]))
    body_height = max(1, int(context["body_height"]))
    clipped_x = _clamp_int(int(x), minimum=0, maximum=body_width - 1)
    clipped_y = _clamp_int(int(y), minimum=0, maximum=body_height - 1)
    notes = []
    if clipped_x != int(x) or clipped_y != int(y):
        notes.append(
            f"target {int(x)},{int(y)} clipped to {clipped_x},{clipped_y} by body bounds"
        )
    return clipped_x, clipped_y, notes


def _target_from_context(context: dict[str, Any], x: int, y: int, *, requested_x: int | None = None, requested_y: int | None = None) -> dict[str, Any]:
    """Build a saved survey target payload for this orbital context."""
    return {
        "system_name": context["system_name"],
        "body_id": context["body_id"],
        "body_name": context["body_name"],
        "source_ship_id": int(context["ship"].id),
        "source_ship_name": _ship_name(context["ship"]),
        "x": int(x),
        "y": int(y),
        "requested_x": int(requested_x) if requested_x is not None else int(x),
        "requested_y": int(requested_y) if requested_y is not None else int(y),
        "body_width": int(context["body_width"]),
        "body_height": int(context["body_height"]),
        "updated_at": int(time.time()),
    }


def _resolve_scan_center(
    caller: Any,
    context: dict[str, Any],
    *,
    target_x: int | None,
    target_y: int | None,
    target_source: str = "",
) -> tuple[int, int, str, list[str]]:
    """Resolve final footprint scan center from command target, saved target, or default."""
    notes: list[str] = []

    if target_x is not None and target_y is not None:
        x, y, target_notes = _clamp_target_to_context(context, int(target_x), int(target_y))
        notes.extend(target_notes)
        return x, y, target_source or "command target", notes

    saved = _read_survey_target(caller)
    if saved:
        if _target_matches_context(saved, context):
            try:
                saved_x = int(saved.get("x"))
                saved_y = int(saved.get("y"))
            except Exception:
                notes.append("saved survey target is incomplete and was ignored")
            else:
                x, y, target_notes = _clamp_target_to_context(context, saved_x, saved_y)
                notes.extend(target_notes)
                return x, y, "saved target", notes

        else:
            notes.append(
                "saved survey target is for a different ship or body and was ignored"
            )

    x, y, target_notes = _clamp_target_to_context(
        context,
        int(context["center_x"]),
        int(context["center_y"]),
    )
    notes.extend(target_notes)
    return x, y, "default orbital center", notes


def render_survey_target(caller: Any, args: str = "") -> str:
    """Render, set, or clear the caller's saved orbital survey target."""
    tokens = (args or "").split()
    action = tokens[0].lower() if tokens else "status"

    if action in {"clear", "cancel", "reset", "none"}:
        _clear_survey_target(caller)
        return "Cleared saved survey target."

    context, error = _resolve_orbital_scan_context(caller)
    saved = _read_survey_target(caller)
    if error:
        if saved:
            lines = [
                "Saved survey target",
                f"  Body: {saved.get('system_name')}/{saved.get('body_name') or saved.get('body_id')}",
                f"  Coordinates: {saved.get('x')},{saved.get('y')}",
                f"  Ship: {saved.get('source_ship_name') or saved.get('source_ship_id')}",
                "",
                f"Current orbit unavailable: {error}",
            ]
            return "\n".join(lines)
        return error

    if action in {"status", "show", "info"}:
        coord_start = -1
    elif action in {"set", "target", "at", "center", "centre"}:
        coord_start = 1
    elif tokens:
        coord_start = 0
    else:
        coord_start = -1

    if coord_start >= 0:
        x, y, next_i, coord_error = _parse_target_coordinates(tokens, coord_start)
        if coord_error:
            return "Usage: survey target <x> <y>, survey target clear"
        if next_i < len(tokens):
            return "Usage: survey target <x> <y>, survey target clear"
        clipped_x, clipped_y, notes = _clamp_target_to_context(context, int(x), int(y))
        target = _target_from_context(
            context,
            clipped_x,
            clipped_y,
            requested_x=int(x),
            requested_y=int(y),
        )
        _write_survey_target(caller, target)
        lines = [
            "Saved survey target.",
            f"  Body: {context['system_name']}/{context['body_name']}",
            f"  Coordinates: {clipped_x},{clipped_y}",
            f"  Ship: {_ship_name(context['ship'])}",
        ]
        if notes:
            lines.append(f"  Note: {'; '.join(notes)}.")
        lines.append("Use survey scan to scan this target, or survey scan target <x> <y> for a one-shot override.")
        return "\n".join(lines)

    default_x = int(context["center_x"])
    default_y = int(context["center_y"])
    lines = [
        "Survey target",
        f"  Current body: {context['system_name']}/{context['body_name']}",
        f"  Body grid: 0-{int(context['body_width']) - 1} x, 0-{int(context['body_height']) - 1} y",
        f"  Default scan center: {default_x},{default_y}",
    ]

    if saved:
        if _target_matches_context(saved, context):
            lines.append(f"  Saved target: {saved.get('x')},{saved.get('y')}")
        else:
            lines.append(
                "  Saved target: ignored; it belongs to a different ship or body"
            )
    else:
        lines.append("  Saved target: none")

    lines.append("")
    lines.append("Use survey target <x> <y> to save a target.")
    lines.append("Use survey scan target <x> <y> for a one-shot scan center.")
    lines.append("Use survey target clear to return to the default orbital center.")
    return "\n".join(lines)


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
        existing = _coverage_record(
            owner_scope,
            owner_id,
            system_name,
            body_id,
            int(x),
            int(y),
            SCAN_TERRAIN,
        )
        existed = existing is not None
        previous_resolution = int(existing.resolution or 0) if existing is not None else 0
        previous_quality = int(existing.quality or 0) if existing is not None else 0
        resolution_upgraded = existed and int(resolution) > previous_resolution
        quality_improved = existed and int(quality) > previous_quality
        if not existed:
            coverage_update = "new"
        elif resolution_upgraded:
            coverage_update = "resolution_upgraded"
        elif quality_improved:
            coverage_update = "quality_improved"
        else:
            coverage_update = "refreshed"

        best_resolution = max(previous_resolution, int(resolution))
        data = _scan_tile_data(
            system_data,
            body,
            int(x),
            int(y),
            resolution=resolution,
            quality=quality,
        )
        data.update(
            {
                "scan_center": {"x": center_x, "y": center_y},
                "scan_resolution": resolution,
                "best_known_resolution": best_resolution,
                "last_scan_resolution": resolution,
                "sensor_quality": quality,
                "source_ship_name": _ship_name(ship),
                "coverage_update": coverage_update,
                "previous_resolution": previous_resolution,
                "previous_quality": previous_quality,
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
                "previous_resolution": previous_resolution,
                "previous_quality": previous_quality,
                "resolution_upgraded": resolution_upgraded,
                "quality_improved": quality_improved,
                "coverage_update": coverage_update,
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


def _band_step_seconds(radius: int, resolution: int, interval: int | None = None) -> int:
    """Return seconds per timed band step."""
    if interval is not None:
        return _clamp_int(int(interval), minimum=MIN_BAND_STEP_SECONDS, maximum=MAX_BAND_STEP_SECONDS)

    multiplier = max(1, int(radius)) * max(1, int(resolution))
    return _clamp_int(
        DEFAULT_BAND_STEP_SECONDS * multiplier,
        minimum=MIN_BAND_STEP_SECONDS,
        maximum=MAX_BAND_STEP_SECONDS,
    )


def _band_stride(operation: dict[str, Any]) -> int:
    """Return x-advance per band step."""
    return max(1, int(operation.get("radius", DEFAULT_SCAN_RADIUS)) * 2 + 1)


def _band_remaining_steps(operation: dict[str, Any]) -> int:
    """Return approximate number of remaining band steps."""
    next_x = int(operation.get("next_x", 0))
    x_max = int(operation.get("x_max", 0))
    if next_x > x_max:
        return 0
    return int(math.ceil((x_max - next_x + 1) / float(_band_stride(operation))))


def _get_band_scripts(caller: Any) -> list[Any]:
    """Return active band timer scripts attached to caller."""
    try:
        scripts = caller.scripts.get(key=SURVEY_BAND_SCRIPT_KEY)
    except Exception:
        return []

    if not scripts:
        return []

    if isinstance(scripts, (list, tuple)):
        return list(scripts)

    try:
        return list(scripts)
    except Exception:
        return [scripts]


def _stop_band_timer(caller: Any) -> None:
    """Stop all band timer scripts attached to caller."""
    for script in _get_band_scripts(caller):
        try:
            script.stop()
        except Exception:
            pass


def _start_band_timer(caller: Any, interval: int) -> str:
    """Start or restart the timed band survey script."""
    _stop_band_timer(caller)

    try:
        from evennia.utils.create import create_script  # type: ignore

        script = create_script(
            SURVEY_BAND_SCRIPT_PATH,
            key=SURVEY_BAND_SCRIPT_KEY,
            obj=caller,
            interval=int(interval),
            start_delay=True,
            persistent=True,
            autostart=True,
        )
        script.interval = int(interval)
        script.start_delay = True
        script.persistent = True
        return ""
    except Exception as err:
        return f"Could not start orbital band survey timer: {err}"


def _pause_band_timer(caller: Any) -> None:
    """Pause active band timer scripts."""
    for script in _get_band_scripts(caller):
        try:
            script.pause()
        except Exception:
            pass


def _resume_band_timer(caller: Any, interval: int) -> str:
    """Resume an active band timer, or recreate it if missing."""
    scripts = _get_band_scripts(caller)
    if not scripts:
        return _start_band_timer(caller, interval)

    for script in scripts:
        try:
            script.interval = int(interval)
            script.unpause()
        except Exception as err:
            return f"Could not resume orbital band survey timer: {err}"

    return ""


def _band_time_until_next(caller: Any) -> int | None:
    """Return seconds until next timer tick, if available."""
    scripts = _get_band_scripts(caller)
    if not scripts:
        return None

    try:
        value = scripts[0].time_until_next_repeat()
        return int(value) if value is not None else None
    except Exception:
        return None


def _format_band_operation(caller: Any, operation: dict[str, Any]) -> str:
    """Render compact band operation status."""
    if not operation:
        return "No active orbital band survey operation."

    next_x = int(operation.get("next_x", 0))
    x_max = int(operation.get("x_max", 0))
    complete = next_x > x_max
    status = "complete" if complete else str(operation.get("status") or "paused")
    remaining_steps = _band_remaining_steps(operation)
    step_seconds = int(operation.get("step_seconds", DEFAULT_BAND_STEP_SECONDS))
    next_tick = _band_time_until_next(caller)

    lines = [
        "Orbital band survey operation",
        f"  Status: {status}",
        f"  Body: {operation.get('system_name')}/{operation.get('body_name') or operation.get('body_id')}",
        f"  Band y: {operation.get('band_y')}",
        f"  Radius per step: {operation.get('radius')}",
        f"  Resolution: {operation.get('resolution')}",
        f"  Step interval: {step_seconds} seconds",
        f"  Remaining steps: {remaining_steps}",
        f"  Next center x: {next_x if not complete else 'none'}",
        f"  Final x: {x_max}",
    ]

    if next_tick is not None and status == "running":
        lines.append(f"  Next automatic step in: {next_tick} seconds")

    if operation.get("last_error"):
        lines.append(f"  Last interruption: {operation.get('last_error')}")

    return "\n".join(lines)


def run_orbital_survey_scan(
    caller,
    *,
    radius: int = DEFAULT_SCAN_RADIUS,
    resolution: int = DEFAULT_SCAN_RESOLUTION,
    mode: str = "footprint",
    band_action: str = "next",
    band_y: int | None = None,
    target_x: int | None = None,
    target_y: int | None = None,
    target_source: str = "",
    interval: int | None = None,
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
            interval=interval,
        )

    context, error = _resolve_orbital_scan_context(caller)
    if error:
        return error

    ship = context["ship"]
    center_x, center_y, center_source, target_notes = _resolve_scan_center(
        caller,
        context,
        target_x=target_x,
        target_y=target_y,
        target_source=target_source,
    )
    radius, resolution, sensor_quality, max_radius, max_resolution, limit_notes = _ship_scan_limits(
        ship,
        int(radius),
        int(resolution),
    )
    limit_notes.extend(target_notes)
    points = _bounded_scan_points(
        center_x,
        center_y,
        radius,
        int(context["body_width"]),
        int(context["body_height"]),
    )

    if not points:
        return "Survey scan produced no valid surface points for that target."

    detail_lines = [
        f"Target selection: {center_source}.",
    ]
    if center_source != "default orbital center":
        detail_lines.append(
            "Use survey target clear to return routine scans to the default orbital center."
        )

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
            "scan_target_source": center_source,
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
        detail_lines=detail_lines,
        include_visual=_include_visual_scan_footprint(caller),
    )


def _validate_band_operation_context(context: dict[str, Any], operation: dict[str, Any]) -> str:
    """Return an error if operation no longer matches current ship/body."""
    ship = context["ship"]
    if (
        operation.get("system_name") != context["system_name"]
        or operation.get("body_id") != context["body_id"]
        or int(operation.get("source_ship_id") or 0) != int(ship.id)
    ):
        return (
            "Active orbital band survey targets a different ship or body. "
            "Use 'survey scan band status', 'survey scan band cancel', or "
            "'survey scan band start' to begin a new pass."
        )
    return ""


def _build_band_operation(
    caller: Any,
    context: dict[str, Any],
    *,
    band_y: int | None,
    radius: int,
    resolution: int,
    interval: int | None,
) -> tuple[dict[str, Any], list[str]]:
    """Build a fresh timed orbital band survey operation."""
    ship = context["ship"]
    body_width = max(1, int(context["body_width"]))
    body_height = max(1, int(context["body_height"]))

    radius, resolution, sensor_quality, max_radius, max_resolution, limit_notes = _ship_scan_limits(
        ship,
        int(radius),
        int(resolution),
    )
    requested_y = int(band_y) if band_y is not None else int(context["center_y"])
    clipped_y = _clamp_int(requested_y, minimum=0, maximum=body_height - 1)
    if clipped_y != requested_y:
        limit_notes.append(f"band y {requested_y} clipped to {clipped_y} by body bounds")

    step_seconds = _band_step_seconds(radius, resolution, interval=interval)
    now = int(time.time())

    operation = {
        "status": "running",
        "system_name": context["system_name"],
        "body_id": context["body_id"],
        "body_name": context["body_name"],
        "source_ship_id": int(ship.id),
        "source_ship_name": _ship_name(ship),
        "operator_id": int(getattr(caller, "id", 0) or 0),
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
        "step_seconds": step_seconds,
        "completed_steps": 0,
        "started_at": now,
        "updated_at": now,
        "last_error": "",
        "limit_notes": limit_notes,
    }
    return operation, limit_notes


def _perform_orbital_band_step(caller: Any, *, from_timer: bool = False) -> tuple[str, bool]:
    """Perform one saved orbital band step. Return message and keep-running flag."""
    operation = _read_band_operation(caller)
    if not operation:
        return "No active orbital band survey operation.", False

    if from_timer and operation.get("status") != "running":
        return "", False

    context, error = _resolve_orbital_scan_context(caller)
    if error:
        operation["status"] = "paused"
        operation["last_error"] = error
        operation["updated_at"] = int(time.time())
        _write_band_operation(caller, operation)
        return f"Orbital band survey paused: {error}", False

    context_error = _validate_band_operation_context(context, operation)
    if context_error:
        operation["status"] = "paused"
        operation["last_error"] = context_error
        operation["updated_at"] = int(time.time())
        _write_band_operation(caller, operation)
        return f"Orbital band survey paused: {context_error}", False

    body_width = max(1, int(context["body_width"]))
    body_height = max(1, int(context["body_height"]))
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
        return "Orbital band survey operation is already complete.", False

    center_x = next_x
    points = _bounded_scan_points(center_x, band_center_y, radius, body_width, body_height)
    if not points:
        operation["status"] = "paused"
        operation["last_error"] = "Band survey step produced no valid surface points."
        _write_band_operation(caller, operation)
        return "Band survey step produced no valid surface points.", False

    stride = _band_stride(operation)
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
            "band_body_height": body_height,
            "band_operation_complete": is_complete,
        },
    )

    operation["next_x"] = following_x
    operation["updated_at"] = int(time.time())
    operation["completed_steps"] = int(operation.get("completed_steps", 0)) + 1
    operation["last_error"] = ""

    if is_complete:
        _clear_band_operation(caller)
    else:
        _write_band_operation(caller, operation)

    progress_end = min(following_x - 1, x_max)
    progress_line = f"Band progress: scanned through x {progress_end} of {x_max}."
    if is_complete:
        next_line = "Band operation complete."
    elif from_timer:
        remaining_steps = _band_remaining_steps(operation)
        next_line = f"Automatic survey continuing; {remaining_steps} step(s) remain."
    else:
        next_line = f"Next automatic step will use center x {following_x}."

    report = render_orbital_scan_report(
        ship_name=_ship_name(context["ship"]),
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
        include_visual=_include_visual_scan_footprint(caller),
    )
    return report, not is_complete


def run_orbital_band_survey_tick(caller: Any) -> tuple[str, bool]:
    """Run one timed orbital band survey tick for a Script."""
    return _perform_orbital_band_step(caller, from_timer=True)


def run_orbital_band_survey_step(
    caller,
    *,
    action: str = "status",
    band_y: int | None = None,
    radius: int = DEFAULT_SCAN_RADIUS,
    resolution: int = DEFAULT_SCAN_RESOLUTION,
    interval: int | None = None,
) -> str:
    """Handle user-facing timed orbital band survey controls."""
    action = (action or "status").lower()
    if action == "clear":
        action = "cancel"
    if action == "next":
        action = "step"

    if action == "cancel":
        _stop_band_timer(caller)
        _clear_band_operation(caller)
        return "Cancelled active orbital band survey operation."

    if action == "status":
        return _format_band_operation(caller, _read_band_operation(caller))

    if action == "pause":
        operation = _read_band_operation(caller)
        if not operation:
            return "No active orbital band survey operation."
        operation["status"] = "paused"
        operation["updated_at"] = int(time.time())
        _write_band_operation(caller, operation)
        _pause_band_timer(caller)
        return "Paused orbital band survey operation."

    if action == "resume":
        operation = _read_band_operation(caller)
        if not operation:
            return "No active orbital band survey operation."
        operation["status"] = "running"
        operation["updated_at"] = int(time.time())
        operation["last_error"] = ""
        _write_band_operation(caller, operation)
        error = _resume_band_timer(caller, int(operation.get("step_seconds", DEFAULT_BAND_STEP_SECONDS)))
        if error:
            operation["status"] = "paused"
            operation["last_error"] = error
            _write_band_operation(caller, operation)
            return error
        return "Resumed orbital band survey operation."

    if action == "step":
        report, _keep_running = _perform_orbital_band_step(caller, from_timer=False)
        return report

    if action != "start":
        return SCAN_USAGE

    context, error = _resolve_orbital_scan_context(caller)
    if error:
        return error

    operation, limit_notes = _build_band_operation(
        caller,
        context,
        band_y=band_y,
        radius=radius,
        resolution=resolution,
        interval=interval,
    )
    _write_band_operation(caller, operation)

    timer_error = _start_band_timer(caller, int(operation["step_seconds"]))
    if timer_error:
        operation["status"] = "paused"
        operation["last_error"] = timer_error
        _write_band_operation(caller, operation)
        return timer_error

    lines = [
        "Started timed orbital band survey operation.",
        f"Body: {operation['system_name']}/{operation['body_name']}",
        f"Band y: {operation['band_y']}",
        f"Radius per step: {operation['radius']}",
        f"Resolution: {operation['resolution']}",
        f"Step interval: {operation['step_seconds']} seconds",
        f"Estimated steps: {_band_remaining_steps(operation)}",
        "First automatic step will run after the step interval.",
        "Use survey scan band status, pause, resume, step, or cancel.",
    ]

    if limit_notes:
        lines.append(f"Limits applied: {'; '.join(limit_notes)}.")

    return "\n".join(lines)
