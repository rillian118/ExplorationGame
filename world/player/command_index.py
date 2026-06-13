"""
Command index for player commands.
"""

from __future__ import annotations


PLAYER_COMMAND_INDEX = [
    {
        "access": "All",
        "command": "player",
        "summary": "Show this player command index.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "player preferences",
        "summary": "List current player preferences and valid values.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "player preferences <name>",
        "summary": "Show one player preference.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "player preferences <name> <value>",
        "summary": "Set one player preference.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "player preferences reset <name>",
        "summary": "Reset one player preference to its default.",
        "lock": "cmd:all()",
    },
]


_ACCESS_ORDER = ["Admin", "Builder", "All"]


def _can_access(caller, lockstring: str) -> bool:
    """Evaluate simple command-index locks."""
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


def render_player_command_index(caller) -> str:
    """Render the player command index."""
    grouped = {group: [] for group in _ACCESS_ORDER}

    for entry in PLAYER_COMMAND_INDEX:
        if not _can_access(caller, entry["lock"]):
            continue

        access = entry.get("access", "All")
        grouped.setdefault(access, []).append(entry)

    lines = ["Player commands"]

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
