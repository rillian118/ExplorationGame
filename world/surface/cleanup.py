"""Cleanup checks for generated surface rooms."""

from __future__ import annotations

from world.surface.overlays import has_blocking_surface_overlays


def get_surface_room_cleanup_report(room) -> tuple[bool, list[str]]:
    """
    Return `(is_safe, reasons)` for deleting a generated surface room.

    This is intentionally conservative. A false negative is acceptable; a false
    positive could destroy player state.
    """
    reasons = []

    if not room.tags.has("generated_surface_room", category="surface"):
        reasons.append("not tagged as a generated surface room")
        return False, reasons

    planet_key = getattr(room.db, "planet_key", None)
    x = getattr(room.db, "surface_x", None)
    y = getattr(room.db, "surface_y", None)

    if planet_key is None or x is None or y is None:
        reasons.append("missing planet_key/surface_x/surface_y attributes")
        return False, reasons

    if getattr(room.db, "surface_cleanup_protected", False):
        reasons.append("room has db.surface_cleanup_protected set")

    meaningful_contents = []
    for obj in room.contents:
        if obj.tags.has("generated_surface_ephemeral", category="surface"):
            continue
        meaningful_contents.append(obj)

    if meaningful_contents:
        labels = ", ".join(obj.get_display_name(room) for obj in meaningful_contents[:8])
        if len(meaningful_contents) > 8:
            labels += ", ..."
        reasons.append(f"meaningful contents present: {labels}")

    if has_blocking_surface_overlays(planet_key, int(x), int(y)):
        reasons.append("blocking surface overlay exists at this coordinate")

    return not reasons, reasons
