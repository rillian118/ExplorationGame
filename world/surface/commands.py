"""Admin/debug commands for surface overlays."""

from __future__ import annotations

from evennia import CmdSet
from evennia.commands.default.muxcommand import MuxCommand

from world.surface.cleanup import get_surface_room_cleanup_report
from world.surface.overlays import (
    create_player_poi,
    delete_surface_overlay,
    get_surface_overlays,
)


def _get_surface_context(caller):
    room = caller.location
    if not room:
        return None, None, None, None
    planet_key = getattr(room.db, "planet_key", None)
    x = getattr(room.db, "surface_x", None)
    y = getattr(room.db, "surface_y", None)
    if planet_key is None or x is None or y is None:
        return room, None, None, None
    return room, planet_key, int(x), int(y)


class CmdSurfaceOverlays(MuxCommand):
    """
    List overlays at the current surface coordinate.

    Usage:
      @surfaceoverlays
    """

    key = "@surfaceoverlays"
    locks = "cmd:perm(Builder)"
    help_category = "Surface"

    def func(self):
        room, planet_key, x, y = _get_surface_context(self.caller)
        if not room:
            self.caller.msg("You are nowhere.")
            return
        if planet_key is None:
            self.caller.msg("This room does not have surface coordinates.")
            return

        overlays = list(get_surface_overlays(planet_key, x, y, visible_only=False))
        if not overlays:
            self.caller.msg(f"No overlays at {planet_key} ({x}, {y}).")
            return

        lines = [f"Surface overlays at {planet_key} ({x}, {y}):"]
        for overlay in overlays:
            flags = []
            if overlay.blocks_cleanup:
                flags.append("blocks_cleanup")
            if overlay.visible_on_surface:
                flags.append("visible")
            if overlay.is_permanent:
                flags.append("permanent")
            flag_text = f" [{' | '.join(flags)}]" if flags else ""
            name = f" {overlay.name}" if overlay.name else ""
            lines.append(f"  #{overlay.id}: {overlay.overlay_type}{name}{flag_text}")
            if overlay.description:
                lines.append(f"      {overlay.description}")
        self.caller.msg("\n".join(lines))


class CmdAddSurfacePOI(MuxCommand):
    """
    Add a test player POI overlay to the current surface coordinate.

    Usage:
      @addsurfacepoi <name> = <description>
    """

    key = "@addsurfacepoi"
    locks = "cmd:perm(Builder)"
    help_category = "Surface"

    def func(self):
        room, planet_key, x, y = _get_surface_context(self.caller)
        if planet_key is None:
            self.caller.msg("This room does not have surface coordinates.")
            return
        if not self.lhs or not self.rhs:
            self.caller.msg("Usage: @addsurfacepoi <name> = <description>")
            return

        overlay = create_player_poi(
            planet_key=planet_key,
            x=x,
            y=y,
            name=self.lhs.strip(),
            description=self.rhs.strip(),
            owner_object=self.caller,
            data={"created_by_cmd": self.key},
        )

        if hasattr(room, "refresh_surface_overlays"):
            room.refresh_surface_overlays()

        self.caller.msg(f"Created surface POI overlay #{overlay.id} at {planet_key} ({x}, {y}).")


class CmdRemoveSurfaceOverlay(MuxCommand):
    """
    Remove a surface overlay by id.

    Usage:
      @removesurfaceoverlay <id>
    """

    key = "@removesurfaceoverlay"
    aliases = ["@delsurfaceoverlay"]
    locks = "cmd:perm(Builder)"
    help_category = "Surface"

    def func(self):
        if not self.args.strip().isdigit():
            self.caller.msg("Usage: @removesurfaceoverlay <id>")
            return
        overlay_id = int(self.args.strip())
        deleted = delete_surface_overlay(overlay_id)
        if not deleted:
            self.caller.msg(f"No surface overlay found with id #{overlay_id}.")
            return

        room = self.caller.location
        if room and hasattr(room, "refresh_surface_overlays"):
            room.refresh_surface_overlays()

        self.caller.msg(f"Deleted surface overlay #{overlay_id}.")


class CmdRegenSurface(MuxCommand):
    """
    Regenerate the current surface room while preserving overlays.

    Usage:
      @regensurface
    """

    key = "@regensurface"
    locks = "cmd:perm(Builder)"
    help_category = "Surface"

    def func(self):
        room = self.caller.location
        if not room:
            self.caller.msg("You are nowhere.")
            return
        if not hasattr(room, "regenerate_surface_room"):
            self.caller.msg("This room does not implement regenerate_surface_room().")
            return
        room.regenerate_surface_room()
        self.caller.msg("Regenerated current surface room while preserving overlays.")


class CmdSurfaceCleanupCheck(MuxCommand):
    """
    Report whether the current surface room is cleanup-safe.

    Usage:
      @surfacecleanupcheck
    """

    key = "@surfacecleanupcheck"
    locks = "cmd:perm(Builder)"
    help_category = "Surface"

    def func(self):
        room = self.caller.location
        if not room:
            self.caller.msg("You are nowhere.")
            return

        safe, reasons = get_surface_room_cleanup_report(room)
        if safe:
            self.caller.msg("This generated surface room is cleanup-safe.")
            return

        lines = ["This generated surface room is NOT cleanup-safe:"]
        lines.extend(f"  - {reason}" for reason in reasons)
        self.caller.msg("\n".join(lines))


class SurfaceOverlayCmdSet(CmdSet):
    """Temporary/debug cmdset for surface overlay development."""

    key = "SurfaceOverlayCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurfaceOverlays())
        self.add(CmdAddSurfacePOI())
        self.add(CmdRemoveSurfaceOverlay())
        self.add(CmdRegenSurface())
        self.add(CmdSurfaceCleanupCheck())

class CmdSurface(MuxCommand):
    """
    Temporary compatibility command for the SpaceCmdSet.

    This preserves the expected CmdSurface import while surface overlay
    commands are being integrated.
    """

    key = "surface"
    aliases = ["surf"]
    locks = "cmd:all()"
    help_category = "Surface"

    def func(self):
        self.caller.msg(
            "Surface command is currently under reconstruction. "
            "Use @surfaceoverlays, @addsurfacepoi, @regensurface, or @surfacecleanupcheck for overlay testing."
        )