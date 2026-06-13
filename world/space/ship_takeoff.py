"""
Player-facing ship takeoff helpers.

This is the ship-side counterpart to admin/dev `surface takeoff`.
It is intended to be called from aboard the caller's current landed ship:

    ship takeoff

Behavior:
    - requires a current ship
    - requires that ship to be in landed mode
    - resolves the generated surface room, if possible
    - emits surface-room takeoff flavor
    - updates ship location_state from landed to orbiting
    - removes the landed_ship_anchor SurfaceOverlay
    - regenerates the surface room so `look` no longer shows the ship
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from world.space.models import find_body, find_system_object, read_system_data
from world.space.shipstate import (
    get_current_ship_for_caller,
    read_ship_location,
    write_ship_location,
)
from world.surface.models import get_or_create_surface_room
from world.surface.overlays import remove_landed_ship_overlay
from world.surface.room_events import announce_surface_event, describe_ship_takeoff
from world.space.ship_access import ACTION_TAKEOFF, require_ship_access


def _as_dict(value: Any) -> dict[str, Any]:
    """Return value as a plain dict if mapping-like, otherwise empty dict."""
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ship_display_name(ship: Any) -> str:
    """Best-effort ship display name."""
    try:
        name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")
    except Exception:
        name = getattr(ship, "key", "Unknown ship")
    return str(name).replace("Ship: ", "", 1)


def _resolve_landed_surface_room_from_state(state: dict[str, Any]):
    """
    Return the generated surface room for a landed ship state.

    Raises ValueError if state data is incomplete or the system/body cannot
    be resolved.
    """
    system_name = state.get("system")
    body_id = state.get("body_id")
    coords = _as_dict(state.get("coordinates"))

    if not system_name or not body_id:
        raise ValueError("ship location state is missing system/body data")

    if coords.get("x") is None or coords.get("y") is None:
        raise ValueError("ship location state is missing surface coordinates")

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        raise ValueError(f"No imported system named '{system_name}' was found.")

    system_data = read_system_data(system_obj)
    if not system_data:
        raise ValueError(f"System '{system_name}' has no stored system data.")

    body = find_body(system_data, str(body_id))
    if body is None:
        raise ValueError(f"No body id '{body_id}' was found in {system_name}.")

    return get_or_create_surface_room(system_data, body, int(coords["x"]), int(coords["y"]))


def takeoff_current_ship(caller) -> str:
    """
    Take off in the caller's current ship.

    Returns a user-facing message. On success, the ship remains the caller's
    current ship and the caller remains aboard whatever object/room they are in.
    """
    ship = get_current_ship_for_caller(caller)
    if ship is None:
        return "No current ship selected. Use 'ship board <ship>' first."
    
    allowed, error = require_ship_access(caller, ship, ACTION_TAKEOFF)
    if not allowed:
        return error

    ship_name = _ship_display_name(ship)
    state = read_ship_location(ship) or {}

    if state.get("mode") != "landed":
        return f"{ship_name} is not currently landed."

    surface_room = None
    try:
        surface_room = _resolve_landed_surface_room_from_state(state)
    except Exception:
        # Takeoff can still clear stale landed state during early development.
        # We simply skip the live surface-room event if the room cannot resolve.
        surface_room = None

    if surface_room is not None:
        try:
            announce_surface_event(surface_room, describe_ship_takeoff(ship_name))
        except Exception:
            pass

    old_coordinates = _as_dict(state.get("coordinates"))

    new_state = dict(state)
    new_state["mode"] = "orbiting"
    new_state["last_surface_coordinates"] = old_coordinates
    new_state["coordinates"] = None
    new_state["site_id"] = None
    new_state["dock_id"] = None
    new_state["notes"] = [
        f"Ship has taken off from surface coordinates "
        f"{old_coordinates.get('x')}, {old_coordinates.get('y')} "
        f"and is in orbit around {state.get('body_name') or state.get('body_id')}."
    ]

    write_ship_location(ship, new_state)

    try:
        remove_landed_ship_overlay(ship)
    except Exception:
        pass

    if surface_room is not None:
        try:
            if hasattr(surface_room, "regenerate_surface_room"):
                surface_room.regenerate_surface_room()
        except Exception:
            pass

    return f"{ship_name} takes off from the surface."
