"""
Persistent survey data models.

Important distinction:

    SurveyCoverage
        Mutable knowledge/progress for an owner, ship, or organization.

    SurveyDataset
        Packaged/snapshotted survey product that can later be traded, sold,
        copied, licensed, loaded, or wrapped by a physical in-game object.

    SurveyDatasetTile
        The tile/coverage rows included in a packaged dataset.

This app intentionally starts with integer owner/object ids instead of hard
ForeignKeys. Survey data may later belong to characters, accounts, ships,
organizations, markets, or physical data cartridges.
"""

from __future__ import annotations

from django.db import models


OWNER_CHARACTER = "character"
OWNER_ACCOUNT = "account"
OWNER_SHIP = "ship"
OWNER_ORG = "org"

SCAN_TERRAIN = "terrain"
SCAN_ORBITAL = "orbital"
SCAN_RESOURCE = "resource"
SCAN_HAZARD = "hazard"
SCAN_POI = "poi"


class SurveyCoverage(models.Model):
    """
    Mutable private/internal survey knowledge.

    This answers: "What does this owner currently know?"
    """

    owner_scope = models.CharField(max_length=32, db_index=True)
    owner_id = models.IntegerField(db_index=True)

    system_name = models.CharField(max_length=128, db_index=True)
    body_id = models.CharField(max_length=128, db_index=True)
    body_name = models.CharField(max_length=128, blank=True, default="")

    x = models.IntegerField(db_index=True)
    y = models.IntegerField(db_index=True)

    scan_type = models.CharField(max_length=64, default=SCAN_TERRAIN, db_index=True)
    resolution = models.IntegerField(default=1, db_index=True)
    quality = models.IntegerField(default=100)

    source_ship_id = models.IntegerField(null=True, blank=True, db_index=True)
    source_object_id = models.IntegerField(null=True, blank=True, db_index=True)

    data = models.JSONField(default=dict, blank=True)

    first_scanned_at = models.DateTimeField(auto_now_add=True)
    last_scanned_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner_scope", "owner_id"]),
            models.Index(fields=["system_name", "body_id", "x", "y"]),
            models.Index(fields=["system_name", "body_id", "scan_type"]),
            models.Index(fields=["source_ship_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "owner_scope",
                    "owner_id",
                    "system_name",
                    "body_id",
                    "x",
                    "y",
                    "scan_type",
                ],
                name="unique_survey_coverage_tile",
            )
        ]

    def __str__(self):
        return (
            f"{self.owner_scope}:{self.owner_id} "
            f"{self.system_name}/{self.body_id} ({self.x}, {self.y}) "
            f"{self.scan_type} r{self.resolution}"
        )


class SurveyDataset(models.Model):
    """
    Packaged survey product.

    This answers: "What can be stored, transferred, traded, or sold?"
    """

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")

    owner_scope = models.CharField(max_length=32, db_index=True)
    owner_id = models.IntegerField(db_index=True)

    creator_id = models.IntegerField(null=True, blank=True, db_index=True)
    source_ship_id = models.IntegerField(null=True, blank=True, db_index=True)

    system_name = models.CharField(max_length=128, db_index=True)
    body_id = models.CharField(max_length=128, db_index=True)
    body_name = models.CharField(max_length=128, blank=True, default="")

    scan_type = models.CharField(max_length=64, default=SCAN_TERRAIN, db_index=True)
    min_resolution = models.IntegerField(default=1)
    max_resolution = models.IntegerField(default=1)
    tile_count = models.IntegerField(default=0)

    integrity = models.IntegerField(default=100)
    is_transferable = models.BooleanField(default=True)
    is_copyable = models.BooleanField(default=True)
    license_mode = models.CharField(max_length=64, default="transferable")

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner_scope", "owner_id"]),
            models.Index(fields=["creator_id"]),
            models.Index(fields=["source_ship_id"]),
            models.Index(fields=["system_name", "body_id"]),
            models.Index(fields=["scan_type"]),
        ]

    def __str__(self):
        return f"{self.name} #{self.id} ({self.system_name}/{self.body_id}, {self.tile_count} tiles)"


class SurveyDatasetTile(models.Model):
    """
    Snapshot of one coverage tile included in a SurveyDataset.

    Dataset tiles should be treated as immutable product contents. Updating
    SurveyCoverage later should not silently mutate an existing dataset.
    """

    dataset = models.ForeignKey(
        SurveyDataset,
        related_name="tiles",
        on_delete=models.CASCADE,
    )

    system_name = models.CharField(max_length=128, db_index=True)
    body_id = models.CharField(max_length=128, db_index=True)
    body_name = models.CharField(max_length=128, blank=True, default="")

    x = models.IntegerField(db_index=True)
    y = models.IntegerField(db_index=True)

    scan_type = models.CharField(max_length=64, default=SCAN_TERRAIN, db_index=True)
    resolution = models.IntegerField(default=1)
    quality = models.IntegerField(default=100)

    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["dataset"]),
            models.Index(fields=["system_name", "body_id", "x", "y"]),
            models.Index(fields=["scan_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "system_name", "body_id", "x", "y", "scan_type"],
                name="unique_survey_dataset_tile",
            )
        ]

    def __str__(self):
        return (
            f"Dataset #{self.dataset_id}: "
            f"{self.system_name}/{self.body_id} ({self.x}, {self.y}) "
            f"{self.scan_type} r{self.resolution}"
        )
