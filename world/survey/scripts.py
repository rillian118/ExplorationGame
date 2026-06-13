"""Timed survey operation scripts."""

from __future__ import annotations

from typeclasses.scripts import Script


class OrbitalBandSurveyScript(Script):
    """Advance a character's orbital band survey operation on a timer."""

    def at_script_creation(self):
        self.key = self.key or "orbital_band_survey_timer"
        self.desc = "Advances one saved orbital band survey step at each interval."
        self.interval = int(self.interval or 60)
        self.start_delay = True
        self.persistent = True

    def at_repeat(self):
        caller = self.obj
        if caller is None:
            self.stop()
            return

        try:
            from world.survey.scanning import run_orbital_band_survey_tick

            message, keep_running = run_orbital_band_survey_tick(caller)
        except Exception as err:
            try:
                caller.msg(f"Orbital band survey timer stopped: {err}")
            except Exception:
                pass
            self.stop()
            return

        if message:
            try:
                caller.msg(message)
            except Exception:
                pass

        if not keep_running:
            self.stop()
