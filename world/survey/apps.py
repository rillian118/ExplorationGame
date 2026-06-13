"""
Django app config for persistent survey data.
"""

from django.apps import AppConfig


class SurveyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "world.survey"
    label = "survey"
