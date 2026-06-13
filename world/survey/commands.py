"""
Survey command group.
"""

from __future__ import annotations

from evennia import Command  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore

from world.survey.command_index import render_survey_command_index
from world.survey.dataset_objects import (
    load_cartridge_into_coverage,
    materialize_dataset_cartridge,
    render_cartridge_list,
    render_dataset_or_cartridge_detail,
)
from world.survey.map_readout import render_survey_detail, render_survey_map

try:
    from world.survey.scanning import parse_scan_options, run_orbital_survey_scan
except Exception:
    parse_scan_options = None
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
      survey scan radius <number>
      survey scan resolution <number>
      survey status
      survey datasets
      survey cartridges
      survey map
      survey map visual
      survey map brief
      survey map list
      survey detail <x> <y>
      survey inspect <dataset id or cartridge>
      survey export <name>
      survey materialize <dataset id>
      survey load <cartridge>
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
            if run_orbital_survey_scan is None or parse_scan_options is None:
                caller.msg("Survey scan is not installed.")
                return

            options, error = parse_scan_options(rest)
            if error:
                caller.msg(error)
                return

            caller.msg(run_orbital_survey_scan(caller, **options))
            return

        # Support both "survey map brief" and "survey map/brief".
        if subcmd.startswith("map"):
            map_args = rest
            if "/" in subcmd:
                _base, switch = subcmd.split("/", 1)
                if switch:
                    map_args = f"{switch} {rest}".strip()
            caller.msg(render_survey_map(caller, map_args))
            return

        if subcmd == "detail":
            caller.msg(render_survey_detail(caller, rest))
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
                caller.msg("Usage: survey inspect <dataset id or cartridge>")
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

        if subcmd in ("load", "import"):
            caller.msg(load_cartridge_into_coverage(caller, rest))
            return

        caller.msg(
            "Usage: survey, survey scan [radius <number>] [resolution <number>], survey status, survey datasets, "
            "survey cartridges, survey map, survey map brief, survey map list, "
            "survey detail <x> <y>, survey inspect <id or cartridge>, "
            "survey export <name>, survey materialize <dataset id>, "
            "survey load <cartridge>"
        )


class SurveyCmdSet(CmdSet):
    """
    Command set for survey commands.
    """

    key = "SurveyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurvey())
