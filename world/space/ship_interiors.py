"""
Canonical ship interior helpers.

This module provides the first real ship-interior foundation for prototype
ships. Ships remain persistent Evennia objects, but boarding now targets a
dedicated interior room instead of falling back to moving the player into the
ship object itself.

Current v0.1 interior model:
    - one canonical Airlock room per ship
    - the Airlock is stored on ship.attributes["airlock_room"]
    - compatibility aliases are also stored:
        boarding_room
        entry_room
        ship_entry_room
    - interior rooms store ship identity attributes:
        ship_dbref
        ship_id
        ship_name
        ship_room_role
"""

from __future__ import annotations

from typing import Any

from evennia.objects.models import ObjectDB  # type: ignore
from evennia.utils.create import create_object # type: ignore


SHIP_INTERIOR_TAG = "ship_interior"
SHIP_INTERIOR_TAG_CATEGORY = "space"
SHIP_AIRLOCK_TAG = "ship_airlock"

BOARDING_ATTR_ALIASES = (
    "airlock_room",
    "boarding_room",
    "entry_room",
    "ship_entry_room",
)


def _ship_name(ship: Any) -> str:
    """Best-effort plain ship name."""
    try:
        name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")
    except Exception:
        name = getattr(ship, "key", "Unknown ship")

    return str(name).replace("Ship: ", "", 1)


def _ship_dbref(ship: Any) -> str:
    """Return a ship dbref string, if available."""
    return str(getattr(ship, "dbref", "") or "")


def _object_from_dbref(dbref: str | None):
    """Resolve #dbref to an Evennia object, or None."""
    if not dbref:
        return None

    dbref = str(dbref).strip()
    if not dbref.startswith("#"):
        return None

    try:
        return ObjectDB.objects.get(id=int(dbref.lstrip("#")))
    except Exception:
        return None


def _object_from_id(object_id: int | str | None):
    """Resolve database id to an Evennia object, or None."""
    if object_id is None:
        return None

    try:
        return ObjectDB.objects.get(id=int(object_id))
    except Exception:
        return None


def _candidate_room_from_attr(value: Any):
    """
    Resolve a possible ship-room attribute value into an object, or None.
    """
    if value is None:
        return None

    if hasattr(value, "move_to") and hasattr(value, "contents"):
        return value

    if isinstance(value, str):
        return _object_from_dbref(value)

    if isinstance(value, int):
        return _object_from_id(value)

    return None


def get_existing_ship_airlock(ship: Any):
    """
    Return an existing configured airlock/boarding room, if any.
    """
    for attr in BOARDING_ATTR_ALIASES:
        try:
            value = ship.attributes.get(attr)
        except Exception:
            value = None

        room = _candidate_room_from_attr(value)
        if room is not None:
            return room

    return None


def create_ship_airlock(ship: Any):
    """
    Create and configure a canonical Airlock room for a ship.
    """
    ship_name = _ship_name(ship)
    ship_dbref = _ship_dbref(ship)

    room = create_object(
        "typeclasses.rooms.Room",
        key=f"{ship_name} - Airlock",
        nohome=True,
    )

    room.db.desc = (
        f"You are in the airlock of {ship_name}. "
        "A pressure door leads deeper into the ship, while the outer hatch "
        "can be used for surface embarkation and disembarkation."
    )

    room.tags.add(SHIP_INTERIOR_TAG, category=SHIP_INTERIOR_TAG_CATEGORY)
    room.tags.add(SHIP_AIRLOCK_TAG, category=SHIP_INTERIOR_TAG_CATEGORY)

    room.attributes.add("ship_dbref", ship_dbref)
    room.attributes.add("ship_id", getattr(ship, "id", None))
    room.attributes.add("ship_name", ship_name)
    room.attributes.add("ship_room_role", "airlock")

    for attr in BOARDING_ATTR_ALIASES:
        ship.attributes.add(attr, room.dbref)

    return room


def get_or_create_ship_airlock(ship: Any):
    """
    Return the ship's canonical airlock, creating it if necessary.
    """
    if ship is None:
        return None

    existing = get_existing_ship_airlock(ship)
    if existing is not None:
        return existing

    return create_ship_airlock(ship)


def get_ship_boarding_target(ship: Any, *, create: bool = True):
    """
    Return the canonical boarding target for a ship.

    Unlike the previous v0.1 fallback, this never returns the ship object itself.
    If create=True, an Airlock room is created lazily when missing.
    """
    if ship is None:
        return None

    existing = get_existing_ship_airlock(ship)
    if existing is not None:
        return existing

    if create:
        return create_ship_airlock(ship)

    return None


def ensure_ship_interiors(ship: Any):
    """
    Ensure the ship has its minimum interior structure.

    Current minimum is just the Airlock.
    """
    return {
        "airlock": get_or_create_ship_airlock(ship),
    }


def render_ship_interior_summary(ship: Any, *, create: bool = True) -> str:
    """
    Render a compact builder/debug summary of a ship's interior rooms.
    """
    if ship is None:
        return "No ship supplied."

    ship_name = _ship_name(ship)
    rooms = ensure_ship_interiors(ship) if create else {"airlock": get_existing_ship_airlock(ship)}

    lines = [f"Ship interior for {ship_name}:"]

    airlock = rooms.get("airlock")
    if airlock is not None:
        lines.append(f"  Airlock: {airlock.key} {airlock.dbref}")
    else:
        lines.append("  Airlock: not configured")

    lines.append("")
    lines.append("Stored boarding attributes:")
    for attr in BOARDING_ATTR_ALIASES:
        try:
            value = ship.attributes.get(attr)
        except Exception:
            value = None
        lines.append(f"  {attr}: {value or '—'}")

    return "\n".join(lines)
