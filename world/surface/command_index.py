"""
Command index for the surface command group.

This is intentionally separate from Evennia's HELP system. It provides a compact
in-game command menu for players/builders/admins using the root command.
"""

from __future__ import annotations

from evennia.locks.lockhandler import LockHandler


SURFACE_COMMAND_INDEX = [
    {
        "access": "Admin",
        "command": "@surfacecleanupsweep",
        "summary": "Dry-run cleanup of disposable generated surface rooms.",
        "lock": "cmd:perm(Admins)",
    },
    {
        "access": "Admin",
        "command": "@surfacecleanupsweep/execute",
        "summary": "Delete cleanup-safe generated surface rooms.",
        "lock": "cmd:perm(Admins)",
    },
    {
        "access": "Admin",
        "command": "@surfacecleanuphere",
        "summary": "Check whether the current generated room can be deleted.",
        "lock": "cmd:perm(Admins)",
    },
    {
        "access": "Builder",
        "command": "@surfaceoverlays",
        "summary": "List persistent overlays on the current surface tile.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "@addsurfacepoi <name> = <description>",
        "summary": "Create a visible persistent POI overlay on the current tile.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "@removesurfaceoverlay <id>",
        "summary": "Remove a persistent surface overlay by id.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "@regensurface",
        "summary": "Regenerate the current surface room while preserving overlays.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "@surfacecleanupcheck",
        "summary": "Report whether the current room is cleanup-safe and why.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "All",
        "command": "surface",
        "summary": "Show this surface command index.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "surface where",
        "summary": "Show your current surface location.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "surface move <n|ne|e|se|s|sw|w|nw>",
        "summary": "Move across the generated surface.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "n, ne, e, se, s, sw, w, nw",
        "summary": "Move one tile while standing in a generated surface room.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "surface ships",
        "summary": "List landed ships visible on the current surface tile.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "surface board <ship name|overlay id>",
        "summary": "Board a landed ship visible on the current surface tile.",
        "lock": "cmd:all()",
    },
]


_ACCESS_ORDER = ["Admin", "Builder", "All"]


def _can_access(caller, lockstring: str) -> bool:
    """
    Evaluate an Evennia-style lockstring against the caller.

    If evaluation fails, default closed.
    """
    try:
        locks = LockHandler(caller)
        locks.add(lockstring)
        return bool(locks.check(caller, "cmd"))
    except Exception:
        return False


def render_surface_command_index(caller) -> str:
    """
    Render the compact surface command index for this caller.
    """
    grouped = {group: [] for group in _ACCESS_ORDER}

    for entry in SURFACE_COMMAND_INDEX:
        if not _can_access(caller, entry["lock"]):
            continue

        access = entry.get("access", "All")
        grouped.setdefault(access, []).append(entry)

    lines = ["Surface commands"]

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