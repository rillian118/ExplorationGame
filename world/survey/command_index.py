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
        "command": "survey scan target <x> <y>",
        "summary": "Run a one-shot orbital survey centered on a surface coordinate.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan radius <number>",
        "summary": "Request a wider orbital survey footprint, limited by ship capability.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan resolution <number>",
        "summary": "Request higher scan resolution, limited by ship capability.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey target",
        "summary": "Show the current orbital survey body, default center, and saved target.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey target <x> <y>",
        "summary": "Save a surface coordinate as the default center for future survey scans.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey target clear",
        "summary": "Clear your saved survey target and return scans to the default orbital center.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey route <x1> <y1> <x2> <y2>",
        "summary": "Read out known survey data along a straight-line route.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey route target <x> <y>",
        "summary": "Read out a route from your current/saved survey center to a target coordinate.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band",
        "summary": "Show the active timed orbital band survey status.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band start y <number> [interval <seconds>]",
        "summary": "Start a timed horizontal orbital band survey at a surface y coordinate.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band status",
        "summary": "Show the active orbital band survey cursor.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band pause",
        "summary": "Pause the active timed orbital band survey.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band resume",
        "summary": "Resume a paused timed orbital band survey.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band step",
        "summary": "Manually process one band step for testing or recovery.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey scan band cancel",
        "summary": "Cancel and clear the active orbital band survey.",
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
        "summary": "Show an ANSI terrain survey map when visual mode is enabled.",
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
        "summary": "Begin loading a carried survey data cartridge into your survey coverage in timed chunks.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey load status",
        "summary": "Show active survey cartridge load progress.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey load cancel",
        "summary": "Cancel the active survey cartridge load operation.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey exchange",
        "summary": "Show the local NPC survey exchange, if one is available.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey exchange appraise <dataset id>",
        "summary": "Appraise an owned dataset for local NPC exchange buyout.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey exchange sell <dataset id> confirm",
        "summary": "Sell an owned dataset to the local NPC exchange as an exclusive buyout.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey trade offers",
        "summary": "List pending spontaneous player-to-player survey trade offers.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey trade offer <player> <dataset id> <transfer|license> <credits>",
        "summary": "Offer a nearby player a priced transfer or license for survey data.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey trade accept <offer id>",
        "summary": "Accept a pending room-based survey trade offer.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey trade decline <offer id>",
        "summary": "Decline a pending survey trade offer.",
        "lock": "cmd:all()",
    },
    {
        "access": "All",
        "command": "survey trade cancel <offer id>",
        "summary": "Cancel a survey trade offer you created.",
        "lock": "cmd:all()",
    },
    {
        "access": "Builder",
        "command": "@surveyexchange <name>",
        "summary": "Mark the current room as an NPC survey exchange.",
        "lock": "cmd:perm(Builders)",
    },
    {
        "access": "Builder",
        "command": "@surveyexchange/clear",
        "summary": "Clear the NPC survey exchange marker from the current room.",
        "lock": "cmd:perm(Builders)",
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
