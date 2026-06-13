"""
Character-level player preferences.

The command surface is intentionally centralized under:

    player preferences

Current storage is character Attributes:

    player_preferences = {
        "survey_map": "brief",
    }

This keeps v0.1 migration-free. The service layer isolates storage so we can
move to account-level, per-session, or database-backed preferences later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PREFERENCE_ATTR = "player_preferences"


@dataclass(frozen=True)
class PlayerPreferenceSpec:
    """Preference definition."""

    key: str
    default: str
    valid_values: tuple[str, ...]
    description: str


PREFERENCE_SPECS: dict[str, PlayerPreferenceSpec] = {
    "survey_map": PlayerPreferenceSpec(
        key="survey_map",
        default="visual",
        valid_values=("visual", "brief", "list"),
        description=(
            "Default renderer for survey map when no explicit map mode is given. "
            "Use visual for compact ASCII, brief for semantic summaries, or list "
            "for directional tile readouts."
        ),
    ),
}


def normalize_preference_key(key: str) -> str:
    """Normalize a user-entered preference key."""
    return str(key or "").strip().lower().replace("-", "_")


def get_preference_spec(key: str) -> PlayerPreferenceSpec | None:
    """Return preference spec by key."""
    return PREFERENCE_SPECS.get(normalize_preference_key(key))


def _read_raw_preferences(caller: Any) -> dict[str, str]:
    """Read raw stored preferences from caller attrs."""
    try:
        prefs = caller.attributes.get(PREFERENCE_ATTR, default={})
    except Exception:
        try:
            prefs = getattr(caller.db, PREFERENCE_ATTR, {}) or {}
        except Exception:
            prefs = {}

    if not isinstance(prefs, dict):
        return {}

    return {normalize_preference_key(key): str(value).strip().lower() for key, value in prefs.items()}


def _write_raw_preferences(caller: Any, prefs: dict[str, str]) -> None:
    """Write raw preferences to caller attrs."""
    clean = {normalize_preference_key(key): str(value).strip().lower() for key, value in prefs.items()}

    try:
        caller.attributes.add(PREFERENCE_ATTR, clean)
    except Exception:
        setattr(caller.db, PREFERENCE_ATTR, clean)


def get_player_preference(caller: Any, key: str, default: str | None = None) -> str:
    """
    Return preference value for caller.

    If unset or invalid, returns the registered spec default. If no spec exists,
    returns supplied default or empty string.
    """
    norm_key = normalize_preference_key(key)
    spec = get_preference_spec(norm_key)
    fallback = default if default is not None else (spec.default if spec else "")

    prefs = _read_raw_preferences(caller)
    value = prefs.get(norm_key)

    if spec and value not in spec.valid_values:
        return spec.default

    return value or fallback


def set_player_preference(caller: Any, key: str, value: str) -> tuple[bool, str]:
    """
    Set a preference.

    Returns:
        (success, message)
    """
    norm_key = normalize_preference_key(key)
    spec = get_preference_spec(norm_key)
    if spec is None:
        return False, f"Unknown player preference '{key}'."

    norm_value = str(value or "").strip().lower()
    if norm_value not in spec.valid_values:
        valid = ", ".join(spec.valid_values)
        return False, f"Invalid value for {spec.key}: {value}. Valid values: {valid}."

    prefs = _read_raw_preferences(caller)
    prefs[spec.key] = norm_value
    _write_raw_preferences(caller, prefs)

    return True, f"Set player preference {spec.key} to {norm_value}."


def reset_player_preference(caller: Any, key: str) -> tuple[bool, str]:
    """
    Reset one preference to its default by removing the stored override.
    """
    norm_key = normalize_preference_key(key)
    spec = get_preference_spec(norm_key)
    if spec is None:
        return False, f"Unknown player preference '{key}'."

    prefs = _read_raw_preferences(caller)
    prefs.pop(spec.key, None)
    _write_raw_preferences(caller, prefs)

    return True, f"Reset player preference {spec.key} to default: {spec.default}."


def render_one_preference(caller: Any, key: str) -> str:
    """Render a single preference."""
    spec = get_preference_spec(key)
    if spec is None:
        return f"Unknown player preference '{key}'."

    value = get_player_preference(caller, spec.key)
    valid = ", ".join(spec.valid_values)

    return "\n".join(
        [
            f"Player preference: {spec.key}",
            f"  Current value: {value}",
            f"  Default value: {spec.default}",
            f"  Valid values: {valid}",
            f"  {spec.description}",
        ]
    )


def render_all_preferences(caller: Any) -> str:
    """Render all known preferences and current values."""
    lines = ["Player preferences"]

    for key in sorted(PREFERENCE_SPECS):
        spec = PREFERENCE_SPECS[key]
        value = get_player_preference(caller, key)
        valid = ", ".join(spec.valid_values)
        lines.append("")
        lines.append(f"{spec.key}: {value}")
        lines.append(f"  Valid values: {valid}")
        lines.append(f"  Default: {spec.default}")
        lines.append(f"  {spec.description}")

    lines.append("")
    lines.append("Usage:")
    lines.append("  player preferences <name>")
    lines.append("  player preferences <name> <value>")
    lines.append("  player preferences reset <name>")

    return "\n".join(lines)


def handle_player_preferences_command(caller: Any, args: str) -> str:
    """
    Handle `player preferences` subcommand body.
    """
    raw = (args or "").strip()

    if not raw:
        return render_all_preferences(caller)

    parts = raw.split(None, 2)

    if parts[0].lower() == "reset":
        if len(parts) < 2:
            return "Usage: player preferences reset <name>"

        _success, message = reset_player_preference(caller, parts[1])
        return message

    if len(parts) == 1:
        return render_one_preference(caller, parts[0])

    key = parts[0]
    value = parts[1]
    _success, message = set_player_preference(caller, key, value)
    return message
