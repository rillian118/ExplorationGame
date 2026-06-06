"""
Patch notes for commands/default_cmdsets.py.

Add this import near the existing surface overlay cmdset import:

    from world.surface.cleanup_commands import CmdSurfaceCleanupSweep, CmdSurfaceCleanupHere

Then inside CharacterCmdSet.at_cmdset_creation(), add:

    self.add(CmdSurfaceCleanupSweep())
    self.add(CmdSurfaceCleanupHere())

Recommended placement: after SurfaceOverlayCmdSet is added.
"""
