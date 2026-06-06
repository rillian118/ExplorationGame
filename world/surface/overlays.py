"""
Helpers for persistent surface overlays.
"""

from __future__ import annotations

from typing import Iterable

from world.surface.models import SurfaceOverlay


def get_surface_overlays(
    planet_key: str,
    x: int,
    y: int,
    *,
    overlay_type: str | None = None,
    visible_on_surface: bool | None = None,
    blocks_cleanup: bool | None = None,
) -> Iterable[SurfaceOverlay]:
    """
    Return overlays for a surface coordinate.

    Optional filters are keyword-only to avoid ambiguity.
    """
    qs = SurfaceOverlay.objects.filter(
        planet_key=str(planet_key),
        x=int(x),
        y=int(y),
    )

    if overlay_type is not None:
        qs = qs.filter(overlay_type=overlay_type)

    if visible_on_surface is not None:
        qs = qs.filter(visible_on_surface=visible_on_surface)

    if blocks_cleanup is not None:
        qs = qs.filter(blocks_cleanup=blocks_cleanup)

    return qs.order_by("created_at", "id")


def has_blocking_surface_overlays(planet_key: str, x: int, y: int) -> bool:
    """
    Return True if any overlay at this coordinate blocks room cleanup.
    """
    return SurfaceOverlay.objects.filter(
        planet_key=str(planet_key),
        x=int(x),
        y=int(y),
        blocks_cleanup=True,
    ).exists()


def create_surface_overlay(
    *,
    planet_key: str,
    x: int,
    y: int,
    overlay_type: str,
    data: dict | None = None,
    object_id: int | None = None,
    owner_id: int | None = None,
    is_permanent: bool = True,
    blocks_cleanup: bool = True,
    visible_on_surface: bool = True,
) -> SurfaceOverlay:
    """
    Create a persistent surface overlay.
    """
    return SurfaceOverlay.objects.create(
        planet_key=str(planet_key),
        x=int(x),
        y=int(y),
        overlay_type=str(overlay_type),
        object_id=object_id,
        owner_id=owner_id,
        data=data or {},
        is_permanent=is_permanent,
        blocks_cleanup=blocks_cleanup,
        visible_on_surface=visible_on_surface,
    )

def surface_overlay_key_from_address(address: dict) -> tuple[str, int, int]:
    """
    Convert a generated surface room address into the canonical overlay key.
    """
    system_name = address.get("system_name")
    body_id = address.get("body_id")
    x = address.get("x")
    y = address.get("y")

    if not system_name or not body_id or x is None or y is None:
        raise ValueError("Incomplete surface address.")

    return f"{system_name}:{body_id}", int(x), int(y)


def create_or_update_landed_ship_overlay(ship, *, system_name: str, body_id: str, body_name: str, x: int, y: int):
    """
    Create or update the cleanup-blocking overlay representing a landed ship.
    """
    ship_id = getattr(ship, "id", None)
    ship_dbref = getattr(ship, "dbref", None)
    ship_name = None

    try:
        ship_name = ship.attributes.get("ship_name")
    except Exception:
        pass

    ship_name = str(ship_name or getattr(ship, "key", "Unknown ship")).replace("Ship: ", "", 1)

    planet_key = f"{system_name}:{body_id}"

    overlay, _created = SurfaceOverlay.objects.update_or_create(
        planet_key=planet_key,
        x=int(x),
        y=int(y),
        overlay_type="landed_ship_anchor",
        object_id=ship_id,
        defaults={
            "data": {
                "ship_name": ship_name,
                "ship_dbref": str(ship_dbref or ""),
                "system_name": str(system_name),
                "body_id": str(body_id),
                "body_name": str(body_name or body_id),
                "description": f"A ship, {ship_name}, rests nearby on its landing struts.",
            },
            "is_permanent": True,
            "blocks_cleanup": True,
            "visible_on_surface": True,
        },
    )

    return overlay


def remove_landed_ship_overlay(ship) -> int:
    """
    Remove any landed-ship anchor overlays for this ship.

    Returns number of overlays deleted.
    """
    ship_id = getattr(ship, "id", None)
    ship_dbref = str(getattr(ship, "dbref", "") or "")

    qs = SurfaceOverlay.objects.filter(overlay_type="landed_ship_anchor")

    if ship_id is not None:
        deleted, _details = qs.filter(object_id=ship_id).delete()
        return int(deleted)

    if ship_dbref:
        deleted, _details = qs.filter(data__ship_dbref=ship_dbref).delete()
        return int(deleted)

    return 0


def sync_landed_ship_overlay(ship):
    """
    Synchronize a ship's current location_state into a landed ship overlay.

    If the ship is not landed, any existing landed anchor overlay is removed.
    """
    from world.space.shipstate import read_ship_location

    state = read_ship_location(ship)

    if state.get("mode") != "landed":
        remove_landed_ship_overlay(ship)
        return None

    coords = state.get("coordinates") or {}
    system_name = state.get("system")
    body_id = state.get("body_id")
    body_name = state.get("body_name") or body_id
    x = coords.get("x")
    y = coords.get("y")

    if not system_name or not body_id or x is None or y is None:
        raise ValueError("Ship is landed, but its location_state is incomplete.")

    return create_or_update_landed_ship_overlay(
        ship,
        system_name=str(system_name),
        body_id=str(body_id),
        body_name=str(body_name),
        x=int(x),
        y=int(y),
    )