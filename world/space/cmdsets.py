"""CmdSet wiring for space commands."""

from evennia import CmdSet

from .commands import CmdImportSystem, CmdSystem
from world.surface.commands import CmdSurface


class SpaceCmdSet(CmdSet):
    """Commands for inspecting/importing systems and testing generated surfaces."""

    key = "SpaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSystem())
        self.add(CmdImportSystem())
        self.add(CmdSurface())
