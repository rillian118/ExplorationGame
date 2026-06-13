"""
Compact command index for the survey command group.
"""

from __future__ import annotations


SURVEY_COMMAND_INDEX = [
    {
        "access": "All",
        "command": "survey",
        "summary": "Show this survey command index.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan",
        "summary": "Run an orbital terrain survey from your current ship.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan radius <0-3>",
        "summary": "Run a capped wider orbital survey footprint.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan resolution <1-3>",
        "summary": "Record the scan at a capped higher prototype resolution.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey status",
        "summary": "Show your current survey coverage summary.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey datasets",
        "summary": "List survey datasets you own digitally.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey cartridges",
        "summary": "List survey data cartridges you are carrying.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey map",
        "summary": "Show a compact visual survey map.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey map brief",
        "summary": "Show a screen-reader-friendly semantic survey summary.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey map list",
        "summary": "Show a directional tile list for screen readers.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey detail <x> <y>",
        "summary": "Show focused survey information for one tile.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey inspect <dataset id or cartridge>",
        "summary": "Inspect an owned dataset or a carried survey data cartridge.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey export <name>",
        "summary": "Package your current coverage into a tradable dataset.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey materialize <dataset id>",
        "summary": "Create a physical survey data cartridge for an owned dataset.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey load <cartridge>",
        "summary": "Import a carried survey data cartridge into your survey coverage.",
        "lock": "cmd:all()",
    },
]


_ACCESS_ORDER = ["Admin", "Builder", "All"]


def _can_access(caller, lockstring: str) -> bool:
    """
    Evaluate simple command-index locks.

    For v0.1 this supports the common project locks:
        cmd:all()
        cmd:perm(Admins)
        cmd:perm(Builders)
    """
    lockstring = (lockstring or "").strip()

    if lockstring == "cmd:all()":
        return True

    if "perm(Admins)" in lockstring:
        try:
            return bool(caller.check_permstring("Admins"))
        except Exception:
            return False

    if "perm(Builders)" in lockstring:
        try:
            return bool(caller.check_permstring("Builders") or caller.check_permstring("Admins"))
        except Exception:
            return False

    return False


def render_survey_command_index(caller) -> str:
    """Render the compact survey command index."""
    grouped = {group: [] for group in _ACCESS_ORDER}

    for entry in SURVEY_COMMAND_INDEX:
        if not _can_access(caller, entry["lock"]):
            continue

        access = entry.get("access", "All")
        grouped.setdefault(access, []).append(entry)

    lines = ["Survey commands"]

    for group in _ACCESS_ORDER:
        entries = grouped.get(group) or []
        if not entries:
            continue

        lines.append("")
        lines.append(f"--{group}--")

        for entry in entries:
            lines.append(entry["command"])
            summary = entry.get("summary")
            if summary:
                lines.append(f"  {summary}")

    return "\n".join(lines)
