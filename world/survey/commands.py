"""
Survey command group.
"""

from __future__ import annotations

from evennia import Command  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore

from world.survey.command_index import render_survey_command_index
from world.survey.dataset_objects import (
    materialize_dataset_cartridge,
    render_cartridge_list,
    render_dataset_or_cartridge_detail,
)

try:
    from world.survey.scanning import run_orbital_survey_scan
except Exception:
    run_orbital_survey_scan = None

from world.survey.services import (
    actor_owner_key,
    render_coverage_status,
    render_dataset_list,
    render_export_result,
)


class CmdSurvey(Command):
    """
    Survey data commands.

    Usage:
      survey
      survey scan
      survey status
      survey datasets
      survey cartridges
      survey inspect <dataset id|cartridge>
      survey export <name>
      survey materialize <dataset id>
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

        if subcmd == "scan":
            if run_orbital_survey_scan is None:
                caller.msg("Survey scan is not installed.")
                return
            caller.msg(run_orbital_survey_scan(caller))
            return

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

        if subcmd in ("cartridges", "cartridge", "items"):
            caller.msg(render_cartridge_list(caller))
            return

        if subcmd in ("inspect", "show", "info"):
            if not rest:
                caller.msg("Usage: survey inspect <dataset id|cartridge>")
                return

            caller.msg(
                render_dataset_or_cartridge_detail(
                    caller,
                    rest,
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

        if subcmd in ("materialize", "cartridge-create", "make-cartridge"):
            if not rest or not rest.lstrip("#").isdigit():
                caller.msg("Usage: survey materialize <dataset id>")
                return

            caller.msg(materialize_dataset_cartridge(caller, int(rest.lstrip("#"))))
            return

        caller.msg(
            "Usage: survey, survey scan, survey status, survey datasets, "
            "survey cartridges, survey inspect <id|cartridge>, "
            "survey export <name>, survey materialize <dataset id>"
        )


class SurveyCmdSet(CmdSet):
    """
    Command set for survey commands.
    """

    key = "SurveyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurvey())
