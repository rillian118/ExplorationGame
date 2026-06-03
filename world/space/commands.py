"""Player and builder commands for generated stellar systems."""

from __future__ import annotations

from evennia import Command

from .formatter import (
    format_body_detail,
    format_body_list,
    format_system_list,
    format_system_summary,
)
from .importer import import_system_json
from .models import find_body, find_system_object, list_system_objects


class CmdSystem(Command):
    """
    Inspect the current or named stellar system.

    Usage:
      system
      system list
      system scan [system name]
      system bodies [system name]
      system body <body name or id> [in <system name>]

    The command first looks for caller.db.current_system, then for a system name
    supplied in the command.  If only one system has been imported, it uses that
    system by default.
    """

    key = "system"
    aliases = ["sys"]
    locks = "cmd:all()"
    help_category = "Space"

    def _default_system(self):
        current_name = self.caller.db.current_system
        if current_name:
            found = find_system_object(str(current_name))
            if found:
                return found

        systems = list_system_objects()
        if len(systems) == 1:
            return systems[0]
        return None

    def _system_from_name_or_default(self, name):
        if name:
            return find_system_object(name)
        return self._default_system()

    def func(self):
        raw = self.args.strip()
        if not raw:
            raw = "scan"

        parts = raw.split(None, 1)
        subcmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if subcmd == "list":
            self.caller.msg(format_system_list(list_system_objects()))
            return

        if subcmd in ("scan", "show", "summary"):
            system = self._system_from_name_or_default(rest)
            if not system:
                self.caller.msg("No system selected. Use 'system list' or 'system scan <name>'.")
                return
            self.caller.msg(format_system_summary(system.db.system_data or {}))
            return

        if subcmd in ("bodies", "bodylist"):
            system = self._system_from_name_or_default(rest)
            if not system:
                self.caller.msg("No system selected. Use 'system list' or 'system bodies <name>'.")
                return
            self.caller.msg(format_body_list(system.db.system_data or {}))
            return

        if subcmd == "body":
            if not rest:
                self.caller.msg("Usage: system body <body name or id> [in <system name>]")
                return

            body_query = rest
            system_query = ""
            if " in " in rest.lower():
                left, right = rest.rsplit(" in ", 1)
                body_query = left.strip()
                system_query = right.strip()

            system = self._system_from_name_or_default(system_query)
            if not system:
                self.caller.msg("No system selected. Use 'system list' or specify 'in <system name>'.")
                return

            data = system.db.system_data or {}
            body = find_body(data, body_query)
            if not body:
                self.caller.msg(f"No body named '{body_query}' was found in {data.get('name', 'that system')}.")
                return

            self.caller.msg(format_body_detail(data, body))
            return

        self.caller.msg("Usage: system, system list, system scan [name], system bodies [name], system body <body> [in <name>]")


class CmdImportSystem(Command):
    """
    Import a generated stellar system JSON file.

    Usage:
      importsystem <absolute path to json>

    This is a builder/admin command.  It persists the system as a hidden Evennia
    object, replacing the existing data if a system with the same name exists.
    """

    key = "importsystem"
    locks = "cmd:perm(Builders)"
    help_category = "Building"

    def func(self):
        path = self.args.strip()
        if not path:
            self.caller.msg("Usage: importsystem <absolute path to json>")
            return

        try:
            obj = import_system_json(path)
        except Exception as err:  # Evennia should display a clean builder-facing error.
            self.caller.msg(f"System import failed: {err}")
            return

        data = obj.db.system_data or {}
        self.caller.msg(
            f"Imported {data.get('name', obj.key)}: seed={data.get('seed')}, bodies={len(data.get('bodies', []) or [])}."
        )
