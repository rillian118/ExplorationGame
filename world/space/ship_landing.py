"""
Ship landing helpers for the prototype surface/ship loop.

Initial v0.1 scope:
  ship land <x> <y>
  ship land <system>/<body> <x> <y>

The current ship is resolved through world.space.shipstate.get_current_ship_for_caller.
If the ship is orbiting a body, `ship land <x> <y>` uses that orbital body.
Explicit system/body syntax can be used by builders/admins or for test flows.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from world.space.models import find_body, find_system_object, read_system_data
from world.space.shipstate import (
    format_ship_status,
    get_current_ship_for_caller,
    read_ship_location,
    set_ship_landed,
)
from world.surface.models import get_or_create_surface_room
from world.space.ship_access import ACTION_LAND, require_ship_access


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ship_display_name(ship: Any) -> str:
    try:
        return str(ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship"))
    except Exception:
        return str(getattr(ship, "key", "Unknown ship"))


def _split_explicit_target(text: str) -> tuple[str, str, int | None, int | None, str]:
    """
    Parse `<system>/<body> <x> <y>` while allowing spaces in body names.
    """
    text = (text or "").strip()
    try:
        target_text, x_text, y_text = text.rsplit(None, 2)
    except ValueError:
        return "", "", None, None, "Usage: ship land <x> <y> or ship land <system>/<body> <x> <y>"

    try:
        x = int(x_text)
        y = int(y_text)
    except ValueError:
        return "", "", None, None, "Landing coordinates must be integers."

    if "/" in target_text:
        system_name, _sep, body_query = target_text.partition("/")
    else:
        parts = target_text.split(None, 1)
        if len(parts) < 2:
            return "", "", None, None, "Explicit landing target must be <system>/<body> or '<system> <body>'."
        system_name, body_query = parts[0], parts[1]

    system_name = system_name.strip()
    body_query = body_query.strip()
    if not system_name or not body_query:
        return "", "", None, None, "Usage: ship land <system>/<body> <x> <y>"

    return system_name, body_query, x, y, ""


def _parse_land_args(ship: Any, args: str) -> tuple[str, str, int | None, int | None, str]:
    """
    Return system_name, body_query, x, y, error.

    Accepted forms:
      ship land <x> <y>
      ship land <system>/<body> <x> <y>
    """
    args = (args or "").strip()
    if not args:
        return "", "", None, None, "Usage: ship land <x> <y> or ship land <system>/<body> <x> <y>"

    parts = args.split()
    if len(parts) == 2:
        try:
            x = int(parts[0])
            y = int(parts[1])
        except ValueError:
            return "", "", None, None, "Landing coordinates must be integers."

        state = read_ship_location(ship)
        system_name = state.get("system")
        body_query = state.get("body_id") or state.get("body_name")
        if not system_name or not body_query:
            return "", "", None, None, "Current ship is not associated with an orbital body. Use: ship land <system>/<body> <x> <y>"

        mode = state.get("mode")
        if mode not in {"orbiting", "landed"}:
            return "", "", None, None, f"Current ship is {mode or 'unknown'}, not orbiting a landable body. Use explicit target if this is a test."

        return str(system_name), str(body_query), x, y, ""

    return _split_explicit_target(args)


def _materialize_landed_room(ship: Any):
    """
    Return the generated surface room for a newly-landed ship.

    This intentionally materializes the room so future disembark/board flows have
    a concrete room and so any live surface occupants can receive landing flavor
    from overlay/event hooks.
    """
    state = read_ship_location(ship)
    if state.get("mode") != "landed":
        return None

    system_name = state.get("system")
    body_id = state.get("body_id")
    coords = _as_dict(state.get("coordinates"))
    if not system_name or not body_id or not coords:
        return None

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        return None

    system_data = read_system_data(system_obj)
    if not system_data:
        return None

    body = find_body(system_data, str(body_id))
    if body is None:
        return None

    return get_or_create_surface_room(system_data, body, int(coords.get("x")), int(coords.get("y")))


def land_current_ship(caller: Any, args: str) -> str:
    """
    Land the caller's current ship and return a user-facing status message.

    State/overlay synchronization is handled by set_ship_landed and the existing
    surface overlay hooks. This helper materializes the target room after landing.
    """
    ship = get_current_ship_for_caller(caller)
    if ship is None:
        return "No current ship selected. Use 'ship board <ship>' or board a landed ship first."

    system_name, body_query, x, y, error = _parse_land_args(ship, args)
    if error:
        return error
    
    allowed, error = require_ship_access(caller, ship, ACTION_LAND)
    if not allowed:
        return error

    try:
        state = set_ship_landed(ship, system_name, body_query, int(x), int(y))
    except Exception as err:
        return f"Could not land {_ship_display_name(ship)}: {err}"

    # Materialize the target surface room for immediate disembark and for live
    # surface event delivery. Failure here should not roll back the ship state.
    room_note = ""
    try:
        room = _materialize_landed_room(ship)
        if room is None:
            room_note = " The landing room was not materialized."
    except Exception as err:
        room_note = f" The ship landed, but the surface room could not be materialized: {err}"

    body_name = state.get("body_name") or state.get("body_id") or body_query
    coords = _as_dict(state.get("coordinates"))
    return (
        f"{_ship_display_name(ship)} lands on {body_name} "
        f"at surface coordinates {coords.get('x')}, {coords.get('y')}."
        f"{room_note}"
    )
