"""Evennia room materialization helpers for generated planetary surfaces."""

from __future__ import annotations

from typing import Any, Dict, Optional

from evennia import create_object, search_tag

from .generator import SurfaceRoomView, compose_surface_room


SURFACE_TAG = "generated_surface_room"
SURFACE_TAG_CATEGORY = "surface"
SURFACE_ADDRESS_CATEGORY = "surface:address"
ROOM_TYPECLASS = "typeclasses.rooms.Room"


def surface_address_key(system_name: str, body_id: str, x: int, y: int) -> str:
    """Return a stable tag key for a generated surface coordinate."""
    return f"{system_name.lower()}::{body_id.lower()}::{int(x)}::{int(y)}"


def get_surface_address(room: Any) -> Dict[str, Any]:
    """Return surface address data from a room, or an empty dict."""
    if room is None:
        return {}
    try:
        data = room.attributes.get("surface_address")
        return dict(data or {})
    except Exception:
        return {}


def is_surface_room(room: Any) -> bool:
    """Return True if this room is a generated surface room."""
    return bool(get_surface_address(room))


def find_surface_room(system_name: str, body_id: str, x: int, y: int) -> Optional[Any]:
    """Find an already materialized generated surface room."""
    key = surface_address_key(system_name, body_id, x, y)
    matches = search_tag(key, category=SURFACE_ADDRESS_CATEGORY) or []
    return matches[0] if matches else None


def _write_room_data(room: Any, system_data: Dict[str, Any], body: Dict[str, Any], x: int, y: int, view: SurfaceRoomView) -> None:
    """Write generated surface metadata onto a materialized room."""
    sample = view.sample
    room.db.desc = view.description
    room.attributes.add(
        "surface_address",
        {
            "system_name": system_data.get("name"),
            "body_id": body.get("id"),
            "body_name": body.get("name"),
            "x": int(x),
            "y": int(y),
        },
    )
    room.attributes.add("surface_view", view.to_dict())
    room.attributes.add(
        "surface_persistence",
        {
            "status": "ephemeral",
            "reason": None,
        },
    )
    room.attributes.add("surface_sample", sample.to_dict())

    room.tags.add(SURFACE_TAG, category=SURFACE_TAG_CATEGORY)
    room.tags.add(
        surface_address_key(str(system_data.get("name")), str(body.get("id")), x, y),
        category=SURFACE_ADDRESS_CATEGORY,
    )


def get_or_create_surface_room(system_data: Dict[str, Any], body: Dict[str, Any], x: int, y: int) -> Any:
    """Return a materialized Evennia room for a generated surface coordinate."""
    system_name = str(system_data.get("name", "Unknown System"))
    body_id = str(body.get("id", "unknown-body"))
    existing = find_surface_room(system_name, body_id, x, y)
    view = compose_surface_room(system_data, body, x, y)

    if existing:
        _write_room_data(existing, system_data, body, x, y, view)
        return existing

    room = create_object(
        ROOM_TYPECLASS,
        key=view.title,
        nohome=True,
    )
    _write_room_data(room, system_data, body, x, y, view)
    return room


def anchor_surface_room(room: Any, reason: str) -> None:
    """Mark a generated surface room as anchored and ineligible for cleanup."""
    room.attributes.add(
        "surface_persistence",
        {
            "status": "anchored",
            "reason": reason,
        },
    )


def read_surface_view(room: Any) -> Dict[str, Any]:
    """Read stored generated room view data."""
    try:
        return dict(room.attributes.get("surface_view") or {})
    except Exception:
        return {}
