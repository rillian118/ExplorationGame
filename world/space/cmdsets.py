"""CmdSet wiring for space commands."""

from evennia import CmdSet

from .commands import CmdImportSystem, CmdSystem


class SpaceCmdSet(CmdSet):
    """Commands for inspecting and importing generated stellar systems."""

    key = "SpaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSystem())
        self.add(CmdImportSystem())
