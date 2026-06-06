"""Player-facing surface commands.

This module intentionally keeps CmdSurface available because
world.space.cmdsets imports it directly.

Overlay/admin commands now live in world.surface.overlay_commands.
"""

from __future__ import annotations

from evennia.commands.default.muxcommand import MuxCommand


class CmdSurface(MuxCommand):
    """
    Show basic information about the current generated surface tile.

    This is a compatibility-safe placeholder while the richer surface command
    is rebuilt. Do not place overlay debug commands in this module; keep them in
    world.surface.overlay_commands so imports remain stable.

    Usage:
      surface
      surf
    """

    key = "surface"
    aliases = ["surf"]
    locks = "cmd:all()"
    help_category = "Surface"

    def func(self):
        caller = self.caller
        room = caller.location
        if not room:
            caller.msg("You are nowhere.")
            return

        planet_key = getattr(room.db, "planet_key", None)
        x = getattr(room.db, "surface_x", None)
        y = getattr(room.db, "surface_y", None)

        if planet_key is None or x is None or y is None:
            caller.msg("This is not a generated surface tile.")
            return

        lines = [f"Surface tile: {planet_key} ({x}, {y})"]

        terrain = getattr(room.db, "terrain", None) or getattr(room.db, "terrain_type", None)
        elevation = getattr(room.db, "elevation_m", None) or getattr(room.db, "elevation", None)
        temperature = getattr(room.db, "temperature_k", None) or getattr(room.db, "temperature", None)
        gravity = getattr(room.db, "gravity", None)
        radiation = getattr(room.db, "radiation", None)

        if terrain is not None:
            lines.append(f"Terrain: {terrain}")
        if elevation is not None:
            lines.append(f"Elevation: {elevation}")
        if gravity is not None:
            lines.append(f"Gravity: {gravity}")
        if temperature is not None:
            lines.append(f"Temperature: {temperature}")
        if radiation is not None:
            lines.append(f"Radiation: {radiation}")

        caller.msg("\n".join(lines))
