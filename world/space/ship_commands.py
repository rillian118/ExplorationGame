"""Commands for ship location state, landed state, and prototype boarding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Tuple

from evennia import Command  # type: ignore

from world.space.models import find_body, find_system_object, read_system_data
from world.surface.models import get_or_create_surface_room, get_surface_address, is_surface_room

from world.space.command_index import render_ship_command_index
from world.space.ship_landing import land_current_ship

from .shipstate import (
    clear_current_ship_for_caller,
    create_ship,
    find_ship,
    format_ship_status,
    get_current_ship_for_caller,
    list_ship_objects,
    read_ship_location,
    set_current_ship_for_caller,
    set_ship_in_system,
    set_ship_landed,
    set_ship_orbiting,
)


LANDED_SHIP_DBREFS_ATTR = "landed_ship_dbrefs"


def _is_builder(caller: Any) -> bool:
    """Return True if caller should be allowed to use builder ship commands."""
    for perm in ("Builders", "Builder", "Admins", "Admin", "Developers", "Developer"):
        try:
            if caller.check_permstring(perm):
                return True
        except Exception:
            pass
    return False


def _split_system_body(text: str) -> Tuple[str, str]:
    """Parse <system>/<body> or <system> <body>, preserving body spaces."""
    text = (text or "").strip()
    if "/" in text:
        system_name, _, body_query = text.partition("/")
        return system_name.strip(), body_query.strip()

    parts = text.split(None, 1)
    if len(parts) < 2:
        return text.strip(), ""

    return parts[0].strip(), parts[1].strip()


def _split_system_body_xy(text: str) -> Tuple[str, str, int | None, int | None, str]:
    """Parse <system>/<body> <x> <y>, allowing spaces in body names."""
    text = (text or "").strip()
    try:
        target_text, x_text, y_text = text.rsplit(None, 2)
    except ValueError:
        return "", "", None, None, "Usage: ship setloc <ship> landed <system>/<body> <x> <y>"

    try:
        x = int(x_text)
        y = int(y_text)
    except ValueError:
        return "", "", None, None, "Landing coordinates must be integers."

    system_name, body_query = _split_system_body(target_text)
    if not system_name or not body_query:
        return "", "", None, None, "Usage: ship setloc <ship> landed <system>/<body> <x> <y>"

    return system_name, body_query, x, y, ""


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ship_display_name(ship: Any) -> str:
    return str(ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship"))


def _resolve_landed_ship_surface(ship: Any):
    """Return the generated surface room for a landed ship, or raise ValueError."""
    state = read_ship_location(ship)

    if state.get("mode") != "landed":
        raise ValueError(f"{_ship_display_name(ship)} is not landed.")

    system_name = state.get("system")
    body_id = state.get("body_id")
    coords = _as_dict(state.get("coordinates"))

    if not system_name or not body_id or not coords:
        raise ValueError(f"{_ship_display_name(ship)} has incomplete landed-location data.")

    system_obj = find_system_object(str(system_name))
    if system_obj is None:
        raise ValueError(f"No imported system named '{system_name}' was found.")

    system_data = read_system_data(system_obj)
    if not system_data:
        raise ValueError(f"System '{system_name}' has no stored system data.")

    body = find_body(system_data, str(body_id))
    if body is None:
        raise ValueError(f"No body id '{body_id}' was found in {system_name}.")

    return get_or_create_surface_room(system_data, body, int(coords.get("x")), int(coords.get("y")))


def _mark_ship_on_surface_room(room: Any, ship: Any) -> None:
    """Record that a landed ship is present at a materialized surface room."""
    dbref = getattr(ship, "dbref", None)
    if not dbref:
        return

    try:
        existing = room.attributes.get(LANDED_SHIP_DBREFS_ATTR) or []
        values = [str(value) for value in existing]
    except Exception:
        values = []

    if str(dbref) not in values:
        values.append(str(dbref))

    room.attributes.add(LANDED_SHIP_DBREFS_ATTR, values)


def _ship_matches_current_surface(ship: Any, room: Any) -> bool:
    """Return whether a landed ship is at the caller's current surface room."""
    if not is_surface_room(room):
        return False

    state = read_ship_location(ship)
    if state.get("mode") != "landed":
        return False

    address = get_surface_address(room)
    coords = _as_dict(state.get("coordinates"))

    return (
        str(address.get("system_name")) == str(state.get("system"))
        and str(address.get("body_id")) == str(state.get("body_id"))
        and int(address.get("x")) == int(coords.get("x"))
        and int(address.get("y")) == int(coords.get("y"))
    )


def _find_landed_ship_at_room(room: Any):
    """Find the first known landed ship recorded at this surface room."""
    if not is_surface_room(room):
        return None

    try:
        dbrefs = room.attributes.get(LANDED_SHIP_DBREFS_ATTR) or []
    except Exception:
        dbrefs = []

    for dbref in dbrefs:
        ship = find_ship(str(dbref))
        if ship is not None and _ship_matches_current_surface(ship, room):
            return ship

    return None


class CmdShip(Command):
    """
    Inspect and manage basic ship location state.

    Usage:
      ship
      ship status [ship]
      ship list
      ship board <ship>
      ship leave
      ship create <name>
      ship setloc <ship> system <system>
      ship setloc <ship> orbit <system>/<body>
      ship setloc <ship> landed <system>/<body> <x> <y>
      ship disembark [ship]
      ship embark [ship]

    Builder-only subcommands:
      create, setloc

    This is a v0.3 test harness. It does not yet create full ship interiors.
    Disembark moves the character to the generated landing surface room; embark
    selects the landed ship as the current ship.
    """

    key = "ship"
    aliases = ["vessel"]
    locks = "cmd:all()"
    help_category = "Space"

    def _resolve_ship_or_current(self, query: str = ""):
        query = (query or "").strip()
        if query:
            return find_ship(query)
        return get_current_ship_for_caller(self.caller)

    def func(self):
        raw = self.args.strip()
        if not raw:
            self.caller.msg(render_ship_command_index(self.caller))
            return

        parts = raw.split(None, 1)
        subcmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if subcmd == "list":
            ships = list_ship_objects()
            if not ships:
                self.caller.msg("No ship objects have been created yet.")
                return

            lines = ["|wKnown Ships|n"]
            for ship in ships:
                name = _ship_display_name(ship)
                lines.append(f"- {name}    {ship.dbref}")
            self.caller.msg("\n".join(lines))
            return

        if subcmd in ("status", "stat", "show"):
            ship = self._resolve_ship_or_current(rest)
            if ship is None:
                self.caller.msg("No current ship selected. Use 'ship board <ship>' or 'ship status <ship>'.")
                return
            self.caller.msg(format_ship_status(ship))
            return
            
        if subcmd == "land":
            self.caller.msg(land_current_ship(self.caller, rest))
            return

        if subcmd == "board":
            if not rest:
                self.caller.msg("Usage: ship board <ship>")
                return

            ship = find_ship(rest)
            if ship is None:
                self.caller.msg(f"No ship named '{rest}' was found.")
                return

            set_current_ship_for_caller(self.caller, ship)
            self.caller.msg(f"Current ship set to {_ship_display_name(ship)} ({ship.dbref}).")
            return

        if subcmd in ("leave", "unboard", "clear"):
            clear_current_ship_for_caller(self.caller)
            self.caller.msg("Current ship cleared.")
            return

        if subcmd == "create":
            if not _is_builder(self.caller):
                self.caller.msg("You do not have permission to create ships.")
                return

            if not rest:
                self.caller.msg("Usage: ship create <name>")
                return

            ship = create_ship(rest, owner=self.caller)
            set_current_ship_for_caller(self.caller, ship)
            self.caller.msg(f"Created ship {_ship_display_name(ship)} ({ship.dbref}) and set it as your current ship.")
            return

        if subcmd == "setloc":
            if not _is_builder(self.caller):
                self.caller.msg("You do not have permission to set ship locations.")
                return

            args = rest.split(None, 2)
            if len(args) < 3:
                self.caller.msg(
                    "Usage: ship setloc <ship> system <system> | "
                    "ship setloc <ship> orbit <system>/<body> | "
                    "ship setloc <ship> landed <system>/<body> <x> <y>"
                )
                return

            ship_query, mode, target = args[0], args[1].lower(), args[2].strip()
            ship = find_ship(ship_query)
            if ship is None:
                self.caller.msg(f"No ship named '{ship_query}' was found.")
                return

            try:
                if mode == "system":
                    state = set_ship_in_system(ship, target)
                elif mode == "orbit":
                    system_name, body_query = _split_system_body(target)
                    if not system_name or not body_query:
                        self.caller.msg("Usage: ship setloc <ship> orbit <system>/<body>")
                        return
                    state = set_ship_orbiting(ship, system_name, body_query)
                elif mode == "landed":
                    system_name, body_query, x, y, error = _split_system_body_xy(target)
                    if error:
                        self.caller.msg(error)
                        return
                    state = set_ship_landed(ship, system_name, body_query, int(x), int(y))
                else:
                    self.caller.msg("Location mode must be 'system', 'orbit', or 'landed'.")
                    return
            except Exception as err:
                self.caller.msg(f"Could not set ship location: {err}")
                return

            body_label = state.get("body_name") or "—"
            coord_label = ""
            coords = _as_dict(state.get("coordinates"))
            if coords:
                coord_label = f" coordinates={coords.get('x')},{coords.get('y')}"

            self.caller.msg(
                f"Updated {_ship_display_name(ship)}: mode={state.get('mode')} "
                f"system={state.get('system')} body={body_label}{coord_label}."
            )
            return

        if subcmd == "disembark":
            ship = self._resolve_ship_or_current(rest)
            if ship is None:
                self.caller.msg("No current ship selected. Use 'ship disembark <ship>' or 'ship board <ship>'.")
                return

            try:
                room = _resolve_landed_ship_surface(ship)
            except Exception as err:
                self.caller.msg(f"You cannot disembark: {err}")
                return

            _mark_ship_on_surface_room(room, ship)
            set_current_ship_for_caller(self.caller, ship)
            self.caller.msg(f"You disembark from {ship.key} onto the surface.")
            self.caller.move_to(room, quiet=False)
            return

        if subcmd == "embark":
            ship = self._resolve_ship_or_current(rest)

            if ship is None:
                ship = _find_landed_ship_at_room(self.caller.location)

            if ship is None:
                self.caller.msg("No landed ship is available here. Use 'ship embark <ship>' if you know the ship name.")
                return

            if not _ship_matches_current_surface(ship, self.caller.location):
                self.caller.msg(f"{_ship_display_name(ship)} is not landed at your current location.")
                return

            set_current_ship_for_caller(self.caller, ship)
            self.caller.msg(
                f"You board {_ship_display_name(ship)}. Ship interiors are not implemented yet, "
                "so your current ship selection has been updated."
            )
            return

        self.caller.msg(
            "Usage: ship, ship status [ship], ship list, ship board <ship>, ship leave,"
            "ship leave, ship create <name>, ship setloc <ship> system <system>, "
            "ship setloc <ship> orbit <system>/<body>, "
            "ship setloc <ship> landed <system>/<body> <x> <y>, "
            "ship land <x> <y>, ship land <system>/<body> <x> <y>, "
            "ship disembark [ship], ship embark [ship]"
        )
