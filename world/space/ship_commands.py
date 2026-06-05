"""Commands for ship location state and test setup."""

from __future__ import annotations

from typing import Any, Tuple

from evennia import Command  # type: ignore

from .shipstate import (
    clear_current_ship_for_caller,
    create_ship,
    find_ship,
    format_ship_status,
    get_current_ship_for_caller,
    list_ship_objects,
    set_current_ship_for_caller,
    set_ship_in_system,
    set_ship_orbiting,
)


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

    Builder-only subcommands:
      create, setloc

    This is a v0.3 test harness for ship location state. It does not yet create
    ship interiors, airlocks, docking exits, or landing ramps.
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
            raw = "status"

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
                name = ship.attributes.get("ship_name") or ship.key
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

        if subcmd == "board":
            if not rest:
                self.caller.msg("Usage: ship board <ship>")
                return

            ship = find_ship(rest)
            if ship is None:
                self.caller.msg(f"No ship named '{rest}' was found.")
                return

            set_current_ship_for_caller(self.caller, ship)
            name = ship.attributes.get("ship_name") or ship.key
            self.caller.msg(f"Current ship set to {name} ({ship.dbref}).")
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
            name = ship.attributes.get("ship_name") or ship.key
            self.caller.msg(f"Created ship {name} ({ship.dbref}) and set it as your current ship.")
            return

        if subcmd == "setloc":
            if not _is_builder(self.caller):
                self.caller.msg("You do not have permission to set ship locations.")
                return

            args = rest.split(None, 2)
            if len(args) < 3:
                self.caller.msg(
                    "Usage: ship setloc <ship> system <system> | "
                    "ship setloc <ship> orbit <system>/<body>"
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
                else:
                    self.caller.msg("Location mode must be 'system' or 'orbit'.")
                    return
            except Exception as err:
                self.caller.msg(f"Could not set ship location: {err}")
                return

            name = ship.attributes.get("ship_name") or ship.key
            self.caller.msg(f"Updated {name}: mode={state.get('mode')} system={state.get('system')} body={state.get('body_name') or '—'}.")
            return

        self.caller.msg(
            "Usage: ship, ship status [ship], ship list, ship board <ship>, "
            "ship leave, ship create <name>, ship setloc <ship> system <system>, "
            "ship setloc <ship> orbit <system>/<body>"
        )
