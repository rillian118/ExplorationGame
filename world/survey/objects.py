"""
Survey data cartridge object typeclasses.

A SurveyDataset is the database record. A SurveyDataCartridge is the tangible
Evennia object that can be carried, dropped, given, stolen, stored, sold, or
loaded later.
"""

from __future__ import annotations

from typeclasses.objects import Object


class SurveyDataCartridge(Object):
    """
    Physical wrapper for a SurveyDataset.

    Required attrs:
        db.survey_dataset_id
        db.dataset_id

    Both attrs are intentionally stored for convenience. `dataset_id` is the
    short generic name that is easy to inspect in-game; `survey_dataset_id` is
    the explicit internal name.
    """

    def at_object_creation(self):
        super().at_object_creation()
        try:
            from world.survey.dataset_objects import (
                SURVEY_CARTRIDGE_TAG,
                SURVEY_CARTRIDGE_TAG_CATEGORY,
            )

            self.tags.add(SURVEY_CARTRIDGE_TAG, category=SURVEY_CARTRIDGE_TAG_CATEGORY)
        except Exception:
            pass

        self.db.item_type = "survey_data_cartridge"
        self.db.desc = (
            "A compact survey data cartridge. It can store a packaged survey "
            "dataset for transport, trade, sale, or later upload."
        )

    def at_init(self):
        super().at_init()
        try:
            from world.survey.dataset_objects import sync_cartridge_aliases

            sync_cartridge_aliases(self)
        except Exception:
            pass

    def get_display_name(self, looker=None, **kwargs):
        try:
            from world.survey.dataset_objects import get_dataset_for_cartridge

            dataset = get_dataset_for_cartridge(self)
            if dataset is not None:
                return f"Survey Data Cartridge: {dataset.name}"
        except Exception:
            pass

        return super().get_display_name(looker=looker, **kwargs)

    def return_appearance(self, looker, **kwargs):
        try:
            from world.survey.dataset_objects import render_cartridge_detail

            return render_cartridge_detail(self, looker=looker)
        except Exception:
            return super().return_appearance(looker, **kwargs)
