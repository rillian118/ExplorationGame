"""
Paste this into world/surface/models.py near your other Django model definitions.

Django only auto-discovers models from models.py. If you keep this model in another
file, make sure world/surface/models.py imports it during app loading.
"""

from django.db import models
from evennia.objects.models import ObjectDB


class SurfaceOverlay(models.Model):
    """
    Persistent state layered onto generated planetary surface rooms.

    Generated rooms may be deleted and recreated. SurfaceOverlay records should
    survive that process and be reapplied whenever the surface tile is loaded or
    regenerated.
    """

    planet_key = models.CharField(max_length=128, db_index=True)
    x = models.IntegerField(db_index=True)
    y = models.IntegerField(db_index=True)

    overlay_type = models.CharField(max_length=64, db_index=True)

    # Optional links into Evennia's object database.
    source_object = models.ForeignKey(
        ObjectDB,
        null=True,
        blank=True,
        related_name="surface_overlays_as_source",
        on_delete=models.SET_NULL,
        help_text="Object that physically/logically creates this overlay, such as a landed ship.",
    )
    owner_object = models.ForeignKey(
        ObjectDB,
        null=True,
        blank=True,
        related_name="surface_overlays_as_owner",
        on_delete=models.SET_NULL,
        help_text="Player, account-controlled character, organization object, or owner proxy.",
    )

    name = models.CharField(max_length=160, blank=True, default="")
    description = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True)

    is_permanent = models.BooleanField(default=True)
    blocks_cleanup = models.BooleanField(default=True)
    visible_on_surface = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["planet_key", "x", "y"]),
            models.Index(fields=["planet_key", "x", "y", "overlay_type"]),
            models.Index(fields=["blocks_cleanup"]),
            models.Index(fields=["visible_on_surface"]),
        ]
        ordering = ["planet_key", "x", "y", "overlay_type", "id"]

    def __str__(self):
        label = self.name or self.overlay_type
        return f"{label} @ {self.planet_key} ({self.x}, {self.y})"

    def display_line(self):
        """
        Surface-room prose for this overlay.
        Keep this conservative; richer rendering can move into overlays.py later.
        """
        if self.description:
            return self.description.strip()
        if self.name:
            return self.name.strip()
        return ""
