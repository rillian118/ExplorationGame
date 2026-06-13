"""
Surface landed-ship interaction helpers.

This module treats landed_ship_anchor SurfaceOverlay records as the source of
truth for visible landed ships on generated surface tiles.

Initial v0.1 scope:
    surface ships
    surface board <ship name|overlay id>

Boarding is intentionally conservative. It looks for common explicit boarding
attributes first and falls back to moving the caller into the ship object only
if no dedicated boarding room is configured.
"""

from __future__ import annotations

from typing import Any, Iterable

from evennia.objects.models import ObjectDB # type: ignore

from world.surface.models import SurfaceOverlay, get_surface_address, is_surface_room
from world.surface.overlays import get_surface_overlays, remove_landed_ship_overlay
from world.surface.room_events import announce_surface_event, describe_ship_takeoff


LANDING_OVERLAY_TYPE = "landed_ship_anchor"


BOARDING_ROOM_ATTRS = (
    "boarding_room",
    "boarding_room_dbref",
    "entry_room",
    "entry_room_dbref",
    "ship_entry_room",
    "ship_entry_room_dbref",
    "bridge_room",
    "bridge_room_dbref",
    "ship_bridge",
    "ship_bridge_dbref",
    "interior_room",
    "interior_room_dbref",
)


def _obj_label(obj: Any) -> str:
    """Best-effort object label."""
    try:
        return str(obj.key)
    except Exception:
        return str(obj)


def _object_from_id(object_id: int | None):
    """Return an Evennia object by database id, or None."""
    if object_id is None:
        return None

    try:
        return ObjectDB.objects.get(id=int(object_id))
    except Exception:
        return None


def _object_from_dbref(dbref: str | None):
    """Return an Evennia object by dbref string, or None."""
    if not dbref:
        return None

    dbref = str(dbref).strip()
    if not dbref.startswith("#"):
        return None

    try:
        return ObjectDB.objects.get(id=int(dbref.lstrip("#")))
    except Exception:
        return None


def _ship_from_overlay(overlay: SurfaceOverlay):
    """Resolve the ship object represented by a landed_ship_anchor overlay."""
    ship = _object_from_id(getattr(overlay, "object_id", None))
    if ship is not None:
        return ship

    data = overlay.data or {}
    return _object_from_dbref(data.get("ship_dbref"))


def get_current_surface_overlay_key(caller) -> tuple[str, int, int] | None:
    """
    Return the canonical overlay key for caller's current generated surface tile.
    """
    room = caller.location
    if not room or not is_surface_room(room):
        return None

    try:
        address = dict(get_surface_address(room) or {})
    except Exception:
        address = {}

    system_name = address.get("system_name")
    body_id = address.get("body_id")
    x = address.get("x")
    y = address.get("y")

    if not system_name or not body_id or x is None or y is None:
        return None

    return f"{system_name}:{body_id}", int(x), int(y)


def get_landed_ship_overlays_at_caller(caller) -> list[SurfaceOverlay]:
    """Return visible landed ship anchor overlays at caller's current surface tile."""
    key = get_current_surface_overlay_key(caller)
    if key is None:
        return []

    planet_key, x, y = key
    return list(
        get_surface_overlays(
            planet_key,
            x,
            y,
            overlay_type=LANDING_OVERLAY_TYPE,
            visible_on_surface=True,
        )
    )


def _overlay_ship_name(overlay: SurfaceOverlay) -> str:
    data = overlay.data or {}
    return str(data.get("ship_name") or data.get("name") or f"overlay #{overlay.id}")

def _can_admin_takeoff(caller) -> bool:
    """
    v0.1 authorization gate for surface takeoff.

    Later, replace or extend this with ship ownership/crew permission checks.
    """
    try:
        return bool(caller.check_permstring("Admins"))
    except Exception:
        try:
            return bool(caller.permissions.check("Admins"))
        except Exception:
            return False


def takeoff_landed_ship(caller, query: str) -> str:
    """
    Admin/dev takeoff for a landed ship visible at caller's current surface tile.

    Returns a user-facing status message. On success, this removes the
    landed_ship_anchor overlay and updates the ship's location_state away from
    landed mode.
    """
    if get_current_surface_overlay_key(caller) is None:
        return "You are not standing on a generated surface tile."

    if not _can_admin_takeoff(caller):
        return "You do not have permission to force surface takeoff."

    if not query.strip():
        return "Usage: surface takeoff <ship name|overlay id>"

    overlay = find_landed_ship_overlay(caller, query)
    if overlay is None:
        return "No matching landed ship is visible here. Use 'surface ships' to list ships."

    ship = _ship_from_overlay(overlay)
    if ship is None:
        return f"Landed ship overlay #{overlay.id} no longer resolves to a ship object."

    room = caller.location
    ship_name = _overlay_ship_name(overlay)

    # Preserve useful state from the overlay before deleting it.
    data = overlay.data or {}
    system_name = data.get("system_name")
    body_id = data.get("body_id")
    body_name = data.get("body_name") or body_id

    # Announce before the overlay disappears so observers get immediate feedback.
    announce_surface_event(room, describe_ship_takeoff(ship_name), exclude=[caller])

    # Update ship state. This is intentionally conservative: we avoid inventing
    # orbital coordinates here. The important v0.1 transition is "not landed".
    try:
        from world.space.shipstate import write_ship_location, read_ship_location

        old_state = read_ship_location(ship) or {}
        state = dict(old_state)
        old_coordinates = dict(state.get("coordinates") or {})
        state["mode"] = "orbiting"
        state["system"] = system_name or state.get("system")
        state["body_id"] = body_id or state.get("body_id")
        state["body_name"] = body_name or state.get("body_name")
        state["last_surface_coordinates"] = old_coordinates
        state["coordinates"] = None
        state["site_id"] = None
        state["dock_id"] = None
        state["notes"] = [
            f"Ship has taken off from surface coordinates "
            f"{old_coordinates.get('x')}, {old_coordinates.get('y')} "
            f"and is in orbit around {state.get('body_name') or state.get('body_id')}."
        ]
        
        write_ship_location(ship, state)
    except Exception:
        # Do not leave a landed overlay behind if the command's purpose is to
        # force takeoff during early development.
        pass

    try:
        remove_landed_ship_overlay(ship)
    except Exception:
        # Fallback: delete the exact overlay resolved by the command.
        try:
            overlay.delete()
        except Exception:
            pass

    try:
        if room and hasattr(room, "regenerate_surface_room"):
            room.regenerate_surface_room()
    except Exception:
        pass

    return f"{ship_name} has taken off."



def render_surface_ships(caller) -> str:
    """Render visible landed ships at the caller's current surface tile."""
    key = get_current_surface_overlay_key(caller)
    if key is None:
        return "You are not standing on a generated surface tile."

    planet_key, x, y = key
    overlays = get_landed_ship_overlays_at_caller(caller)

    if not overlays:
        return f"No landed ships are visible at {planet_key} ({x}, {y})."

    lines = [f"Landed ships at {planet_key} ({x}, {y}):"]

    for overlay in overlays:
        data = overlay.data or {}
        ship_name = _overlay_ship_name(overlay)
        ship_dbref = data.get("ship_dbref") or "unknown dbref"
        lines.append(f"  #{overlay.id}: {ship_name} [{ship_dbref}]")

        desc = data.get("description")
        if desc:
            lines.append(f"      {desc}")

    lines.append("")
    lines.append("Use: surface board <ship name|overlay id>")
    return "\n".join(lines)


def find_landed_ship_overlay(caller, query: str) -> SurfaceOverlay | None:
    """
    Find a landed ship overlay at caller's tile by overlay id or ship name.
    """
    query = (query or "").strip()
    if not query:
        return None

    overlays = get_landed_ship_overlays_at_caller(caller)
    if not overlays:
        return None

    # Overlay id forms: 3, #3
    normalized = query.lstrip("#")
    if normalized.isdigit():
        oid = int(normalized)
        for overlay in overlays:
            if overlay.id == oid:
                return overlay

    qlow = query.lower()

    exact_matches = []
    partial_matches = []
    for overlay in overlays:
        name = _overlay_ship_name(overlay)
        nlow = name.lower()
        if nlow == qlow:
            exact_matches.append(overlay)
        elif qlow in nlow:
            partial_matches.append(overlay)

    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(partial_matches) == 1:
        return partial_matches[0]

    return None


def _candidate_room_from_attr(value: Any):
    """
    Resolve a possible boarding-room attribute value into an ObjectDB, or None.
    """
    if value is None:
        return None

    # Already an Evennia object.
    if hasattr(value, "move_to") and hasattr(value, "contents"):
        return value

    # Attribute handler can return dbrefs as strings.
    if isinstance(value, str):
        return _object_from_dbref(value)

    # Numeric database id.
    if isinstance(value, int):
        return _object_from_id(value)

    return None


def _get_ship_boarding_target(ship):
    """
    Return the room/object the caller should move into when boarding this ship.

    Preference order:
      1. Explicit boarding/interior/bridge room attributes.
      2. The ship object itself, if no interior room is configured.
    """
    for attr in BOARDING_ROOM_ATTRS:
        try:
            value = ship.attributes.get(attr)
        except Exception:
            value = None

        target = _candidate_room_from_attr(value)
        if target is not None:
            return target

    # Conservative fallback for v0.1. This works if ships are container-like
    # objects. Later, replace this with a canonical ship interior accessor.
    return ship


def board_landed_ship(caller, query: str) -> str:
    """
    Attempt to board a landed ship visible at caller's current surface tile.

    Returns a user-facing status message. On success, the caller has already
    been moved to the boarding target.
    """
    if get_current_surface_overlay_key(caller) is None:
        return "You are not standing on a generated surface tile."

    if not query.strip():
        return "Usage: surface board <ship name|overlay id>"

    overlay = find_landed_ship_overlay(caller, query)
    if overlay is None:
        return "No matching landed ship is visible here. Use 'surface ships' to list ships."

    ship = _ship_from_overlay(overlay)
    if ship is None:
        return f"Landed ship overlay #{overlay.id} no longer resolves to a ship object."

    target = _get_ship_boarding_target(ship)
    if target is None:
        return f"{_obj_label(ship)} does not have a boarding target configured."

    ship_name = _overlay_ship_name(overlay)

    try:
        caller.msg(f"You board {ship_name}.")
        caller.move_to(target, quiet=False)
    except Exception as err:
        return f"Boarding failed: {err}"

    return ""
