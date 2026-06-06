"""Patch snippet for commands/default_cmdsets.py.

Add the import near the existing SpaceCmdSet import:

    from world.surface.overlay_commands import SurfaceOverlayCmdSet

Then add the cmdset inside CharacterCmdSet.at_cmdset_creation after
self.add(SpaceCmdSet()):

    self.add(SurfaceOverlayCmdSet())

Do not install this file as-is; it is a reference snippet.
"""

from world.surface.overlay_commands import SurfaceOverlayCmdSet

# inside CharacterCmdSet.at_cmdset_creation:
# self.add(SurfaceOverlayCmdSet())
