"""
Character-level player preferences.

Storage:

    caller.attributes["player_preferences"] = {
        "survey_map": "brief",
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PREFERENCE_ATTR = "player_preferences"


@dataclass(frozen=True)
class PlayerPreferenceSpec:
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


def _norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _norm_value(value: Any) -> str:
    return str(value or "").strip().lower()


def _get_spec(key: Any) -> PlayerPreferenceSpec | None:
    return PREFERENCE_SPECS.get(_norm_key(key))


def _read_prefs(caller: Any) -> dict[str, str]:
    raw = caller.attributes.get(PREFERENCE_ATTR, default={})

    if raw is None:
        return {}

    if not hasattr(raw, "items"):
        return {}

    clean: dict[str, str] = {}
    for key, value in raw.items():
        clean[_norm_key(key)] = _norm_value(value)

    return clean


def _write_prefs(caller: Any, prefs: dict[str, str]) -> None:
    clean: dict[str, str] = {}
    for key, value in prefs.items():
        clean[_norm_key(key)] = _norm_value(value)

    caller.attributes.add(PREFERENCE_ATTR, clean)


def get_player_preference(caller: Any, key: str, default: str | None = None) -> str:
    """
    Return one player preference.
    """
    norm_key = _norm_key(key)
    spec = _get_spec(norm_key)

    fallback = default
    if fallback is None:
        fallback = spec.default if spec else ""

    prefs = _read_prefs(caller)
    value = _norm_value(prefs.get(norm_key, ""))

    if not value:
        return fallback

    if spec is not None and value not in spec.valid_values:
        return spec.default

    return value


def set_player_preference(caller: Any, key: str, value: str) -> tuple[bool, str]:
    """
    Set one player preference.
    """
    spec = _get_spec(key)
    if spec is None:
        return False, f"Unknown player preference '{key}'."

    norm_value = _norm_value(value)
    if norm_value not in spec.valid_values:
        valid = ", ".join(spec.valid_values)
        return False, f"Invalid value for {spec.key}: {value}. Valid values: {valid}."

    prefs = _read_prefs(caller)
    prefs[spec.key] = norm_value
    _write_prefs(caller, prefs)

    saved = _read_prefs(caller).get(spec.key)
    if saved != norm_value:
        return False, f"Failed to save player preference {spec.key}. Expected {norm_value}, read back {saved!r}."

    return True, f"Set player preference {spec.key} to {norm_value}."


def reset_player_preference(caller: Any, key: str) -> tuple[bool, str]:
    """
    Reset one player preference.
    """
    spec = _get_spec(key)
    if spec is None:
        return False, f"Unknown player preference '{key}'."

    prefs = _read_prefs(caller)
    prefs.pop(spec.key, None)
    _write_prefs(caller, prefs)

    return True, f"Reset player preference {spec.key} to default: {spec.default}."


def render_one_preference(caller: Any, key: str) -> str:
    """
    Render one player preference.
    """
    spec = _get_spec(key)
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
    """
    Render all player preferences.
    """
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
    Handle `player preferences`.
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
