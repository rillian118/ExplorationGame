"""
Player-facing commands for generated planetary surface rooms.

Overlay/admin commands should live in world.surface.overlay_commands.
"""

from __future__ import annotations

from typing import Any

from evennia import Command  # type: ignore

from world.space.models import find_body, find_system_object, read_system_data
from world.surface.generator import normalize_direction
from world.surface.models import (
    get_or_create_surface_room,
    get_surface_address,
    is_surface_room,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _get_current_surface_context(caller):
    """
    Return room, address, system_data, body, or an error string.
    """
    room = caller.location
    if not room:
        return None, {}, {}, {}, "You are nowhere."

    if not is_surface_room(room):
        return room, {}, {}, {}, "This is not a generated surface tile."

    address = get_surface_address(room)
    system_name = address.get("system_name")
    body_id = address.get("body_id")

    if not system_name or not body_id:
        return room, address, {}, {}, "This surface tile has incomplete address data."

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        return room, address, {}, {}, f"No imported system named '{system_name}' was found."

    system_data = read_system_data(system_obj)
    if not system_data:
        return room, address, {}, {}, f"System '{system_name}' has no stored system data."

    body = find_body(system_data, str(body_id))
    if body is None:
        return room, address, system_data, {}, f"No body id '{body_id}' was found in {system_name}."

    return room, address, system_data, body, ""


def move_surface(caller, raw_direction: str):
    """
    Move caller from one generated surface room to an adjacent surface room.
    """
    direction = normalize_direction(raw_direction)

    if not direction:
        caller.msg("Usage: surface move <n|ne|e|se|s|sw|w|nw>")
        return

    room, address, system_data, body, error = _get_current_surface_context(caller)
    if error:
        caller.msg(error)
        return

        try:
        from world.surface.generator import evaluate_direction

        profile_obj = evaluate_direction(
            system_data,
            body,
            int(address.get("x")),
            int(address.get("y")),
            direction,
        )
        profile = profile_obj.to_dict()
    except Exception as err:
        caller.msg(f"Could not generate movement data for {direction}: {err}")
        return

    if not profile.get("allowed", True):
        caller.msg(profile.get("blocked_reason") or f"You cannot travel {direction}.")
        return

    target_x = int(profile["target_x"])
    target_y = int(profile["target_y"])

    try:
        target_room = get_or_create_surface_room(system_data, body, target_x, target_y)
    except Exception as err:
        caller.msg(f"Surface movement failed: {err}")
        return

    message = profile.get("message")
    if message:
        caller.msg(message)

    caller.move_to(target_room, quiet=False)


class CmdSurface(Command):
    """
    Inspect or move across a generated planetary surface.

    Usage:
      surface
      surface where
      surface move <direction>
    """

    key = "surface"
    aliases = ["surf"]
    locks = "cmd:all()"
    help_category = "Surface"

    def func(self):
        caller = self.caller
        raw = self.args.strip()

        if not raw or raw.lower() in ("where", "coords", "location"):
            room, address, system_data, body, error = _get_current_surface_context(caller)
            if error:
                caller.msg(error)
                return

            caller.msg(
                "Surface location: "
                f"{address.get('system_name', 'Unknown System')} / "
                f"{address.get('body_name') or address.get('body_id', 'Unknown Body')} "
                f"({address.get('x')}, {address.get('y')})"
            )
            return

        parts = raw.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "move":
            move_surface(caller, parts[1])
            return

        caller.msg("Usage: surface, surface where, or surface move <direction>.")


class CmdSurfaceDirection(Command):
    """
    Base command for direct surface movement aliases.
    """

    key = ""
    locks = "cmd:all()"
    help_category = "Surface"

    direction = ""

    def func(self):
        move_surface(self.caller, self.direction or self.key)


class CmdSurfaceNorth(CmdSurfaceDirection):
    key = "n"
    aliases = ["north"]
    direction = "north"


class CmdSurfaceNortheast(CmdSurfaceDirection):
    key = "ne"
    aliases = ["northeast"]
    direction = "northeast"


class CmdSurfaceEast(CmdSurfaceDirection):
    key = "e"
    aliases = ["east"]
    direction = "east"


class CmdSurfaceSoutheast(CmdSurfaceDirection):
    key = "se"
    aliases = ["southeast"]
    direction = "southeast"


class CmdSurfaceSouth(CmdSurfaceDirection):
    key = "s"
    aliases = ["south"]
    direction = "south"


class CmdSurfaceSouthwest(CmdSurfaceDirection):
    key = "sw"
    aliases = ["southwest"]
    direction = "southwest"


class CmdSurfaceWest(CmdSurfaceDirection):
    key = "w"
    aliases = ["west"]
    direction = "west"


class CmdSurfaceNorthwest(CmdSurfaceDirection):
    key = "nw"
    aliases = ["northwest"]
    direction = "northwest"