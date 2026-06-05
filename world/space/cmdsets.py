"""CmdSet wiring for space commands."""

from evennia import CmdSet  # type: ignore

from .commands import CmdImportSystem, CmdSystem
from .ship_commands import CmdShip
from world.surface.commands import CmdSurface



class SpaceCmdSet(CmdSet):
    """Commands for generated stellar systems and basic ship state."""

    key = "SpaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSystem())
        self.add(CmdImportSystem())
        self.add(CmdShip())
        self.add(CmdSurface())
