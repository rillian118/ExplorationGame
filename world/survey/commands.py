"""
Survey command group.
"""

from __future__ import annotations

from evennia import Command, default_cmds  # type: ignore
from evennia.commands.cmdset import CmdSet  # type: ignore
from evennia.commands.default.muxcommand import MuxCommand  # type: ignore

from world.survey.commerce import (
    handle_survey_exchange_admin_command,
    handle_survey_exchange_command,
    handle_survey_trade_command,
)
from world.survey.command_index import render_survey_command_index
from world.survey.dataset_objects import (
    find_inventory_cartridge_exact,
    load_cartridge_into_coverage,
    materialize_dataset_cartridge,
    render_cartridge_list,
    render_cartridge_detail,
    render_dataset_or_cartridge_detail,
)
from world.survey.map_readout import render_survey_detail, render_survey_map
from world.survey.route_readout import render_survey_route

try:
    from world.survey.scanning import parse_scan_options, render_survey_target, run_orbital_survey_scan
except Exception:
    parse_scan_options = None
    render_survey_target = None
    run_orbital_survey_scan = None

from world.survey.services import (
    actor_owner_key,
    render_coverage_status,
    render_dataset_list,
    render_export_result,
)


class CmdSurveyLook(default_cmds.CmdLook):
    """
    Look command with exact survey cartridge resolution before fuzzy search.
    """

    key = "look"
    aliases = ["l", "ls"]

    def func(self):
        caller = self.caller
        query = (self.args or "").strip()
        if query.lower().startswith("at "):
            query = query[3:].strip()

        if query:
            cartridge = find_inventory_cartridge_exact(caller, query)
            if cartridge is not None:
                self.msg(
                    text=(render_cartridge_detail(cartridge, looker=caller), {"type": "look"}),
                    options=None,
                )
                return

        super().func()


class CmdSurvey(Command):
    """
    Survey data commands.

    Usage:
      survey
      survey scan
      survey scan target <x> <y>
      survey scan radius <number>
      survey scan resolution <number>
      survey target
      survey target <x> <y>
      survey target clear
      survey route <x1> <y1> <x2> <y2>
      survey route target <x> <y>
      survey scan band
      survey scan band start y <number> [interval <seconds>]
      survey scan band status
      survey scan band pause
      survey scan band resume
      survey scan band step
      survey scan band cancel
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
      survey load status
      survey load cancel
      survey exchange
      survey exchange appraise <dataset id>
      survey exchange sell <dataset id> confirm
      survey trade offers
      survey trade offer <player> <dataset id> <transfer|license> <credits>
      survey trade accept <offer id>
      survey trade decline <offer id>
      survey trade cancel <offer id>
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

        if subcmd == "target":
            if render_survey_target is None:
                caller.msg("Survey target selection is not installed.")
                return

            caller.msg(render_survey_target(caller, rest))
            return

        if subcmd in ("route", "path", "readout"):
            caller.msg(render_survey_route(caller, rest))
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

        if subcmd in ("exchange", "market"):
            caller.msg(handle_survey_exchange_command(caller, rest))
            return

        if subcmd in ("trade", "offer", "offers"):
            trade_args = rest
            if subcmd in ("offer", "offers"):
                trade_args = f"{subcmd} {rest}".strip()
            caller.msg(handle_survey_trade_command(caller, trade_args))
            return

        caller.msg(
            "Usage: survey, survey scan [target <x> <y>] [radius <number>] [resolution <number>], "
            "survey target [<x> <y> or clear], "
            "survey route <x1> <y1> <x2> <y2>, survey route target <x> <y>, "
            "survey scan band [start, status, pause, resume, step, or cancel], "
            "survey status, survey datasets, "
            "survey cartridges, survey map, survey map brief, survey map list, "
            "survey detail <x> <y>, survey inspect <id or cartridge>, "
            "survey export <name>, survey materialize <dataset id>, "
            "survey load <cartridge>, survey load status, survey load cancel, "
            "survey exchange, survey trade offers"
        )


class CmdSurveyExchangeAdmin(MuxCommand):
    """
    Mark the current room as an NPC survey exchange.

    Usage:
      @surveyexchange <name>
      @surveyexchange/clear
    """

    key = "@surveyexchange"
    locks = "cmd:perm(Builder)"
    help_category = "Survey"

    def func(self):
        self.caller.msg(handle_survey_exchange_admin_command(self.caller, self.args, self.switches))


class SurveyCmdSet(CmdSet):
    """
    Command set for survey commands.
    """

    key = "SurveyCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdSurvey())
        self.add(CmdSurveyExchangeAdmin())
