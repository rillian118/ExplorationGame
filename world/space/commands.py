"""Player and builder commands for generated stellar systems."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from evennia import Command # pyright: ignore[reportMissingImports]

from .formatter import (
    format_body_detail,
    format_body_list,
    format_system_list,
    format_system_summary,
)
from .importer import import_system_json
from .models import find_body, find_system_object, list_system_objects


def get_system_data(system_obj: Any) -> Dict[str, Any]:
    """
    Return stored system data from either a raw dict or an Evennia system object.
    """
    if not system_obj:
        return {}

    if isinstance(system_obj, dict):
        return system_obj

    try:
        data = system_obj.system_data
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        data = system_obj.db.system_data
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        data = system_obj.attributes.get("system_data")
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}

def get_system_display_name(system_obj: Any) -> str:
    """
    Return a readable system name for command messages.
    """
    data = get_system_data(system_obj)
    return data.get("name") or getattr(system_obj, "key", "Unknown System")


def split_body_and_system_query(rest: str) -> tuple[str, str]:
    """
    Parse:
        system body <body name>
        system body <body name> in <system name>

    This handles 'in' case-insensitively and preserves the original body/system
    text around it.
    """
    match = re.search(r"\s+in\s+", rest, flags=re.IGNORECASE)

    if not match:
        return rest.strip(), ""

    body_query = rest[: match.start()].strip()
    system_query = rest[match.end() :].strip()
    return body_query, system_query


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
    supplied in the command. If only one system has been imported, it uses that
    system by default.
    """

    key = "system"
    aliases = ["sys"]
    locks = "cmd:all()"
    help_category = "Space"

    def _default_system(self):
        """
        Resolve the default system.

        Priority:
          1. caller.db.current_system, if set and valid
          2. the only imported system, if exactly one exists
          3. None
        """
        current_name = self.caller.db.current_system

        if current_name:
            found = find_system_object(str(current_name))
            if found:
                return found

        systems = list_system_objects()

        if len(systems) == 1:
            return systems[0]

        return None

    def _system_from_name_or_default(self, name: str):
        """
        Resolve a named system, or fall back to the default system.
        """
        name = (name or "").strip()

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
            system_obj = self._system_from_name_or_default(rest)

            if not system_obj:
                self.caller.msg(
                    "No system selected. Use 'system list' or 'system scan <name>'."
                )
                return

            system_data = get_system_data(system_obj)

            if not system_data:
                self.caller.msg(
                    f"System object '{get_system_display_name(system_obj)}' exists, "
                    "but it has no stored system data."
                )
                return

            self.caller.msg(format_system_summary(system_data))
            return

        if subcmd in ("bodies", "bodylist"):
            system_obj = self._system_from_name_or_default(rest)

            if not system_obj:
                self.caller.msg(
                    "No system selected. Use 'system list' or 'system bodies <name>'."
                )
                return

            system_data = get_system_data(system_obj)

            if not system_data:
                self.caller.msg(
                    f"System object '{get_system_display_name(system_obj)}' exists, "
                    "but it has no stored system data."
                )
                return

            self.caller.msg(format_body_list(system_data))
            return

        if subcmd == "body":
            if not rest:
                self.caller.msg("Usage: system body <body name or id> [in <system name>]")
                return

            body_query, system_query = split_body_and_system_query(rest)

            if not body_query:
                self.caller.msg("Usage: system body <body name or id> [in <system name>]")
                return

            system_obj = self._system_from_name_or_default(system_query)

            if not system_obj:
                self.caller.msg(
                    "No system selected. Use 'system list' or specify "
                    "'system body <body> in <system name>'."
                )
                return

            system_data = get_system_data(system_obj)

            if not system_data:
                self.caller.msg(
                    f"System object '{get_system_display_name(system_obj)}' exists, "
                    "but it has no stored system data."
                )
                return

            body = find_body(system_data, body_query)

            if not body:
                self.caller.msg(
                    f"No body named '{body_query}' was found in "
                    f"{system_data.get('name', 'that system')}."
                )
                return

            self.caller.msg(format_body_detail(system_data, body))
            return

        self.caller.msg(
            "Usage: system, system list, system scan [name], system bodies [name], "
            "system body <body> [in <name>]"
        )


class CmdImportSystem(Command):
    """
    Import a generated stellar system JSON file.

    Usage:
      importsystem <absolute path to json>

    This is a builder/admin command. It persists the system as a hidden Evennia
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
        except Exception as err:
            self.caller.msg(f"System import failed: {err}")
            return

        data = get_system_data(obj)

        self.caller.msg(
            f"Imported {data.get('name', obj.key)}: "
            f"seed={data.get('seed')}, "
            f"bodies={len(data.get('bodies', []) or [])}."
        )