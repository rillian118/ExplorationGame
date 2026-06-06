"""
Admin commands for safely cleaning up generated surface rooms.

These commands are intentionally conservative. They call the same safety report
used by @surfacecleanupcheck, so a room is only deleted when the centralized
cleanup policy says it is safe.
"""

from __future__ import annotations

from evennia import search_tag
from evennia.commands.default.muxcommand import MuxCommand

from world.surface.cleanup import get_surface_room_cleanup_report
from world.surface.models import SURFACE_TAG, SURFACE_TAG_CATEGORY, get_surface_address


class CmdSurfaceCleanupSweep(MuxCommand):
    """
    Inspect or delete cleanup-safe generated surface rooms.

    Usage:
      @surfacecleanupsweep
      @surfacecleanupsweep/execute
      @surfacecleanupsweep/limit <count>
      @surfacecleanupsweep/execute/limit <count>

    Without /execute, this is a dry run. With /execute, only rooms that pass
    get_surface_room_cleanup_report() are deleted.
    """

    key = "@surfacecleanupsweep"
    aliases = ["@surfacesweep"]
    locks = "cmd:perm(Admin)"
    help_category = "Building"

    def _format_room(self, room):
        """Return a compact room label with address if available."""
        try:
            address = get_surface_address(room) or {}
        except Exception:
            address = {}

        system_name = address.get("system_name")
        body_id = address.get("body_id")
        body_name = address.get("body_name") or body_id
        x = address.get("x")
        y = address.get("y")

        if system_name and body_id and x is not None and y is not None:
            return f"{room.key} #{room.id} [{system_name}/{body_name} ({x}, {y})]"

        return f"{room.key} #{room.id} [no valid surface_address]"

    def func(self):
        caller = self.caller
        execute = "execute" in self.switches

        limit = None
        if "limit" in self.switches:
            raw = self.args.strip()
            if not raw:
                caller.msg("Usage: @surfacecleanupsweep/limit <count>")
                return
            try:
                limit = max(0, int(raw))
            except ValueError:
                caller.msg("Limit must be a whole number.")
                return

        rooms = list(search_tag(SURFACE_TAG, category=SURFACE_TAG_CATEGORY) or [])

        safe_rooms = []
        blocked = []

        for room in rooms:
            safe, reasons = get_surface_room_cleanup_report(room)
            if safe:
                safe_rooms.append(room)
            else:
                blocked.append((room, reasons))

        selected_safe_rooms = safe_rooms[:limit] if limit is not None else safe_rooms

        lines = []
        lines.append("Surface cleanup sweep")
        lines.append(f"  generated surface rooms found: {len(rooms)}")
        lines.append(f"  cleanup-safe rooms found: {len(safe_rooms)}")
        lines.append(f"  blocked rooms found: {len(blocked)}")

        if limit is not None:
            lines.append(f"  limit: {limit}")
            lines.append(f"  cleanup-safe rooms selected: {len(selected_safe_rooms)}")

        if not execute:
            lines.append("")
            lines.append("Dry run only. Use @surfacecleanupsweep/execute to delete selected safe rooms.")

            if selected_safe_rooms:
                lines.append("")
                lines.append("Cleanup-safe rooms:")
                for room in selected_safe_rooms[:12]:
                    lines.append(f"  - {self._format_room(room)}")
                if len(selected_safe_rooms) > 12:
                    lines.append(f"  ... and {len(selected_safe_rooms) - 12} more")

            if blocked:
                lines.append("")
                lines.append("Sample blocked rooms:")
                for room, reasons in blocked[:8]:
                    reason = "; ".join(reasons[:3])
                    if len(reasons) > 3:
                        reason += "; ..."
                    lines.append(f"  - {self._format_room(room)}: {reason}")
                if len(blocked) > 8:
                    lines.append(f"  ... and {len(blocked) - 8} more blocked rooms")

            caller.msg("\n".join(lines))
            return

        deleted = 0
        failed = []

        for room in selected_safe_rooms:
            label = self._format_room(room)

            # Re-check immediately before deletion in case something changed
            # between initial scan and delete loop.
            safe, reasons = get_surface_room_cleanup_report(room)
            if not safe:
                failed.append((label, "became unsafe before deletion: " + "; ".join(reasons)))
                continue

            try:
                room.delete()
                deleted += 1
            except Exception as err:
                failed.append((label, str(err)))

        lines.append("")
        lines.append(f"Deleted cleanup-safe generated surface rooms: {deleted}")

        if failed:
            lines.append("")
            lines.append("Failures/skipped rooms:")
            for label, reason in failed[:12]:
                lines.append(f"  - {label}: {reason}")
            if len(failed) > 12:
                lines.append(f"  ... and {len(failed) - 12} more")

        caller.msg("\n".join(lines))


class CmdSurfaceCleanupHere(MuxCommand):
    """
    Delete the current generated surface room if it is cleanup-safe.

    Usage:
      @surfacecleanuphere
      @surfacecleanuphere/execute

    Without /execute, this reports what would happen. With /execute, this tries
    to delete the current room only if it is cleanup-safe.
    """

    key = "@surfacecleanuphere"
    aliases = ["@surfacecleanhere"]
    locks = "cmd:perm(Admin)"
    help_category = "Building"

    def func(self):
        caller = self.caller
        room = caller.location
        execute = "execute" in self.switches

        if not room:
            caller.msg("You are nowhere.")
            return

        safe, reasons = get_surface_room_cleanup_report(room)

        if not safe:
            caller.msg(
                "This room is NOT cleanup-safe:\n"
                + "\n".join(f"  - {reason}" for reason in reasons)
            )
            return

        if not execute:
            caller.msg(
                "This room is cleanup-safe, but this was a dry run. "
                "Use @surfacecleanuphere/execute to delete it."
            )
            return

        # This normally will not be reachable while the caller is standing in
        # the room, because meaningful contents should include the caller.
        # Kept for completeness and for remote/testing scenarios.
        try:
            room.delete()
        except Exception as err:
            caller.msg(f"Cleanup failed: {err}")
            return

        caller.msg("Deleted current cleanup-safe surface room.")


class SurfaceCleanupCmdSet:
    """
    Mixin-style holder for the cleanup commands.

    Add the individual command classes to an existing cmdset, or create a real
    CmdSet wrapper in your project's default_cmdsets.py.
    """

    commands = (CmdSurfaceCleanupSweep, CmdSurfaceCleanupHere)
