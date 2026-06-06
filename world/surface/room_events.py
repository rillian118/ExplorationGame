"""
Transient event messaging for generated surface rooms.

These helpers intentionally do not persist anything. They are for live flavor
messages when world state changes, such as ships landing or taking off.
"""

from __future__ import annotations

from typing import Iterable, Any


def announce_surface_event(room: Any, message: str, exclude: Iterable[Any] | None = None) -> None:
    """
    Send a transient message to occupants of a generated surface room.

    Args:
        room: Evennia room/object whose contents should receive the message.
        message: Text to send.
        exclude: Optional iterable of objects to skip.
    """
    if not room or not message:
        return

    excluded = set(exclude or [])

    try:
        contents = list(room.contents)
    except Exception:
        contents = []

    for obj in contents:
        if obj in excluded:
            continue
        try:
            obj.msg(message)
        except Exception:
            pass


def describe_ship_landing(ship_name: str) -> str:
    """Return standard surface flavor for a ship landing."""
    return f"{ship_name} descends through the haze and settles onto its landing struts."


def describe_ship_takeoff(ship_name: str) -> str:
    """Return standard surface flavor for a ship taking off."""
    return f"{ship_name} lifts from the surface, throwing dust outward before climbing into the sky."
