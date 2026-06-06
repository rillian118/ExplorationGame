"""
Helpers for persistent surface overlays.

These functions are deliberately thin wrappers around the Django model so room
code and commands do not need to know query details.
"""

from __future__ import annotations

from typing import Iterable, Optional

from evennia.objects.models import ObjectDB

from world.surface.models import SurfaceOverlay


DEFAULT_POI_TYPE = "player_poi"
LANDING_ANCHOR_TYPE = "landed_ship_anchor"
PLAYER_IMPACT_TYPE = "player_impact"


def get_surface_overlays(
    planet_key: str,
    x: int,
    y: int,
    *,
    visible_only: bool = True,
    overlay_type: Optional[str] = None,
):
    """Return overlays for a specific surface coordinate."""
    qs = SurfaceOverlay.objects.filter(planet_key=planet_key, x=x, y=y)
    if visible_only:
        qs = qs.filter(visible_on_surface=True)
    if overlay_type:
        qs = qs.filter(overlay_type=overlay_type)
    return qs.order_by("overlay_type", "id")


def has_blocking_surface_overlays(planet_key: str, x: int, y: int) -> bool:
    """True if any overlay at this tile should prevent room cleanup."""
    return SurfaceOverlay.objects.filter(
        planet_key=planet_key,
        x=x,
        y=y,
        blocks_cleanup=True,
    ).exists()


def create_surface_overlay(
    *,
    planet_key: str,
    x: int,
    y: int,
    overlay_type: str,
    name: str = "",
    description: str = "",
    source_object: Optional[ObjectDB] = None,
    owner_object: Optional[ObjectDB] = None,
    data: Optional[dict] = None,
    is_permanent: bool = True,
    blocks_cleanup: bool = True,
    visible_on_surface: bool = True,
) -> SurfaceOverlay:
    """Create a generic persistent overlay."""
    return SurfaceOverlay.objects.create(
        planet_key=planet_key,
        x=x,
        y=y,
        overlay_type=overlay_type,
        name=name or "",
        description=description or "",
        source_object=source_object,
        owner_object=owner_object,
        data=data or {},
        is_permanent=is_permanent,
        blocks_cleanup=blocks_cleanup,
        visible_on_surface=visible_on_surface,
    )


def create_player_poi(
    *,
    planet_key: str,
    x: int,
    y: int,
    name: str,
    description: str,
    owner_object: Optional[ObjectDB] = None,
    data: Optional[dict] = None,
) -> SurfaceOverlay:
    """Create a simple player-visible point of interest."""
    return create_surface_overlay(
        planet_key=planet_key,
        x=x,
        y=y,
        overlay_type=DEFAULT_POI_TYPE,
        name=name,
        description=description,
        owner_object=owner_object,
        data=data,
        is_permanent=True,
        blocks_cleanup=True,
        visible_on_surface=True,
    )


def create_or_update_landed_ship_anchor(
    *,
    ship: ObjectDB,
    planet_key: str,
    x: int,
    y: int,
    owner_object: Optional[ObjectDB] = None,
    description: Optional[str] = None,
) -> SurfaceOverlay:
    """
    Create/update the persistent overlay showing that a ship is landed here.

    This does not move the ship object. Movement should be handled by your ship
    or landing system, then this helper should be called to persist the surface
    state.
    """
    name = getattr(ship, "key", "Landed ship") or "Landed ship"
    desc = description or f"{name} rests here on extended landing struts."

    overlay, _created = SurfaceOverlay.objects.update_or_create(
        source_object=ship,
        overlay_type=LANDING_ANCHOR_TYPE,
        defaults={
            "planet_key": planet_key,
            "x": x,
            "y": y,
            "owner_object": owner_object,
            "name": name,
            "description": desc,
            "data": {"ship_dbref": ship.dbref, "landing_status": "landed"},
            "is_permanent": True,
            "blocks_cleanup": True,
            "visible_on_surface": True,
        },
    )
    return overlay


def remove_landed_ship_anchor(ship: ObjectDB) -> int:
    """Remove any landed ship overlay associated with this ship."""
    deleted, _details = SurfaceOverlay.objects.filter(
        source_object=ship,
        overlay_type=LANDING_ANCHOR_TYPE,
    ).delete()
    return deleted


def delete_surface_overlay(overlay_id: int) -> bool:
    """Delete one overlay by database id. Returns True if deleted."""
    deleted, _details = SurfaceOverlay.objects.filter(id=overlay_id).delete()
    return bool(deleted)


def compose_overlay_description(overlays: Iterable[SurfaceOverlay]) -> str:
    """Render visible overlays into prose appended to a generated room desc."""
    lines = []
    for overlay in overlays:
        line = overlay.display_line()
        if line:
            lines.append(line)
    return "\n".join(lines)
