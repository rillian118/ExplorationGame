# Exploration MUD v0.2 Starter Code: System Persistence + Inspection

This package adds the first bridge between standalone stellar-system generation and Evennia gameplay.

## What this gives you

- A stable `systemgen` JSON schema for generated systems.
- JSON read/write helpers for the standalone generator.
- An Evennia persistence object for imported systems.
- Builder command: `importsystem <absolute path>`
- Player command: `system`, `system list`, `system scan`, `system bodies`, `system body <name>`

## Suggested copy locations

Copy these into your Evennia game directory:

```text
systemgen/schema.py        -> /home/mud/games/exploration/systemgen/schema.py
systemgen/export.py        -> /home/mud/games/exploration/systemgen/export.py
world/space/*              -> /home/mud/games/exploration/world/space/*
```

If `world/space/` does not exist yet, create it.

## Add the command set

In your character cmdset, usually something like:

```python
# commands/default_cmdsets.py
from world.space.cmdsets import SpaceCmdSet

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(SpaceCmdSet)
```

Then reload Evennia:

```bash
evennia reload
```

## Import a generated system

From inside Evennia as a Builder/Admin:

```text
importsystem /home/mud/games/exploration/system_exports/Astalon.system.json
```

Then test:

```text
system list
system scan Astalon
system bodies Astalon
system body Astalon III in Astalon
```

## Generator integration

Once your generator returns an object or dict, export it like this:

```python
from systemgen.export import adapt_generated_system, write_system_json

raw_system = generate_system(seed=12345, name="Astalon")
record = adapt_generated_system(raw_system)
write_system_json(record, "system_exports/Astalon.system.json")
```

The adapter is intentionally permissive. Replace it with a stricter generator-specific adapter later if needed.

## Design note

This version stores systems as hidden Evennia objects instead of new database models. That is deliberate: it lets you build commands, ship integration, and survey hooks before committing to a heavier persistence model.
