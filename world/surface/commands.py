"""Commands for previewing and traversing generated planetary surfaces."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from evennia import Command
from evennia.utils import delay

from world.space.models import find_body, find_system_object, read_system_data

from .formatter import format_surface_view
from .generator import compose_surface_room, normalize_direction
from .models import get_or_create_surface_room, get_surface_address, is_surface_room, read_surface_view


BODY_QUERY_HELP = "Use '<system>/<body>' or '<system> <body>'. Example: Astalon/Astalon IV"


def _split_system_body(text: str) -> Tuple[str, str, str]:
    """Return system name, body query, and remaining args from a command tail."""
    text = (text or "").strip()
    if not text:
        return "", "", ""

    if "/" in text:
        left, _, rest = text.partition(" ")
        system_name, _, body_query = left.partition("/")
        return system_name.strip(), body_query.strip(), rest.strip()

    parts = text.split()
    if len(parts) < 3:
        return "", "", ""

    # This form assumes a one-word system and a one-word body id/name token.
    # Multi-word body names should use System/Body syntax.
    return parts[0].strip(), parts[1].strip(), " ".join(parts[2:]).strip()


def _resolve_body(system_name: str, body_query: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """Resolve system/body command input into stored system data and body data."""
    if not system_name or not body_query:
        return None, None, BODY_QUERY_HELP

    system_obj = find_system_object(system_name)
    if system_obj is None:
        return None, None, f"No imported system named '{system_name}' was found."

    system_data = read_system_data(system_obj)
    if not system_data:
        return None, None, f"System '{system_name}' has no stored system data."

    body = find_body(system_data, body_query)
    if body is None:
        return system_data, None, f"No body named '{body_query}' was found in {system_data.get('name', system_name)}."

    return system_data, body, ""


def _parse_xy(rest: str) -> Tuple[Optional[int], Optional[int], str]:
    parts = (rest or "").split()
    if len(parts) < 2:
        return None, None, "Coordinates required: <x> <y>."
    try:
        return int(parts[0]), int(parts[1]), ""
    except ValueError:
        return None, None, "Coordinates must be integers."


def _complete_surface_move(caller: Any, target_room: Any) -> None:
    """Delayed movement callback."""
    if caller is None or target_room is None:
        return
    try:
        caller.db.surface_move_pending = False
        caller.move_to(target_room, quiet=False)
        view = read_surface_view(target_room)
        caller.msg(format_surface_view(view))
    except Exception as err:
        try:
            caller.msg(f"Surface movement failed: {err}")
        except Exception:
            pass


class CmdSurface(Command):
    """Preview and traverse generated planetary surface terrain.

    Usage:
      surface preview <system>/<body> <x> <y>
      surface goto <system>/<body> <x> <y>
      surface look
      surface move <north|east|south|west>

    Examples:
      surface preview Astalon/Astalon IV 10 25
      surface goto Astalon/Astalon IV 10 25
      surface move east

    This is a v0.3 prototype command. It lets builders test deterministic
    terrain, blocked exits, and capped movement delays before ship landing is
    wired into the surface system.
    """

    key = "surface"
    aliases = ["surf"]
    locks = "cmd:all()"
    help_category = "Space"

    def func(self):
        raw = self.args.strip()
        if not raw:
            self.caller.msg(self.__doc__ or "Usage: surface <preview|goto|look|move>")
            return

        parts = raw.split(None, 1)
        subcmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if subcmd == "preview":
            system_name, body_query, coord_text = _split_system_body(rest)
            x, y, error = _parse_xy(coord_text)
            if error:
                self.caller.msg(f"{error} {BODY_QUERY_HELP}")
                return

            system_data, body, error = _resolve_body(system_name, body_query)
            if error:
                self.caller.msg(error)
                return

            view = compose_surface_room(system_data, body, x, y)
            self.caller.msg(format_surface_view(view.to_dict()))
            return

        if subcmd == "goto":
            if not self.caller.permissions.check("Builders"):
                self.caller.msg("Only Builders may use surface goto during the prototype phase.")
                return

            system_name, body_query, coord_text = _split_system_body(rest)
            x, y, error = _parse_xy(coord_text)
            if error:
                self.caller.msg(f"{error} {BODY_QUERY_HELP}")
                return

            system_data, body, error = _resolve_body(system_name, body_query)
            if error:
                self.caller.msg(error)
                return

            room = get_or_create_surface_room(system_data, body, x, y)
            self.caller.move_to(room, quiet=False)
            self.caller.msg(format_surface_view(read_surface_view(room)))
            return

        if subcmd in {"look", "l"}:
            room = self.caller.location
            if not is_surface_room(room):
                self.caller.msg("You are not standing in a generated surface room.")
                return
            self.caller.msg(format_surface_view(read_surface_view(room)))
            return

        if subcmd in {"move", "go", "walk"}:
            direction = normalize_direction(rest)
            if not direction:
                self.caller.msg("Usage: surface move <north|east|south|west>")
                return

            room = self.caller.location
            if not is_surface_room(room):
                self.caller.msg("You are not standing in a generated surface room.")
                return

            if self.caller.db.surface_move_pending:
                self.caller.msg("You are still regaining your footing.")
                return

            next_time = float(self.caller.db.surface_next_move_time or 0.0)
            now = time.time()
            if now < next_time:
                self.caller.msg("You are still regaining your footing.")
                return

            address = get_surface_address(room)
            system_name = address.get("system_name")
            body_id = address.get("body_id")
            x = int(address.get("x"))
            y = int(address.get("y"))

            system_data, body, error = _resolve_body(str(system_name), str(body_id))
            if error:
                self.caller.msg(error)
                return

            view = compose_surface_room(system_data, body, x, y)
            profile = view.directions[direction]

            if not profile.allowed:
                self.caller.msg(profile.blocked_reason or "You cannot travel that way.")
                return

            target_room = get_or_create_surface_room(system_data, body, profile.target_x, profile.target_y)
            move_delay = min(2.0, max(0.0, float(profile.delay_seconds)))
            self.caller.db.surface_next_move_time = now + move_delay

            if profile.message:
                self.caller.msg(profile.message)

            if move_delay <= 0:
                _complete_surface_move(self.caller, target_room)
                return

            self.caller.db.surface_move_pending = True
            delay(move_delay, _complete_surface_move, self.caller, target_room, persistent=False)
            return

        self.caller.msg("Usage: surface preview|goto|look|move")
