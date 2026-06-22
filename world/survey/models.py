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
OWNER_NPC_MARKET = "npc_market"

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


class SurveyTradeOffer(models.Model):
    """
    Pending spontaneous player-to-player survey data offer.

    Persistent public listings can build on this later; v1 offers are still
    room-bound and short-lived.
    """

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    MODE_TRANSFER = "transfer"
    MODE_LICENSE = "license"

    dataset = models.ForeignKey(
        SurveyDataset,
        related_name="trade_offers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    dataset_name = models.CharField(max_length=128, blank=True, default="")

    seller_scope = models.CharField(max_length=32, db_index=True)
    seller_id = models.IntegerField(db_index=True)
    seller_name = models.CharField(max_length=128, blank=True, default="")

    buyer_scope = models.CharField(max_length=32, db_index=True)
    buyer_id = models.IntegerField(db_index=True)
    buyer_name = models.CharField(max_length=128, blank=True, default="")

    mode = models.CharField(max_length=32, default=MODE_TRANSFER, db_index=True)
    price = models.IntegerField(default=0)
    currency = models.CharField(max_length=32, default="credits")

    requested_is_transferable = models.BooleanField(default=True)
    requested_is_copyable = models.BooleanField(default=True)
    requested_license_mode = models.CharField(max_length=64, default="transferable")

    status = models.CharField(max_length=32, default=STATUS_PENDING, db_index=True)
    seller_location_id = models.IntegerField(null=True, blank=True, db_index=True)
    buyer_location_id = models.IntegerField(null=True, blank=True, db_index=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["seller_scope", "seller_id", "status"]),
            models.Index(fields=["buyer_scope", "buyer_id", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return (
            f"Offer #{self.id}: {self.seller_name or self.seller_id} -> "
            f"{self.buyer_name or self.buyer_id} {self.mode} "
            f"{self.dataset_name or self.dataset_id} for {self.price} {self.currency}"
        )


class SurveyMarketTransaction(models.Model):
    """
    Completed survey commerce event.
    """

    TYPE_NPC_BUYOUT = "npc_buyout"
    TYPE_P2P_TRANSFER = "p2p_transfer"
    TYPE_P2P_LICENSE = "p2p_license"

    transaction_type = models.CharField(max_length=32, db_index=True)

    dataset = models.ForeignKey(
        SurveyDataset,
        related_name="market_transactions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    dataset_name = models.CharField(max_length=128, blank=True, default="")
    root_dataset_id = models.IntegerField(null=True, blank=True, db_index=True)
    source_dataset_id = models.IntegerField(null=True, blank=True, db_index=True)

    seller_scope = models.CharField(max_length=32, blank=True, default="", db_index=True)
    seller_id = models.IntegerField(null=True, blank=True, db_index=True)
    seller_name = models.CharField(max_length=128, blank=True, default="")

    buyer_scope = models.CharField(max_length=32, blank=True, default="", db_index=True)
    buyer_id = models.IntegerField(null=True, blank=True, db_index=True)
    buyer_name = models.CharField(max_length=128, blank=True, default="")

    price = models.IntegerField(default=0)
    currency = models.CharField(max_length=32, default="credits")
    status = models.CharField(max_length=32, default="complete", db_index=True)

    exchange_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    exchange_name = models.CharField(max_length=128, blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["transaction_type", "created_at"]),
            models.Index(fields=["seller_scope", "seller_id"]),
            models.Index(fields=["buyer_scope", "buyer_id"]),
            models.Index(fields=["dataset"]),
            models.Index(fields=["root_dataset_id"]),
        ]

    def __str__(self):
        return (
            f"{self.transaction_type} #{self.id}: "
            f"{self.dataset_name or self.dataset_id} for {self.price} {self.currency}"
        )


class SurveyCopyEvent(models.Model):
    """
    Cumulative copy/provenance event for a survey data lineage.
    """

    EVENT_CARTRIDGE = "cartridge"
    EVENT_DIGITAL_LICENSE = "digital_license"

    dataset = models.ForeignKey(
        SurveyDataset,
        related_name="copy_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_dataset = models.ForeignKey(
        SurveyDataset,
        related_name="copy_events_as_source",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    transaction = models.ForeignKey(
        SurveyMarketTransaction,
        related_name="copy_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    root_dataset_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=32, db_index=True)

    actor_scope = models.CharField(max_length=32, blank=True, default="", db_index=True)
    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    object_id = models.IntegerField(null=True, blank=True, db_index=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["root_dataset_id", "event_type"]),
            models.Index(fields=["actor_scope", "actor_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} copy event for root dataset #{self.root_dataset_id}"
