"""CmdSet wiring for generated planetary surface commands."""

from evennia import CmdSet

from .commands import CmdSurface


class SurfaceCmdSet(CmdSet):
    """Commands for generated planetary surface previews and movement."""

    key = "SurfaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurface())
