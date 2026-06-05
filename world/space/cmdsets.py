"""Space and exploration command sets."""

from evennia import CmdSet

from .commands import CmdImportSystem, CmdSystem
from .ship_commands import CmdShip
from world.surface.commands import CmdSurface


class SpaceCmdSet(CmdSet):
    """
    Exploration command set.

    Added to the default character cmdset from commands/default_cmdsets.py.
    """

    key = "SpaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSystem())
        self.add(CmdImportSystem())
        self.add(CmdShip())
        self.add(CmdSurface())