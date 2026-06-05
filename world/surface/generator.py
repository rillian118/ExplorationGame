"""Deterministic planetary surface generation for Exploration MUD v0.3.

This module does not create Evennia rooms. It only samples terrain, movement
costs, blocked directions, and room text from stable inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple


DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
}

ALIASES = {
    "n": "north",
    "e": "east",
    "s": "south",
    "w": "west",
    "north": "north",
    "east": "east",
    "south": "south",
    "west": "west",
}

MAX_MOVE_DELAY = 2.0


@dataclass
class SurfaceSample:
    """Raw deterministic terrain/environment sample for one surface coordinate."""

    system_name: str
    body_id: str
    body_name: str
    x: int
    y: int
    terrain: str
    terrain_label: str
    elevation_m: int
    roughness: float
    temperature_k: float
    radiation: float
    gravity_g: float
    feature_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DirectionProfile:
    """Movement/passability information for one cardinal direction."""

    direction: str
    target_x: int
    target_y: int
    allowed: bool
    delay_seconds: float
    message: str
    blocked_reason: Optional[str] = None
    severity: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SurfaceRoomView:
    """Generated room presentation plus directional movement metadata."""

    sample: SurfaceSample
    title: str
    description: str
    directions: Dict[str, DirectionProfile]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample": self.sample.to_dict(),
            "title": self.title,
            "description": self.description,
            "directions": {key: value.to_dict() for key, value in self.directions.items()},
        }


def normalize_direction(direction: str) -> Optional[str]:
    """Normalize n/e/s/w aliases to full direction names."""
    return ALIASES.get((direction or "").strip().lower())


def _stable_int(*parts: Any) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _unit_noise(*parts: Any) -> float:
    return _stable_int(*parts) / float(2**64 - 1)


def _smooth_value(seed: int, body_id: str, x: int, y: int, scale: int, salt: str) -> float:
    """Very small deterministic value-noise helper.

    This intentionally avoids external dependencies. It is not intended to be
    geologically perfect; it gives stable room-scale variation cheaply.
    """
    gx = math.floor(x / scale)
    gy = math.floor(y / scale)
    fx = (x / scale) - gx
    fy = (y / scale) - gy

    def n(ix: int, iy: int) -> float:
        return _unit_noise(seed, body_id, ix, iy, salt)

    v00 = n(gx, gy)
    v10 = n(gx + 1, gy)
    v01 = n(gx, gy + 1)
    v11 = n(gx + 1, gy + 1)

    # smoothstep interpolation
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    ix0 = v00 * (1 - sx) + v10 * sx
    ix1 = v01 * (1 - sx) + v11 * sx
    return ix0 * (1 - sy) + ix1 * sy


def _fractal(seed: int, body_id: str, x: int, y: int, salt: str) -> float:
    return (
        _smooth_value(seed, body_id, x, y, 64, salt) * 0.50
        + _smooth_value(seed, body_id, x, y, 24, salt + "2") * 0.30
        + _smooth_value(seed, body_id, x, y, 8, salt + "3") * 0.20
    )


def _body_gravity_g(body: Dict[str, Any]) -> float:
    mass = body.get("mass_earth")
    radius = body.get("radius_km")
    if not mass or not radius:
        return 1.0
    try:
        return max(0.02, float(mass) / ((float(radius) / 6371.0) ** 2))
    except Exception:
        return 1.0


def _terrain_from_values(body: Dict[str, Any], elevation_n: float, roughness: float, temp_k: float) -> Tuple[str, str, List[str]]:
    classification = str(body.get("classification", "")).lower()
    kind = str(body.get("kind", "")).lower()
    tags: List[str] = []

    if kind not in {"planet", "moon"}:
        return "unlandable", "Unlandable Surface", ["unlandable"]

    if "gas giant" in classification or "sub-neptune" in classification:
        return "unlandable", "Unlandable Atmospheric Depths", ["unlandable"]

    if temp_k > 750:
        return "lava_field", "Thermal Rupture Field", ["heat", "lava"]

    if temp_k < 120 and elevation_n < 0.35:
        return "ice_plain", "Frozen Low Plain", ["cold", "ice"]

    if elevation_n > 0.82:
        tags.append("steep")
        return "mountains", "Jagged Mountain Terrain", tags

    if elevation_n > 0.66:
        tags.append("elevated")
        if roughness > 0.55:
            return "highlands", "Fractured Highlands", tags
        return "uplands", "Open Uplands", tags

    if roughness > 0.74:
        return "crater_field", "Broken Crater Field", ["rough"]

    if "ice" in classification or temp_k < 180:
        return "ice_field", "Wind-Scored Ice Field", ["cold", "ice"]

    if "dry" in classification or temp_k > 310:
        return "dust_plain", "Dusty Open Plain", ["dry"]

    if "rocky" in classification or "moon" in kind:
        return "basalt_plain", "Basalt Plain", ["rock"]

    return "open_plain", "Open Plain", tags


def sample_surface(system_data: Dict[str, Any], body: Dict[str, Any], x: int, y: int) -> SurfaceSample:
    """Sample deterministic terrain/environment at a surface coordinate."""
    seed = int(system_data.get("seed", 0))
    body_id = str(body.get("id", "unknown-body"))
    body_name = str(body.get("name", body_id))
    system_name = str(system_data.get("name", "Unknown System"))

    elevation_n = _fractal(seed, body_id, x, y, "elevation")
    roughness = _fractal(seed, body_id, x, y, "roughness")
    radiation_n = _fractal(seed, body_id, x, y, "radiation")

    base_temp = float(body.get("temperature_k") or 273.0)
    elevation_m = int((elevation_n - 0.40) * 6200)
    temp_variation = (_unit_noise(seed, body_id, x, y, "temp") - 0.5) * 34.0
    temperature_k = max(1.0, base_temp + temp_variation - max(elevation_m, 0) * 0.0025)
    gravity_g = _body_gravity_g(body)
    radiation = round(max(0.0, radiation_n * 1.25), 3)

    terrain, label, tags = _terrain_from_values(body, elevation_n, roughness, temperature_k)

    return SurfaceSample(
        system_name=system_name,
        body_id=body_id,
        body_name=body_name,
        x=int(x),
        y=int(y),
        terrain=terrain,
        terrain_label=label,
        elevation_m=elevation_m,
        roughness=round(float(roughness), 3),
        temperature_k=round(float(temperature_k), 1),
        radiation=radiation,
        gravity_g=round(gravity_g, 3),
        feature_tags=tags,
    )


def _blocked_reason(direction: str, current: SurfaceSample, neighbor: SurfaceSample, elevation_delta: int) -> str:
    if neighbor.terrain == "unlandable":
        return f"The terrain {direction} is not suitable for traversal on foot."
    if neighbor.terrain == "lava_field":
        return f"A thermal rupture field glows to the {direction}, making travel impossible."
    if abs(elevation_delta) > 900:
        if elevation_delta > 0:
            return f"A sheer escarpment rises to the {direction}, blocking travel toward higher ground."
        return f"The ground drops away into a steep ravine to the {direction}."
    if neighbor.terrain == "mountains" and neighbor.roughness > 0.65:
        return f"Jagged mountain terrain closes off passage to the {direction}."
    return f"The terrain to the {direction} is too difficult to cross safely."


def _movement_message(direction: str, current: SurfaceSample, neighbor: SurfaceSample, severity: str) -> str:
    terrain = neighbor.terrain
    if terrain in {"highlands", "mountains", "crater_field"}:
        if severity == "rough":
            return f"You scramble {direction} across broken {neighbor.terrain_label.lower()}."
        return f"You pick your way {direction} through {neighbor.terrain_label.lower()}."
    if terrain in {"dust_plain", "basalt_plain"}:
        if severity == "rough":
            return f"You trudge {direction} across uneven {neighbor.terrain_label.lower()}."
        return f"You cross {direction} over the {neighbor.terrain_label.lower()}."
    if terrain in {"ice_plain", "ice_field"}:
        return f"You move carefully {direction} across the slick frozen surface."
    return f"You travel {direction}."


def evaluate_direction(system_data: Dict[str, Any], body: Dict[str, Any], x: int, y: int, direction: str) -> DirectionProfile:
    """Evaluate movement from one coordinate to an adjacent coordinate."""
    dx, dy = DIRECTIONS[direction]
    current = sample_surface(system_data, body, x, y)
    neighbor = sample_surface(system_data, body, x + dx, y + dy)
    elevation_delta = neighbor.elevation_m - current.elevation_m
    slope_factor = min(1.0, abs(elevation_delta) / 900.0)

    if neighbor.terrain in {"unlandable", "lava_field"} or slope_factor >= 1.0:
        return DirectionProfile(
            direction=direction,
            target_x=x + dx,
            target_y=y + dy,
            allowed=False,
            delay_seconds=0.0,
            message="",
            blocked_reason=_blocked_reason(direction, current, neighbor, elevation_delta),
            severity="blocked",
        )

    roughness = max(current.roughness, neighbor.roughness)
    gravity_penalty = max(0.0, current.gravity_g - 1.0) * 0.35
    low_g_penalty = max(0.0, 0.35 - current.gravity_g) * 0.60
    terrain_penalty = 0.0
    if neighbor.terrain in {"highlands", "crater_field", "mountains"}:
        terrain_penalty += 0.45
    if neighbor.terrain in {"ice_field", "ice_plain"}:
        terrain_penalty += 0.25

    delay = 0.25 + roughness * 0.80 + slope_factor * 0.85 + gravity_penalty + low_g_penalty + terrain_penalty
    delay = round(max(0.0, min(MAX_MOVE_DELAY, delay)), 1)
    severity = "easy" if delay < 0.7 else "normal" if delay < 1.3 else "rough"

    return DirectionProfile(
        direction=direction,
        target_x=x + dx,
        target_y=y + dy,
        allowed=True,
        delay_seconds=delay,
        message=_movement_message(direction, current, neighbor, severity),
        severity=severity,
    )


def compose_surface_room(system_data: Dict[str, Any], body: Dict[str, Any], x: int, y: int) -> SurfaceRoomView:
    """Generate room text and directional profiles for a coordinate."""
    sample = sample_surface(system_data, body, x, y)
    directions = {
        direction: evaluate_direction(system_data, body, x, y, direction)
        for direction in DIRECTIONS
    }

    title = f"{sample.terrain_label} on {sample.body_name}"

    temp_c = sample.temperature_k - 273.15
    desc_parts = [
        f"The terrain here is {sample.terrain_label.lower()}, with an elevation near {sample.elevation_m:,} meters.",
        f"Local readings show {sample.gravity_g:.2f}g gravity, {sample.temperature_k:.0f} K ({temp_c:.0f} C), and radiation level {sample.radiation:.2f}.",
    ]

    if sample.terrain in {"highlands", "mountains"}:
        desc_parts.append("Ridges and broken slopes interrupt the horizon, making route choice important.")
    elif sample.terrain in {"crater_field"}:
        desc_parts.append("Overlapping impact scars and fractured shelves make the ground uneven underfoot.")
    elif sample.terrain in {"basalt_plain", "dust_plain", "open_plain"}:
        desc_parts.append("The surface stretches outward in broad, open bands, broken by occasional shallow rises.")
    elif sample.terrain in {"ice_plain", "ice_field"}:
        desc_parts.append("Pale frozen crust reflects the light in hard, glassy patches.")

    blocked = [profile for profile in directions.values() if not profile.allowed]
    for profile in blocked:
        desc_parts.append(profile.blocked_reason or "Nearby terrain blocks travel.")

    return SurfaceRoomView(
        sample=sample,
        title=title,
        description=" ".join(desc_parts),
        directions=directions,
    )
