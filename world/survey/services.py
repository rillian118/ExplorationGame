"""
Survey service helpers.

These functions keep command code thin and make it easier to reuse survey
storage for future scanners, markets, data cartridges, org archives, and NPC
buyers.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from django.db import transaction

from world.survey.models import (
    OWNER_CHARACTER,
    SCAN_TERRAIN,
    SurveyCoverage,
    SurveyDataset,
    SurveyDatasetTile,
)


def actor_owner_key(actor: Any) -> tuple[str, int]:
    """
    Return the default survey owner key for a character/player object.
    """
    if actor is None:
        raise ValueError("Survey owner actor is required.")

    try:
        return OWNER_CHARACTER, int(actor.id)
    except Exception as err:
        raise ValueError("Could not resolve survey owner id.") from err


def _ship_id_from_caller(caller: Any) -> int | None:
    """Best-effort current ship id for provenance metadata."""
    try:
        from world.space.shipstate import get_current_ship_for_caller

        ship = get_current_ship_for_caller(caller)
        if ship is not None:
            return int(ship.id)
    except Exception:
        pass
    return None


def get_owner_coverage(owner_scope: str, owner_id: int):
    """Return SurveyCoverage queryset for an owner."""
    return SurveyCoverage.objects.filter(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
    ).order_by("system_name", "body_id", "scan_type", "x", "y")


def get_owner_datasets(owner_scope: str, owner_id: int):
    """Return SurveyDataset queryset for an owner."""
    return SurveyDataset.objects.filter(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
    ).order_by("-created_at", "-id")


def summarize_coverage(owner_scope: str, owner_id: int) -> dict[str, Any]:
    """
    Return compact coverage summary for an owner.
    """
    qs = get_owner_coverage(owner_scope, owner_id)
    total = qs.count()

    by_body = Counter()
    by_scan_type = Counter()
    max_resolution = 0

    for row in qs.iterator():
        body_label = f"{row.system_name}/{row.body_name or row.body_id}"
        by_body[body_label] += 1
        by_scan_type[row.scan_type] += 1
        max_resolution = max(max_resolution, int(row.resolution or 0))

    return {
        "total": total,
        "by_body": dict(by_body),
        "by_scan_type": dict(by_scan_type),
        "max_resolution": max_resolution,
    }


def render_coverage_status(owner_scope: str, owner_id: int) -> str:
    """Render an owner coverage status report."""
    summary = summarize_coverage(owner_scope, owner_id)

    lines = ["Survey coverage status"]
    lines.append(f"  Total known tiles: {summary['total']}")
    lines.append(f"  Max resolution: {summary['max_resolution']}")

    if summary["by_body"]:
        lines.append("")
        lines.append("By body:")
        for body, count in sorted(summary["by_body"].items()):
            lines.append(f"  {body}: {count} tiles")

    if summary["by_scan_type"]:
        lines.append("")
        lines.append("By scan type:")
        for scan_type, count in sorted(summary["by_scan_type"].items()):
            lines.append(f"  {scan_type}: {count} tiles")

    if summary["total"] == 0:
        lines.append("")
        lines.append("No survey coverage recorded yet.")

    return "\n".join(lines)


def upsert_coverage_tile(
    *,
    owner_scope: str,
    owner_id: int,
    system_name: str,
    body_id: str,
    body_name: str = "",
    x: int,
    y: int,
    scan_type: str = SCAN_TERRAIN,
    resolution: int = 1,
    quality: int = 100,
    source_ship_id: int | None = None,
    source_object_id: int | None = None,
    data: dict | None = None,
) -> SurveyCoverage:
    """
    Create or update a mutable coverage record.

    Existing records keep the best resolution and quality seen so far, and
    merge the latest data payload over the old payload.
    """
    defaults = {
        "body_name": body_name or "",
        "resolution": int(resolution),
        "quality": int(quality),
        "source_ship_id": source_ship_id,
        "source_object_id": source_object_id,
        "data": data or {},
    }

    obj, created = SurveyCoverage.objects.get_or_create(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
        system_name=str(system_name),
        body_id=str(body_id),
        x=int(x),
        y=int(y),
        scan_type=str(scan_type),
        defaults=defaults,
    )

    if not created:
        changed = True  # Refresh last_scanned_at even when the payload is unchanged.

        incoming_resolution = int(resolution)
        current_resolution = int(obj.resolution or 0)

        if incoming_resolution > current_resolution:
            obj.resolution = int(resolution)
            changed = True

        if int(quality) > int(obj.quality or 0):
            obj.quality = int(quality)
            changed = True

        if incoming_resolution >= current_resolution:
            merged = dict(obj.data or {})
            merged.update(data or {})
        else:
            merged = dict(data or {})
            merged.update(obj.data or {})
        if merged != (obj.data or {}):
            obj.data = merged
            changed = True

        if body_name and obj.body_name != body_name:
            obj.body_name = body_name
            changed = True

        if source_ship_id and obj.source_ship_id != source_ship_id:
            obj.source_ship_id = source_ship_id
            changed = True

        if source_object_id and obj.source_object_id != source_object_id:
            obj.source_object_id = source_object_id
            changed = True

        if changed:
            obj.save()

    return obj


@transaction.atomic
def export_dataset_from_coverage(
    *,
    owner_scope: str,
    owner_id: int,
    name: str,
    creator_id: int | None = None,
    source_ship_id: int | None = None,
    scan_type: str | None = None,
    system_name: str | None = None,
    body_id: str | None = None,
    description: str = "",
) -> SurveyDataset:
    """
    Snapshot matching SurveyCoverage rows into a SurveyDataset.

    The dataset is a packaged product. It does not automatically update when
    SurveyCoverage changes later.
    """
    qs = get_owner_coverage(owner_scope, owner_id)

    if scan_type:
        qs = qs.filter(scan_type=scan_type)

    if system_name:
        qs = qs.filter(system_name=system_name)

    if body_id:
        qs = qs.filter(body_id=body_id)

    rows = list(qs.order_by("system_name", "body_id", "scan_type", "x", "y"))

    if not rows:
        raise ValueError("No survey coverage matches that export request.")

    first = rows[0]
    resolutions = [int(row.resolution or 0) for row in rows]

    dataset = SurveyDataset.objects.create(
        name=name,
        description=description,
        owner_scope=owner_scope,
        owner_id=int(owner_id),
        creator_id=creator_id,
        source_ship_id=source_ship_id,
        system_name=system_name or first.system_name,
        body_id=body_id or first.body_id,
        body_name=first.body_name or "",
        scan_type=scan_type or first.scan_type,
        min_resolution=min(resolutions) if resolutions else 0,
        max_resolution=max(resolutions) if resolutions else 0,
        tile_count=len(rows),
        metadata={
            "export_filters": {
                "scan_type": scan_type,
                "system_name": system_name,
                "body_id": body_id,
            }
        },
    )

    tiles = [
        SurveyDatasetTile(
            dataset=dataset,
            system_name=row.system_name,
            body_id=row.body_id,
            body_name=row.body_name,
            x=row.x,
            y=row.y,
            scan_type=row.scan_type,
            resolution=row.resolution,
            quality=row.quality,
            data=dict(row.data or {}),
        )
        for row in rows
    ]

    SurveyDatasetTile.objects.bulk_create(tiles)
    return dataset


@transaction.atomic
def import_dataset_tiles_to_coverage(
    *,
    dataset: SurveyDataset,
    owner_scope: str,
    owner_id: int,
    source_object_id: int | None = None,
) -> dict[str, Any]:
    """
    Import a packaged dataset into an owner's mutable SurveyCoverage.

    This is the core "load cartridge" operation. It does not alter or consume
    the SurveyDataset, and it does not require the digital dataset owner to be
    the importing actor. Possession/access should be checked by the caller.

    Existing coverage rows are improved/merged by `upsert_coverage_tile`.
    """
    tiles = list(dataset.tiles.all().order_by("system_name", "body_id", "scan_type", "x", "y"))

    created = 0
    updated = 0
    unchanged_or_merged = 0

    for tile in tiles:
        existed = SurveyCoverage.objects.filter(
            owner_scope=owner_scope,
            owner_id=int(owner_id),
            system_name=tile.system_name,
            body_id=tile.body_id,
            x=int(tile.x),
            y=int(tile.y),
            scan_type=tile.scan_type,
        ).exists()

        data = dict(tile.data or {})
        data.update(
            {
                "loaded_from_dataset_id": int(dataset.id),
                "loaded_from_dataset_name": dataset.name,
                "loaded_from_cartridge_object_id": source_object_id,
                "loaded_via": "survey_data_cartridge",
            }
        )

        upsert_coverage_tile(
            owner_scope=owner_scope,
            owner_id=int(owner_id),
            system_name=tile.system_name,
            body_id=tile.body_id,
            body_name=tile.body_name or dataset.body_name or "",
            x=int(tile.x),
            y=int(tile.y),
            scan_type=tile.scan_type,
            resolution=int(tile.resolution or 0),
            quality=int(tile.quality or 0),
            source_ship_id=dataset.source_ship_id,
            source_object_id=source_object_id,
            data=data,
        )

        if existed:
            updated += 1
        else:
            created += 1

    # Kept as a separate field for future richer diffing.
    unchanged_or_merged = updated

    return {
        "dataset_id": int(dataset.id),
        "dataset_name": dataset.name,
        "tile_count": len(tiles),
        "created": created,
        "updated": updated,
        "merged": unchanged_or_merged,
    }


def render_dataset_list(owner_scope: str, owner_id: int) -> str:
    """Render datasets owned by an owner."""
    datasets = list(get_owner_datasets(owner_scope, owner_id)[:20])

    if not datasets:
        return "You do not own any survey datasets."

    lines = ["Survey datasets:"]
    for dataset in datasets:
        lines.append(
            f"  #{dataset.id}: {dataset.name} "
            f"[{dataset.system_name}/{dataset.body_name or dataset.body_id}, "
            f"{dataset.tile_count} tiles, r{dataset.min_resolution}-{dataset.max_resolution}, "
            f"{dataset.scan_type}]"
        )

    return "\n".join(lines)


def render_dataset_detail(dataset_id: int, *, viewer_scope: str, viewer_id: int) -> str:
    """Render one dataset if viewer owns it."""
    try:
        dataset = SurveyDataset.objects.get(
            id=int(dataset_id),
            owner_scope=viewer_scope,
            owner_id=int(viewer_id),
        )
    except SurveyDataset.DoesNotExist:
        return f"No owned survey dataset #{dataset_id} was found."

    lines = [
        f"Survey Dataset #{dataset.id}: {dataset.name}",
        f"  Body: {dataset.system_name}/{dataset.body_name or dataset.body_id}",
        f"  Scan type: {dataset.scan_type}",
        f"  Tiles: {dataset.tile_count}",
        f"  Resolution: {dataset.min_resolution}-{dataset.max_resolution}",
        f"  Integrity: {dataset.integrity}%",
        f"  Transferable: {'yes' if dataset.is_transferable else 'no'}",
        f"  Copyable: {'yes' if dataset.is_copyable else 'no'}",
        f"  License: {dataset.license_mode}",
    ]

    if dataset.description:
        lines.append("")
        lines.append(dataset.description)

    return "\n".join(lines)


def render_export_result(caller: Any, name: str) -> str:
    """
    Export all caller-owned coverage into a dataset.

    This is intentionally broad for v0.1. More filters can be added after scan
    mechanics exist.
    """
    owner_scope, owner_id = actor_owner_key(caller)
    creator_id = owner_id
    source_ship_id = _ship_id_from_caller(caller)

    dataset = export_dataset_from_coverage(
        owner_scope=owner_scope,
        owner_id=owner_id,
        name=name,
        creator_id=creator_id,
        source_ship_id=source_ship_id,
    )

    return (
        f"Created survey dataset #{dataset.id}: {dataset.name} "
        f"({dataset.tile_count} tiles)."
    )
