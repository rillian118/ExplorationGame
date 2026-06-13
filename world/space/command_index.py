"""
Compact command index for the ship command group.

This is intentionally separate from Evennia HELP. The root `ship` command should
show this index so players can discover available ship commands without digging
through a large global help list.
"""

from __future__ import annotations

from evennia.locks.lockhandler import LockHandler # type: ignore


SHIP_COMMAND_INDEX = [
    {
        "access": "Builder",
        "command": "ship create <name>",
        "summary": "Create a prototype ship and select it as your current ship.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "ship setloc <ship> system <system>",
        "summary": "Set a ship's prototype location to open in-system space.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "ship setloc <ship> orbit <system>/<body>",
        "summary": "Set a ship's prototype location to orbit a body.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "ship setloc <ship> landed <system>/<body> <x> <y>",
        "summary": "Set a ship's prototype location to a surface coordinate.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "ship interior [ship]",
        "summary": "Create/inspect the prototype interior rooms for a ship.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "All",
        "command": "ship",
        "summary": "Show this ship command index.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship status [ship]",
        "summary": "Show status for your current ship or a named ship.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship list",
        "summary": "List known prototype ship objects.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship board <ship>",
        "summary": "Select a known ship as your current ship.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship leave",
        "summary": "Clear your current ship selection.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship land <x> <y>",
        "summary": "Land your current orbiting ship on its current body.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship land <system>/<body> <x> <y>",
        "summary": "Land your current ship at an explicit surface coordinate.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship takeoff",
        "summary": "Take off in your current landed ship.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship disembark [ship]",
        "summary": "Move from a landed ship to its generated surface room.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "ship embark [ship]",
        "summary": "Select a landed ship at your current surface tile.",
        "lock": "cmd:all()",
    },
]

_ACCESS_ORDER = ["Builder", "All"]


def _can_access(caller, lockstring: str) -> bool:
    try:
        locks = LockHandler(caller)
        locks.add(lockstring)
        return bool(locks.check(caller, "cmd"))
    except Exception:
        return False


def render_ship_command_index(caller) -> str:
    grouped = {group: [] for group in _ACCESS_ORDER}

    for entry in SHIP_COMMAND_INDEX:
        if not _can_access(caller, entry["lock"]):
            continue
        grouped.setdefault(entry.get("access", "All"), []).append(entry)

    lines = ["Ship commands"]

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
