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

from evennia import Command  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore

from world.player.command_index import render_player_command_index
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

        caller.msg("Usage: player, player preferences, player preferences <name> <value>")


class PlayerCmdSet(CmdSet):
    """
    Command set for player commands.
    """

    key = "PlayerCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdPlayer())
