"""
Survey command group.

This is the initial data-backbone command set. It intentionally does not yet
perform active sensor scans; it exposes the persistent storage surface for
coverage and packaged datasets.
"""

from __future__ import annotations

from evennia import Command  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore

from world.survey.command_index import render_survey_command_index
from world.survey.services import (
    actor_owner_key,
    render_coverage_status,
    render_dataset_detail,
    render_dataset_list,
    render_export_result,
)


class CmdSurvey(Command):
    """
    Survey data commands.

    Usage:
      survey
      survey status
      survey datasets
      survey inspect <dataset id>
      survey export <name>
    """

    key = "survey"
    locks = "cmd:all()"
    help_category = "Survey"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip()

        if not raw:
            caller.msg(render_survey_command_index(caller))
            return

        parts = raw.split(None, 1)
        subcmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        try:
            owner_scope, owner_id = actor_owner_key(caller)
        except Exception as err:
            caller.msg(f"Could not resolve survey owner: {err}")
            return

        if subcmd in ("status", "coverage"):
            caller.msg(render_coverage_status(owner_scope, owner_id))
            return

        if subcmd in ("datasets", "data", "list"):
            caller.msg(render_dataset_list(owner_scope, owner_id))
            return

        if subcmd in ("inspect", "show", "info"):
            if not rest or not rest.lstrip("#").isdigit():
                caller.msg("Usage: survey inspect <dataset id>")
                return

            caller.msg(
                render_dataset_detail(
                    int(rest.lstrip("#")),
                    viewer_scope=owner_scope,
                    viewer_id=owner_id,
                )
            )
            return

        if subcmd == "export":
            name = rest.strip()
            if not name:
                caller.msg("Usage: survey export <name>")
                return

            try:
                caller.msg(render_export_result(caller, name))
            except Exception as err:
                caller.msg(f"Survey export failed: {err}")
            return

        caller.msg("Usage: survey, survey status, survey datasets, survey inspect <id>, survey export <name>")


class SurveyCmdSet(CmdSet):
    """
    Command set for survey commands.
    """

    key = "SurveyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurvey())
