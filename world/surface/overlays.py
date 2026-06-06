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