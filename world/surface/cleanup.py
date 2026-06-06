"""
Cleanup checks for generated surface rooms.

Generated surface rooms are cacheable, but only if they do not contain
persistent player/world state. This module centralizes the conservative safety
check so commands and future cleanup jobs use the same rules.
"""

from __future__ import annotations

from typing import Any

from world.surface.models import (
    SURFACE_TAG,
    SURFACE_TAG_CATEGORY,
    get_surface_address,
    is_surface_room,
)
from world.surface.overlays import get_surface_overlays, has_blocking_surface_overlays


def _display_name(obj: Any, looker: Any = None) -> str:
    """Best-effort object display name for reports."""
    try:
        return obj.get_display_name(looker or obj)
    except Exception:
        return getattr(obj, "key", str(obj))


def _is_ephemeral_surface_object(obj: Any) -> bool:
    """
    Return True if an object is explicitly safe to ignore during room cleanup.

    This is intentionally opt-in. Anything not tagged ephemeral is treated as
    meaningful player/world state.
    """
    try:
        return obj.tags.has("generated_surface_ephemeral", category="surface")
    except Exception:
        return False


def _surface_persistence_reason(room: Any) -> str | None:
    """
    Return a persistence/anchor reason if the room has one.

    Current surface rooms store this as:
        room.attributes["surface_persistence"] = {"status": ..., "reason": ...}
    """
    try:
        persistence = room.attributes.get("surface_persistence") or {}
    except Exception:
        persistence = {}

    if not isinstance(persistence, dict):
        return None

    status = persistence.get("status")
    reason = persistence.get("reason")

    if status and status != "ephemeral":
        return str(reason or status)

    return None


def get_surface_room_cleanup_report(room: Any) -> tuple[bool, list[str]]:
    """
    Return `(is_safe, reasons)` for deleting a generated surface room.

    This is intentionally conservative:
      - false negative: acceptable; room remains cached
      - false positive: unacceptable; player/world state could be destroyed
    """
    reasons: list[str] = []

    if room is None:
        return False, ["no room supplied"]

    # The room should be recognizable as a generated surface room.
    try:
        has_tag = room.tags.has(SURFACE_TAG, category=SURFACE_TAG_CATEGORY)
    except Exception:
        has_tag = False

    if not has_tag:
        reasons.append("not tagged as a generated surface room")

    if not is_surface_room(room):
        reasons.append("missing surface_address data")

    if reasons:
        return False, reasons

    address = get_surface_address(room)
    system_name = address.get("system_name")
    body_id = address.get("body_id")
    x = address.get("x")
    y = address.get("y")

    if not system_name or not body_id or x is None or y is None:
        return False, ["surface_address is incomplete"]

    planet_key = f"{system_name}:{body_id}"
    x = int(x)
    y = int(y)

    # Manual/admin hard-protection.
    try:
        if getattr(room.db, "surface_cleanup_protected", False):
            reasons.append("room has db.surface_cleanup_protected set")
    except Exception:
        pass

    persistence_reason = _surface_persistence_reason(room)
    if persistence_reason:
        reasons.append(f"room persistence status blocks cleanup: {persistence_reason}")

    # Meaningful contents block cleanup. Only explicitly tagged generated
    # ephemeral objects are ignored.
    meaningful_contents = []
    try:
        contents = list(room.contents)
    except Exception:
        contents = []

    for obj in contents:
        if _is_ephemeral_surface_object(obj):
            continue
        meaningful_contents.append(obj)

    if meaningful_contents:
        labels = ", ".join(_display_name(obj, room) for obj in meaningful_contents[:8])
        if len(meaningful_contents) > 8:
            labels += ", ..."
        reasons.append(f"meaningful contents present: {labels}")

    # Persistent overlays that block cleanup.
    try:
        blocking_overlays = list(
            get_surface_overlays(
                planet_key=planet_key,
                x=x,
                y=y,
                blocks_cleanup=True,
            )
        )
    except TypeError:
        # Compatibility fallback if get_surface_overlays does not support
        # keyword filtering yet.
        blocking_overlays = []
        try:
            for overlay in get_surface_overlays(planet_key, x, y):
                if getattr(overlay, "blocks_cleanup", False):
                    blocking_overlays.append(overlay)
        except Exception:
            if has_blocking_surface_overlays(planet_key, x, y):
                blocking_overlays = [None]
    except Exception:
        blocking_overlays = []

    if blocking_overlays:
        ids = []
        for overlay in blocking_overlays[:8]:
            if overlay is None:
                continue
            ids.append(f"#{overlay.id}:{overlay.overlay_type}")
        if ids:
            detail = ", ".join(ids)
            if len(blocking_overlays) > 8:
                detail += ", ..."
            reasons.append(f"blocking surface overlay exists: {detail}")
        else:
            reasons.append("blocking surface overlay exists at this coordinate")

    return not reasons, reasons


def is_surface_room_cleanup_safe(room: Any) -> bool:
    """Convenience boolean wrapper around get_surface_room_cleanup_report."""
    safe, _reasons = get_surface_room_cleanup_report(room)
    return safe