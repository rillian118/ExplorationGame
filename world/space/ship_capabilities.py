"""Prototype ship sensor package and capability helpers.

Survey code should keep reading capabilities through `read_ship_capabilities`.
Sensor packages, manual overrides, damage, power, crew skill, and environmental
modifiers can all feed this API without changing survey command code.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SHIP_CAPABILITIES_ATTR = "ship_capabilities"
SHIP_CAPABILITY_OVERRIDES_ATTR = "ship_capability_overrides"
SHIP_SENSOR_PACKAGE_ATTR = "ship_sensor_package"

CAP_SURVEY_MAX_RADIUS = "survey_max_radius"
CAP_SURVEY_MAX_RESOLUTION = "survey_max_resolution"
CAP_SENSOR_QUALITY = "sensor_quality"

DEFAULT_SENSOR_PACKAGE = "survey"


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


SENSOR_PACKAGE_DEFINITIONS = {
    "civilian": {
        "label": "Civilian scanner",
        "summary": "Short-range navigation and landing survey sensors.",
        "aliases": {"basic", "starter", "civilian_scanner"},
        "capabilities": {
            CAP_SURVEY_MAX_RADIUS: 1,
            CAP_SURVEY_MAX_RESOLUTION: 1,
            CAP_SENSOR_QUALITY: 60,
        },
    },
    "frontier": {
        "label": "Frontier survey array",
        "summary": "General exploration sensors for routine orbital survey work.",
        "aliases": {"standard", "explorer", "frontier_array"},
        "capabilities": {
            CAP_SURVEY_MAX_RADIUS: 2,
            CAP_SURVEY_MAX_RESOLUTION: 2,
            CAP_SENSOR_QUALITY: 80,
        },
    },
    "survey": {
        "label": "Dedicated survey suite",
        "summary": "Prototype high-grade survey sensors matching the current maximum caps.",
        "aliases": {"advanced", "dedicated", "survey_suite"},
        "capabilities": {
            CAP_SURVEY_MAX_RADIUS: 3,
            CAP_SURVEY_MAX_RESOLUTION: 3,
            CAP_SENSOR_QUALITY: 100,
        },
    },
}


def _alias_map() -> dict[str, str]:
    aliases = {}
    for key, definition in CAPABILITY_DEFINITIONS.items():
        aliases[key] = key
        for alias in definition.get("aliases", set()):
            aliases[str(alias)] = key
    return aliases


def _sensor_package_alias_map() -> dict[str, str]:
    aliases = {}
    for key, definition in SENSOR_PACKAGE_DEFINITIONS.items():
        aliases[key] = key
        for alias in definition.get("aliases", set()):
            aliases[str(alias)] = key
    return aliases


CAPABILITY_ALIASES = _alias_map()
SENSOR_PACKAGE_ALIASES = _sensor_package_alias_map()


def default_ship_capabilities() -> dict[str, int]:
    """Return default prototype capabilities for a ship."""
    return {
        key: int(definition["default"])
        for key, definition in CAPABILITY_DEFINITIONS.items()
    }


def capability_names() -> str:
    """Return a compact list of supported capability keys."""
    return ", ".join(CAPABILITY_DEFINITIONS.keys())


def sensor_package_names() -> str:
    """Return a compact list of supported sensor package keys."""
    return ", ".join(SENSOR_PACKAGE_DEFINITIONS.keys())


def normalize_capability_name(name: str) -> str | None:
    """Return canonical capability key, accepting friendly aliases."""
    return CAPABILITY_ALIASES.get(str(name or "").strip().lower())


def normalize_sensor_package_name(name: str) -> str | None:
    """Return canonical sensor package key, accepting friendly aliases."""
    return SENSOR_PACKAGE_ALIASES.get(str(name or "").strip().lower())


def _clamp_capability(key: str, value: Any) -> int:
    definition = CAPABILITY_DEFINITIONS[key]
    minimum = int(definition["minimum"])
    maximum = int(definition["maximum"])
    return max(minimum, min(maximum, int(value)))


def _read_attr(obj: Any, attr_name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(attr_name)

    try:
        return obj.attributes.get(attr_name)
    except Exception:
        return None


def _has_attr(obj: Any, attr_name: str) -> bool:
    if isinstance(obj, Mapping):
        return attr_name in obj

    try:
        return bool(obj.attributes.has(attr_name))
    except Exception:
        try:
            return obj.attributes.get(attr_name) is not None
        except Exception:
            return False


def _write_attr(obj: Any, attr_name: str, value: Any) -> None:
    if isinstance(obj, Mapping):
        raise ValueError("Cannot write ship attributes to a raw mapping.")

    obj.attributes.add(attr_name, value)


def _normalize_capability_mapping(raw: Any) -> dict[str, int]:
    capabilities: dict[str, int] = {}
    if not isinstance(raw, Mapping):
        return capabilities

    for raw_key, raw_value in raw.items():
        key = normalize_capability_name(str(raw_key))
        if key is None:
            continue
        try:
            capabilities[key] = _clamp_capability(key, raw_value)
        except Exception:
            continue

    return capabilities


def capabilities_for_sensor_package(package_key: str) -> dict[str, int]:
    """Return clamped capability values supplied by a sensor package."""
    package_key = normalize_sensor_package_name(package_key) or DEFAULT_SENSOR_PACKAGE
    package = SENSOR_PACKAGE_DEFINITIONS[package_key]
    capabilities = default_ship_capabilities()
    capabilities.update(_normalize_capability_mapping(package.get("capabilities") or {}))
    return capabilities


def read_ship_sensor_package(ship: Any) -> str:
    """Read the installed ship sensor package key, falling back to the default."""
    raw = _read_attr(ship, SHIP_SENSOR_PACKAGE_ATTR)
    return normalize_sensor_package_name(str(raw or "")) or DEFAULT_SENSOR_PACKAGE


def ensure_ship_sensor_package(ship: Any) -> str:
    """Ensure a ship has an installed sensor package attribute."""
    package_key = read_ship_sensor_package(ship)
    _write_attr(ship, SHIP_SENSOR_PACKAGE_ATTR, package_key)
    return package_key


def install_ship_sensor_package(ship: Any, package_name: str) -> tuple[str, dict[str, int]]:
    """Install a sensor package and return its key and package capabilities."""
    package_key = normalize_sensor_package_name(package_name)
    if package_key is None:
        raise ValueError(f"Unknown sensor package '{package_name}'. Valid packages: {sensor_package_names()}.")

    _write_attr(ship, SHIP_SENSOR_PACKAGE_ATTR, package_key)
    capabilities = read_ship_capabilities(ship)
    _write_attr(ship, SHIP_CAPABILITIES_ATTR, capabilities)
    return package_key, capabilities


def _legacy_capability_overrides(ship: Any) -> dict[str, int]:
    """
    Return non-default values from the legacy ship_capabilities attribute.

    Older ships were created with a full default `ship_capabilities` mapping.
    Treating that as an override would prevent sensor packages from changing
    effective capabilities, so only values that differ from the historical
    defaults are carried forward.
    """
    raw = _normalize_capability_mapping(_read_attr(ship, SHIP_CAPABILITIES_ATTR))
    defaults = default_ship_capabilities()
    return {key: value for key, value in raw.items() if value != defaults.get(key)}


def read_ship_capability_overrides(ship: Any) -> dict[str, int]:
    """Read explicit manual capability overrides for a ship."""
    explicit = _normalize_capability_mapping(_read_attr(ship, SHIP_CAPABILITY_OVERRIDES_ATTR))
    if explicit or _has_attr(ship, SHIP_CAPABILITY_OVERRIDES_ATTR):
        return explicit

    if _has_attr(ship, SHIP_SENSOR_PACKAGE_ATTR):
        return {}

    return _legacy_capability_overrides(ship)


def read_ship_capabilities(ship: Any) -> dict[str, int]:
    """Read effective ship capabilities from package values plus overrides."""
    package_key = read_ship_sensor_package(ship)
    capabilities = capabilities_for_sensor_package(package_key)

    for key, value in read_ship_capability_overrides(ship).items():
        capabilities[key] = _clamp_capability(key, value)

    return capabilities


def ensure_ship_capabilities(ship: Any) -> dict[str, int]:
    """Ensure a ship has normalized sensor package and capability attributes."""
    ensure_ship_sensor_package(ship)
    capabilities = read_ship_capabilities(ship)
    _write_attr(ship, SHIP_CAPABILITIES_ATTR, capabilities)
    return capabilities


def set_ship_capability(ship: Any, name: str, value: Any) -> tuple[str, int, dict[str, int]]:
    """Set one manual ship capability override."""
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

    overrides = read_ship_capability_overrides(ship)
    overrides[key] = parsed
    _write_attr(ship, SHIP_CAPABILITY_OVERRIDES_ATTR, overrides)

    capabilities = read_ship_capabilities(ship)
    _write_attr(ship, SHIP_CAPABILITIES_ATTR, capabilities)
    return key, parsed, capabilities


def clear_ship_capability_override(ship: Any, name: str | None = None) -> dict[str, int]:
    """Clear one manual capability override, or all overrides if name is empty."""
    overrides = read_ship_capability_overrides(ship)

    if name:
        key = normalize_capability_name(name)
        if key is None:
            raise ValueError(f"Unknown ship capability '{name}'. Valid capabilities: {capability_names()}.")
        overrides.pop(key, None)
    else:
        overrides = {}

    _write_attr(ship, SHIP_CAPABILITY_OVERRIDES_ATTR, overrides)
    capabilities = read_ship_capabilities(ship)
    _write_attr(ship, SHIP_CAPABILITIES_ATTR, capabilities)
    return capabilities


def render_sensor_package_catalog() -> str:
    """Render available sensor packages for builders."""
    lines = ["Ship sensor packages"]
    for key, package in SENSOR_PACKAGE_DEFINITIONS.items():
        lines.append("")
        lines.append(f"{key}: {package['label']}")
        lines.append(f"  {package['summary']}")
        package_caps = capabilities_for_sensor_package(key)
        for cap_key, definition in CAPABILITY_DEFINITIONS.items():
            lines.append(f"  {definition['label']}: {package_caps[cap_key]}")
    return "\n".join(lines)


def render_ship_capabilities(ship: Any) -> str:
    """Render player-facing ship capability summary."""
    capabilities = read_ship_capabilities(ship)
    package_key = read_ship_sensor_package(ship)
    package = SENSOR_PACKAGE_DEFINITIONS[package_key]
    package_capabilities = capabilities_for_sensor_package(package_key)
    overrides = read_ship_capability_overrides(ship)

    try:
        name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")
    except Exception:
        name = getattr(ship, "key", "Unknown ship")

    lines = [
        f"Ship capabilities: {name}",
        f"Object: {getattr(ship, 'dbref', 'unknown')}",
        f"Sensor package: {package['label']} ({package_key})",
    ]

    for key, definition in CAPABILITY_DEFINITIONS.items():
        label = definition["label"]
        value = capabilities[key]
        package_value = package_capabilities[key]
        minimum = definition["minimum"]
        maximum = definition["maximum"]

        if key in overrides:
            source = f"manual override; package {package_value}"
        else:
            source = "package"

        lines.append(f"  {label}: {value} ({source}; allowed {minimum}-{maximum})")

    lines.append("")
    if overrides:
        lines.append(f"Manual overrides: {', '.join(sorted(overrides.keys()))}")
    else:
        lines.append("Manual overrides: none")

    lines.append("Survey scans are limited by these effective capabilities.")
    return "\n".join(lines)
