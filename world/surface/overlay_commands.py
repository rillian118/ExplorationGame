"""Admin/debug commands for persistent surface overlays.

Keep this module separate from world.surface.commands so the player-facing
CmdSurface import used by world.space.cmdsets remains stable.
"""

from __future__ import annotations

from typing import Any

from evennia import CmdSet
from evennia.commands.default.muxcommand import MuxCommand

from world.surface.cleanup import get_surface_room_cleanup_report
from world.surface.models import SurfaceOverlay


def _get_surface_context(caller):
    """Return (room, planet_key, x, y), with None coordinate values if invalid."""
    room = caller.location
    if not room:
        return None, None, None, None

    try:
        from world.surface.models import get_surface_address

        address = get_surface_address(room) or {}
        address = dict(address)
    except Exception:
        return room, None, None, None

    system_name = address.get("system_name")
    body_id = address.get("body_id")
    x = address.get("x")
    y = address.get("y")

    if not system_name or not body_id or x is None or y is None:
        return room, None, None, None

    planet_key = f"{system_name}:{body_id}"
    return room, planet_key, int(x), int(y)


def _obj_id(obj: Any) -> int | None:
    """Best-effort Evennia object id extraction."""
    return getattr(obj, "id", None) or getattr(obj, "dbid", None)


def _overlay_name(overlay: SurfaceOverlay) -> str:
    """Read overlay name from a real field if present, otherwise from data."""
    value = getattr(overlay, "name", None)
    if value:
        return str(value)
    data = overlay.data or {}
    return str(data.get("name", ""))


def _overlay_description(overlay: SurfaceOverlay) -> str:
    """Read overlay description from a real field if present, otherwise from data."""
    value = getattr(overlay, "description", None)
    if value:
        return str(value)
    data = overlay.data or {}
    return str(data.get("description", ""))


def _create_overlay(*, planet_key: str, x: int, y: int, overlay_type: str, name: str, description: str, caller) -> SurfaceOverlay:
    """Create an overlay using the raw-id v0.1 model shape.

    This intentionally stores display text in JSON data so it works with the
    current SurfaceOverlay model that uses object_id/owner_id rather than
    ForeignKey fields or dedicated name/description columns.
    """
    return SurfaceOverlay.objects.create(
        planet_key=planet_key,
        x=x,
        y=y,
        overlay_type=overlay_type,
        object_id=_obj_id(caller),
        owner_id=_obj_id(caller),
        data={
            "name": name,
            "description": description,
            "created_by_cmd": True,
            "created_by": getattr(caller, "key", str(caller)),
            "created_by_dbref": getattr(caller, "dbref", None),
        },
        is_permanent=True,
        blocks_cleanup=True,
        visible_on_surface=True,
    )


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

        overlays = list(
            SurfaceOverlay.objects.filter(planet_key=planet_key, x=x, y=y).order_by(
                "overlay_type", "id"
            )
        )
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
            name = _overlay_name(overlay)
            desc = _overlay_description(overlay)
            name_text = f" {name}" if name else ""
            lines.append(f"  #{overlay.id}: {overlay.overlay_type}{name_text}{flag_text}")
            if desc:
                lines.append(f"      {desc}")

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

        overlay = _create_overlay(
            planet_key=planet_key,
            x=x,
            y=y,
            overlay_type="player_poi",
            name=self.lhs.strip(),
            description=self.rhs.strip(),
            caller=self.caller,
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
        raw = self.args.strip()
        if not raw.isdigit():
            self.caller.msg("Usage: @removesurfaceoverlay <id>")
            return

        overlay_id = int(raw)
        deleted, _details = SurfaceOverlay.objects.filter(id=overlay_id).delete()
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
    """Builder/debug cmdset for surface overlay development."""

    key = "SurfaceOverlayCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurfaceOverlays())
        self.add(CmdAddSurfacePOI())
        self.add(CmdRemoveSurfaceOverlay())
        self.add(CmdRegenSurface())
        self.add(CmdSurfaceCleanupCheck())
