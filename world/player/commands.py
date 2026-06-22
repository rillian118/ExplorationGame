"""
Player command group.

Root command:
    player

Preference command:
    player preferences
    player preferences <name>
    player preferences <name> <value>
"""

from __future__ import annotations

from evennia import Command, search_object  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore
from evennia.commands.default.muxcommand import MuxCommand  # type: ignore

from world.player.command_index import render_player_command_index
from world.player.credits import format_credits, get_credits, grant_credits, set_credits
from world.player.preferences import handle_player_preferences_command


class CmdPlayer(Command):
    """
    Player-level commands.

    Usage:
      player
      player preferences
      player preferences <name>
      player preferences <name> <value>
    """

    key = "player"
    locks = "cmd:all()"
    help_category = "Player"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()

        if not raw:
            caller.msg(render_player_command_index(caller))
            return

        parts = raw.split(None, 1)
        subcmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if subcmd in ("preferences", "preference", "prefs", "pref"):
            caller.msg(handle_player_preferences_command(caller, rest))
            return

        if subcmd in ("credits", "credit", "balance"):
            caller.msg(f"Credit balance: {format_credits(get_credits(caller))}.")
            return

        caller.msg("Usage: player, player preferences, player preferences <name> <value>, player credits")


def _display_name(obj) -> str:
    return str(getattr(obj, "key", None) or getattr(obj, "name", None) or obj)


def _find_character(query: str):
    """Best-effort global character/object lookup for builder credit tools."""
    query = (query or "").strip()
    if not query:
        return None

    matches = search_object(query, exact=True) or []
    if not matches and not query.startswith("#"):
        matches = search_object(query) or []
    return matches[0] if matches else None


class CmdCreditsAdmin(MuxCommand):
    """
    Builder/admin credit controls.

    Usage:
      @credits <player>
      @credits/set <player>=<amount>
      @credits/grant <player>=<amount>
    """

    key = "@credits"
    locks = "cmd:perm(Builder)"
    help_category = "Player"

    def func(self):
        if "set" in self.switches:
            if not self.lhs or not self.rhs:
                self.caller.msg("Usage: @credits/set <player>=<amount>")
                return
            target = _find_character(self.lhs)
            if target is None:
                self.caller.msg(f"No player or character matching '{self.lhs}' was found.")
                return
            try:
                amount = int(self.rhs.strip())
            except ValueError:
                self.caller.msg("Credit amount must be a whole number.")
                return
            balance = set_credits(target, amount)
            self.caller.msg(f"Set {_display_name(target)} to {format_credits(balance)}.")
            return

        if "grant" in self.switches:
            if not self.lhs or not self.rhs:
                self.caller.msg("Usage: @credits/grant <player>=<amount>")
                return
            target = _find_character(self.lhs)
            if target is None:
                self.caller.msg(f"No player or character matching '{self.lhs}' was found.")
                return
            try:
                amount = int(self.rhs.strip())
            except ValueError:
                self.caller.msg("Credit amount must be a whole number.")
                return
            balance = grant_credits(target, amount)
            self.caller.msg(
                f"Granted {format_credits(amount)} to {_display_name(target)}. "
                f"Balance: {format_credits(balance)}."
            )
            return

        target = _find_character(self.args)
        if target is None:
            self.caller.msg("Usage: @credits <player>, @credits/set <player>=<amount>, @credits/grant <player>=<amount>")
            return
        self.caller.msg(f"{_display_name(target)} has {format_credits(get_credits(target))}.")


class PlayerCmdSet(CmdSet):
    """
    Command set for player commands.
    """

    key = "PlayerCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdPlayer())
        self.add(CmdCreditsAdmin())
