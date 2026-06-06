"""Evennia room materialization helpers for generated planetary surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Optional

from evennia import create_object, search_tag # type: ignore

from .generator import SurfaceRoomView, compose_surface_room

from typeclasses.rooms import Room as BaseRoom

from django.db import models

SURFACE_TAG = "generated_surface_room"
SURFACE_TAG_CATEGORY = "surface"
SURFACE_ADDRESS_CATEGORY = "surface:address"
ROOM_TYPECLASS = "world.surface.models.GeneratedSurfaceRoom"
SURFACE_ROOM_CMDSET = "world.surface.cmdsets.SurfaceRoomCmdSet"

class SurfaceOverlay(models.Model):
    """
    Persistent state layered onto generated planetary surface rooms.

    Generated rooms may be deleted and recreated. SurfaceOverlay records should
    survive that process and be reapplied whenever the surface tile is loaded or
    regenerated.
    """

    planet_key = models.CharField(max_length=128, db_index=True)
    x = models.IntegerField(db_index=True)
    y = models.IntegerField(db_index=True)

    overlay_type = models.CharField(max_length=64, db_index=True)

    # Optional links into Evennia's object database.
    source_object = models.ForeignKey(
        ObjectDB,
        null=True,
        blank=True,
        related_name="surface_overlays_as_source",
        on_delete=models.SET_NULL,
        help_text="Object that physically/logically creates this overlay, such as a landed ship.",
    )
    owner_object = models.ForeignKey(
        ObjectDB,
        null=True,
        blank=True,
        related_name="surface_overlays_as_owner",
        on_delete=models.SET_NULL,
        help_text="Player, account-controlled character, organization object, or owner proxy.",
    )

    name = models.CharField(max_length=160, blank=True, default="")
    description = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)

    is_permanent = models.BooleanField(default=True)
    blocks_cleanup = models.BooleanField(default=True)
    visible_on_surface = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["planet_key", "x", "y"]),
            models.Index(fields=["planet_key", "overlay_type"]),
            models.Index(fields=["object_id"]),
            models.Index(fields=["owner_id"]),
        ]

        ordering = ["planet_key", "x", "y", "overlay_type", "id"]

    def __str__(self):
        label = self.name or self.overlay_type
        return f"{label} @ {self.planet_key} ({self.x}, {self.y})"

    def display_line(self):
        """
        Surface-room prose for this overlay.
        Keep this conservative; richer rendering can move into overlays.py later.
        """
        if self.description:
            return self.description.strip()
        if self.name:
            return self.name.strip()
        return ""

class GeneratedSurfaceRoom(BaseRoom):
    """
    Typeclass for materialized procedural surface rooms.

    This makes normal Evennia room display use the generated surface formatter,
    so movement, look, and disembarkation all show the same surface view.
    """

    def return_appearance(self, looker, **kwargs):
        view = read_surface_view(self)
        if view:
            from .formatter import format_surface_view
            return format_surface_view(view)

        return super().return_appearance(looker, **kwargs)

def surface_address_key(system_name: str, body_id: str, x: int, y: int) -> str:
    """Return a stable tag key for a generated surface coordinate."""
    return f"{system_name.lower()}::{body_id.lower()}::{int(x)}::{int(y)}"


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def get_surface_address(room: Any) -> Dict[str, Any]:
    """Return surface address data from a room, or an empty dict."""
    if room is None:
        return {}

    try:
        return _as_dict(room.attributes.get("surface_address"))
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


def _ensure_surface_room_cmdset(room: Any) -> None:
    """
    Attach room-local direct movement commands to a generated surface room.

    Avoid stacking duplicate SurfaceRoomCmdSet instances.
    """
    try:
        for cmdset in room.cmdset.get():
            if getattr(cmdset, "key", None) == "SurfaceRoomCmdSet":
                return
    except Exception:
        pass

    try:
        room.cmdset.add(SURFACE_ROOM_CMDSET, persistent=True)
    except TypeError:
        room.cmdset.add(SURFACE_ROOM_CMDSET, permanent=True)
    except Exception:
        pass



def _write_room_data(
    room: Any,
    system_data: Dict[str, Any],
    body: Dict[str, Any],
    x: int,
    y: int,
    view: SurfaceRoomView,
) -> None:
    """Write generated surface metadata onto a materialized room."""
    sample = view.sample
    room.db.desc = view.description
    room.key = view.title

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
    _ensure_surface_room_cmdset(room)


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
    """Read stored generated room view data and add dynamic surface overlays."""
    try:
        view = _as_dict(room.attributes.get("surface_view"))
    except Exception:
        return {}

    try:
        dbrefs = room.attributes.get("landed_ship_dbrefs") or []
    except Exception:
        dbrefs = []

    ship_names = []

    if dbrefs:
        try:
            from world.space.shipstate import find_ship
        except Exception:
            find_ship = None

        if find_ship:
            for dbref in dbrefs:
                ship = find_ship(str(dbref))
                if ship is not None:
                    try:
                        ship_names.append(
                            str(ship.attributes.get("ship_name") or ship.key)
                        )
                    except Exception:
                        ship_names.append(str(ship))

    view["landed_ship_names"] = ship_names
    return view
