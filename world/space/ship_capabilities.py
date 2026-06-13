"""Prototype ship capability helpers.

Capabilities are intentionally simple ship attributes for now. Future sensor
components, damage, power, crew skill, and environmental modifiers can feed
into this same read API without changing survey command code.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SHIP_CAPABILITIES_ATTR = "ship_capabilities"

CAP_SURVEY_MAX_RADIUS = "survey_max_radius"
CAP_SURVEY_MAX_RESOLUTION = "survey_max_resolution"
CAP_SENSOR_QUALITY = "sensor_quality"


CAPABILITY_DEFINITIONS = {
    CAP_SURVEY_MAX_RADIUS: {
        "label": "Survey max radius",
        "default": 3,
        "minimum": 0,
        "maximum": 3,
        "aliases": {"radius", "survey_radius", "max_radius"},
    },
    CAP_SURVEY_MAX_RESOLUTION: {
        "label": "Survey max resolution",
        "default": 3,
        "minimum": 1,
        "maximum": 3,
        "aliases": {"resolution", "res", "survey_resolution", "max_resolution"},
    },
    CAP_SENSOR_QUALITY: {
        "label": "Sensor quality",
        "default": 100,
        "minimum": 1,
        "maximum": 100,
        "aliases": {"quality", "sensor", "sensors"},
    },
}


def _alias_map() -> dict[str, str]:
    aliases = {}
    for key, definition in CAPABILITY_DEFINITIONS.items():
        aliases[key] = key
        for alias in definition.get("aliases", set()):
            aliases[str(alias)] = key
    return aliases


CAPABILITY_ALIASES = _alias_map()


def default_ship_capabilities() -> dict[str, int]:
    """Return default prototype capabilities for a ship."""
    return {
        key: int(definition["default"])
        for key, definition in CAPABILITY_DEFINITIONS.items()
    }


def capability_names() -> str:
    """Return a compact list of supported capability keys."""
    return ", ".join(CAPABILITY_DEFINITIONS.keys())


def normalize_capability_name(name: str) -> str | None:
    """Return canonical capability key, accepting friendly aliases."""
    return CAPABILITY_ALIASES.get(str(name or "").strip().lower())


def _clamp_capability(key: str, value: Any) -> int:
    definition = CAPABILITY_DEFINITIONS[key]
    minimum = int(definition["minimum"])
    maximum = int(definition["maximum"])
    return max(minimum, min(maximum, int(value)))


def read_ship_capabilities(ship: Any) -> dict[str, int]:
    """Read normalized ship capabilities, filling missing values with defaults."""
    capabilities = default_ship_capabilities()

    try:
        raw = ship.attributes.get(SHIP_CAPABILITIES_ATTR)
    except Exception:
        raw = None

    if isinstance(raw, Mapping):
        for raw_key, raw_value in raw.items():
            key = normalize_capability_name(str(raw_key))
            if key is None:
                continue
            try:
                capabilities[key] = _clamp_capability(key, raw_value)
            except Exception:
                continue

    return capabilities


def ensure_ship_capabilities(ship: Any) -> dict[str, int]:
    """Ensure a ship has a normalized capability attribute."""
    capabilities = read_ship_capabilities(ship)
    ship.attributes.add(SHIP_CAPABILITIES_ATTR, capabilities)
    return capabilities


def set_ship_capability(ship: Any, name: str, value: Any) -> tuple[str, int, dict[str, int]]:
    """Set one ship capability and return the canonical key, value, and full state."""
    key = normalize_capability_name(name)
    if key is None:
        raise ValueError(f"Unknown ship capability '{name}'. Valid capabilities: {capability_names()}.")

    definition = CAPABILITY_DEFINITIONS[key]
    try:
        parsed = int(value)
    except Exception as err:
        raise ValueError(f"{definition['label']} must be a number.") from err

    minimum = int(definition["minimum"])
    maximum = int(definition["maximum"])
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{definition['label']} must be between {minimum} and {maximum}.")

    capabilities = read_ship_capabilities(ship)
    capabilities[key] = parsed
    ship.attributes.add(SHIP_CAPABILITIES_ATTR, capabilities)
    return key, parsed, capabilities


def render_ship_capabilities(ship: Any) -> str:
    """Render player-facing ship capability summary."""
    capabilities = read_ship_capabilities(ship)

    try:
        name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")
    except Exception:
        name = getattr(ship, "key", "Unknown ship")

    lines = [
        f"Ship capabilities: {name}",
        f"Object: {getattr(ship, 'dbref', 'unknown')}",
    ]

    for key, definition in CAPABILITY_DEFINITIONS.items():
        label = definition["label"]
        value = capabilities[key]
        minimum = definition["minimum"]
        maximum = definition["maximum"]
        lines.append(f"  {label}: {value} (allowed {minimum}-{maximum})")

    lines.append("")
    lines.append("Survey scans are limited by these capabilities.")
    return "\n".join(lines)
