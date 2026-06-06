"""
Merge these methods into your existing GeneratedSurfaceRoom class.

This assumes the room already stores:
    self.db.planet_key
    self.db.surface_x
    self.db.surface_y

If your current attribute names differ, adjust `_surface_coordinates()`.
"""

from world.surface.cleanup import get_surface_room_cleanup_report
from world.surface.overlays import compose_overlay_description, get_surface_overlays


def _surface_coordinates(self):
    planet_key = getattr(self.db, "planet_key", None)
    x = getattr(self.db, "surface_x", None)
    y = getattr(self.db, "surface_y", None)
    if planet_key is None or x is None or y is None:
        return None, None, None
    return planet_key, int(x), int(y)


def get_surface_overlay_description(self):
    planet_key, x, y = self._surface_coordinates()
    if planet_key is None:
        return ""
    overlays = get_surface_overlays(planet_key, x, y, visible_only=True)
    return compose_overlay_description(overlays)


def compose_surface_description(self, base_description=None):
    """
    Compose procedural terrain plus persistent overlays.

    `base_description` should be your current/generated terrain description. If
    omitted, we preserve existing self.db.desc as the base.
    """
    base = (base_description or self.db.desc or "").strip()
    overlay_desc = self.get_surface_overlay_description().strip()

    if base and overlay_desc:
        return f"{base}\n\n{overlay_desc}"
    return base or overlay_desc


def refresh_surface_overlays(self):
    """Re-append overlay prose to this room's current/base generated desc."""
    base = getattr(self.db, "surface_base_desc", None) or self.db.desc or ""
    self.db.desc = self.compose_surface_description(base_description=base)


def regenerate_surface_room(self):
    """
    Regenerate this room while preserving persistent overlays.

    Replace the placeholder base generation with your existing terrain generator.
    """
    # IMPORTANT: Replace this with the actual procedural tile description call.
    # Example:
    # terrain_data = generate_surface_tile(self.db.planet_key, self.db.surface_x, self.db.surface_y)
    # base_desc = render_surface_tile_description(terrain_data)
    base_desc = getattr(self.db, "surface_base_desc", None) or self.db.desc or ""

    self.db.surface_base_desc = base_desc.strip()
    self.db.desc = self.compose_surface_description(base_description=self.db.surface_base_desc)
    return self.db.desc


def is_cleanup_safe(self):
    safe, _reasons = get_surface_room_cleanup_report(self)
    return safe


def get_cleanup_report(self):
    return get_surface_room_cleanup_report(self)
