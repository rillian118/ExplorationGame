"""CmdSet wiring for generated planetary surface commands."""

from evennia import CmdSet

from .commands import (
    CmdSurface,
    CmdSurfaceEast,
    CmdSurfaceNorth,
    CmdSurfaceNortheast,
    CmdSurfaceNorthwest,
    CmdSurfaceSouth,
    CmdSurfaceSoutheast,
    CmdSurfaceSouthwest,
    CmdSurfaceWest,
)


class SurfaceCmdSet(CmdSet):
    """Global prototype command for generated planetary surface previews."""

    key = "SurfaceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurface())


class SurfaceRoomCmdSet(CmdSet):
    """Room-local direct movement commands for generated surface rooms."""

    key = "SurfaceRoomCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurfaceNorth())
        self.add(CmdSurfaceNortheast())
        self.add(CmdSurfaceEast())
        self.add(CmdSurfaceSoutheast())
        self.add(CmdSurfaceSouth())
        self.add(CmdSurfaceSouthwest())
        self.add(CmdSurfaceWest())
        self.add(CmdSurfaceNorthwest())
