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
from django.utils import timezone

from world.survey.models import (
    OWNER_CHARACTER,
    SCAN_TERRAIN,
    SurveyCoverage,
    SurveyDataset,
    SurveyDatasetTile,
)


BULK_DATASET_IMPORT_BATCH_SIZE = 500
DATASET_VALUATION_VERSION = 1


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


def _coverage_key(system_name: str, body_id: str, x: int, y: int, scan_type: str) -> tuple[str, str, int, int, str]:
    """Return the unique logical key for one coverage tile."""
    return (str(system_name), str(body_id), int(x), int(y), str(scan_type))


def _merged_coverage_data(
    existing_data: dict | None,
    incoming_data: dict | None,
    *,
    current_resolution: int,
    incoming_resolution: int,
) -> dict:
    """Merge tile payloads while preserving higher-resolution data."""
    if int(incoming_resolution) >= int(current_resolution):
        merged = dict(existing_data or {})
        merged.update(incoming_data or {})
    else:
        merged = dict(incoming_data or {})
        merged.update(existing_data or {})
    return merged


def _payload_values(data: dict[str, Any], *keys: str) -> list[str]:
    """Return normalized string values from scalar/list-like payload fields."""
    for key in keys:
        value = data.get(key)
        if not value:
            continue
        values = value if isinstance(value, (list, tuple, set)) else [value]
        result = [
            str(item)
            for item in values
            if item is not None and item != "" and str(item).lower() != "none"
        ]
        if result:
            return result
    return []


def _safe_int(value: Any, default: int = 0) -> int:
    """Return value as an int without letting legacy metadata break display."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _value_grade(value_points: int) -> str:
    """Return coarse valuation grade."""
    if value_points >= 2000:
        return "exceptional"
    if value_points >= 900:
        return "valuable"
    if value_points >= 300:
        return "useful"
    return "routine"


def calculate_dataset_valuation(rows: Iterable[SurveyCoverage]) -> dict[str, Any]:
    """
    Calculate first-pass dataset valuation metadata from coverage rows.

    This is a market-facing estimate, not final currency. Later market demand,
    ownership, licensing, age, and buyer-specific needs can adjust it.
    """
    rows = list(rows)
    tile_count = len(rows)
    if not rows:
        return {
            "version": DATASET_VALUATION_VERSION,
            "points": 0,
            "grade": "empty",
            "basis": "survey dataset valuation v1",
            "factors": {},
            "counts": {"tiles": 0},
            "tags": [],
            "notes": ["No tiles were included in this dataset."],
        }

    terrain = Counter()
    resources = Counter()
    anomalies = Counter()
    hazards = Counter()
    environment_tags = Counter()
    resolutions: list[int] = []
    qualities: list[int] = []
    hazard_tiles = 0
    resource_tiles = 0
    anomaly_tiles = 0

    for row in rows:
        data = dict(row.data or {})
        resolutions.append(int(row.resolution or 0))
        qualities.append(int(row.quality or 0))

        terrain_label = (
            data.get("terrain")
            or data.get("terrain_label")
            or data.get("terrain_name")
            or row.scan_type
        )
        if terrain_label:
            terrain[str(terrain_label).lower()] += 1

        row_hazards = _payload_values(data, "hazards", "hazard")
        if row_hazards:
            hazard_tiles += 1
            for hazard in row_hazards:
                hazards[hazard] += 1

        row_resources = _payload_values(data, "resource_signatures", "resources")
        if row_resources:
            resource_tiles += 1
            for resource in row_resources:
                resources[resource] += 1

        row_anomalies = _payload_values(data, "anomaly_signatures", "anomalies")
        if row_anomalies:
            anomaly_tiles += 1
            for anomaly in row_anomalies:
                anomalies[anomaly] += 1

        for key in ("temperature_band", "radiation_band", "gravity_band", "roughness_class"):
            value = data.get(key)
            if value and str(value).lower() not in {"nominal", "low", "smooth", "none"}:
                environment_tags[f"{key}:{value}"] += 1

    max_resolution = max(resolutions) if resolutions else 0
    min_resolution = min(resolutions) if resolutions else 0
    avg_quality = int(sum(qualities) / len(qualities)) if qualities else 0
    terrain_variety = len(terrain)
    resource_variety = len(resources)
    anomaly_variety = len(anomalies)
    hazard_variety = len(hazards)

    base_points = tile_count * 10
    resolution_points = sum(max(0, int(value) - 1) * 8 for value in resolutions)
    quality_points = int(tile_count * max(0, avg_quality - 50) / 10)
    variety_points = terrain_variety * 20
    hazard_points = hazard_tiles * 18 + hazard_variety * 25
    resource_points = resource_tiles * 35 + resource_variety * 55
    anomaly_points = anomaly_tiles * 60 + anomaly_variety * 90
    environment_points = sum(environment_tags.values()) * 8 + len(environment_tags) * 25

    factors = {
        "tile_coverage": base_points,
        "resolution": resolution_points,
        "sensor_quality": quality_points,
        "terrain_variety": variety_points,
        "hazards": hazard_points,
        "resources": resource_points,
        "anomalies": anomaly_points,
        "environment": environment_points,
    }
    points = int(sum(factors.values()))
    grade = _value_grade(points)

    tags = []
    if hazard_tiles:
        tags.append("hazard")
    if resource_tiles:
        tags.append("resource")
    if anomaly_tiles:
        tags.append("anomaly")
    if max_resolution >= 3:
        tags.append("high_resolution")
    if terrain_variety >= 4:
        tags.append("terrain_variety")
    if environment_tags:
        tags.append("environmental_extremes")

    notes = [
        f"{tile_count} tile(s), r{min_resolution}-{max_resolution}, average quality {avg_quality}.",
    ]
    if resource_tiles:
        notes.append(f"{resource_tiles} tile(s) contain resource signatures.")
    if anomaly_tiles:
        notes.append(f"{anomaly_tiles} tile(s) contain anomaly candidates.")
    if hazard_tiles:
        notes.append(f"{hazard_tiles} tile(s) carry hazard flags.")
    if max_resolution < 3:
        notes.append("Higher-resolution rescans may improve market value.")

    return {
        "version": DATASET_VALUATION_VERSION,
        "basis": "survey dataset valuation v1",
        "points": points,
        "grade": grade,
        "factors": factors,
        "counts": {
            "tiles": tile_count,
            "min_resolution": min_resolution,
            "max_resolution": max_resolution,
            "avg_quality": avg_quality,
            "terrain_variety": terrain_variety,
            "hazard_tiles": hazard_tiles,
            "hazard_variety": hazard_variety,
            "resource_tiles": resource_tiles,
            "resource_variety": resource_variety,
            "anomaly_tiles": anomaly_tiles,
            "anomaly_variety": anomaly_variety,
            "environment_markers": sum(environment_tags.values()),
        },
        "top": {
            "terrain": terrain.most_common(5),
            "hazards": hazards.most_common(5),
            "resources": resources.most_common(5),
            "anomalies": anomalies.most_common(5),
            "environment": environment_tags.most_common(5),
        },
        "tags": tags,
        "notes": notes,
    }


def dataset_valuation(dataset: SurveyDataset) -> dict[str, Any]:
    """Return stored valuation metadata from a dataset."""
    metadata = dataset.metadata or {}
    valuation = metadata.get("valuation")
    return dict(valuation) if isinstance(valuation, dict) else {}


def format_valuation_brief(dataset: SurveyDataset) -> str:
    """Return compact valuation label for dataset lists."""
    valuation = dataset_valuation(dataset)
    if not valuation:
        return "value unassessed"
    return f"value {_safe_int(valuation.get('points'))} VP, {valuation.get('grade') or 'ungraded'}"


def valuation_detail_lines(dataset: SurveyDataset) -> list[str]:
    """Return player-facing valuation detail lines."""
    valuation = dataset_valuation(dataset)
    if not valuation:
        return ["Valuation: not assessed"]

    lines = [
        f"Valuation: {_safe_int(valuation.get('points'))} VP ({valuation.get('grade') or 'ungraded'})",
    ]

    tags = valuation.get("tags") or []
    if tags:
        lines.append(f"Value tags: {', '.join(str(tag) for tag in tags)}")

    counts = valuation.get("counts") or {}
    if counts:
        lines.append(
            "Value basis: "
            f"{counts.get('tiles', dataset.tile_count)} tiles, "
            f"r{counts.get('min_resolution', dataset.min_resolution)}-"
            f"{counts.get('max_resolution', dataset.max_resolution)}, "
            f"avg quality {counts.get('avg_quality', 'unknown')}"
        )

    factors = valuation.get("factors") or {}
    if factors:
        lines.append("Value factors:")
        for label, points in sorted(factors.items(), key=lambda item: _safe_int(item[1]), reverse=True):
            factor_points = _safe_int(points)
            if factor_points <= 0:
                continue
            lines.append(f"  {label.replace('_', ' ')}: {factor_points} VP")

    notes = valuation.get("notes") or []
    if notes:
        lines.append("Value notes:")
        for note in notes[:5]:
            lines.append(f"  {note}")

    return lines


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

        merged = _merged_coverage_data(
            obj.data or {},
            data or {},
            current_resolution=current_resolution,
            incoming_resolution=incoming_resolution,
        )
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
    valuation = calculate_dataset_valuation(rows)

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
            },
            "valuation": valuation,
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
def import_dataset_tiles_to_coverage_chunk(
    *,
    dataset: SurveyDataset,
    owner_scope: str,
    owner_id: int,
    source_object_id: int | None = None,
    offset: int = 0,
    limit: int = BULK_DATASET_IMPORT_BATCH_SIZE,
    total_tiles: int | None = None,
) -> dict[str, Any]:
    """
    Import one chunk of a packaged dataset into mutable SurveyCoverage.

    Existing rows are prefetched by group and then written in bulk. This keeps
    large cartridge loads from issuing one query and one save per tile.
    """
    offset = max(0, int(offset or 0))
    limit = max(1, int(limit or BULK_DATASET_IMPORT_BATCH_SIZE))
    total = int(total_tiles) if total_tiles is not None else int(dataset.tiles.count())
    tiles = list(
        dataset.tiles.all()
        .order_by("id")
        .only(
            "id",
            "system_name",
            "body_id",
            "body_name",
            "x",
            "y",
            "scan_type",
            "resolution",
            "quality",
            "data",
        )[offset : offset + limit]
    )

    if not tiles:
        return {
            "dataset_id": int(dataset.id),
            "dataset_name": dataset.name,
            "tile_count": 0,
            "processed_total": offset,
            "next_offset": offset,
            "total_tiles": total,
            "created": 0,
            "updated": 0,
            "merged": 0,
            "done": True,
            "summary": _summarize_dataset_tile_batch([]),
        }

    bounds_by_group: dict[tuple[str, str, str], dict[str, int]] = {}
    for tile in tiles:
        group_key = (str(tile.system_name), str(tile.body_id), str(tile.scan_type))
        bounds = bounds_by_group.setdefault(
            group_key,
            {
                "x_min": int(tile.x),
                "x_max": int(tile.x),
                "y_min": int(tile.y),
                "y_max": int(tile.y),
            },
        )
        bounds["x_min"] = min(bounds["x_min"], int(tile.x))
        bounds["x_max"] = max(bounds["x_max"], int(tile.x))
        bounds["y_min"] = min(bounds["y_min"], int(tile.y))
        bounds["y_max"] = max(bounds["y_max"], int(tile.y))

    existing_by_key: dict[tuple[str, str, int, int, str], SurveyCoverage] = {}
    for (system_name, body_id, scan_type), bounds in bounds_by_group.items():
        rows = SurveyCoverage.objects.filter(
            owner_scope=owner_scope,
            owner_id=int(owner_id),
            system_name=system_name,
            body_id=body_id,
            scan_type=scan_type,
            x__gte=bounds["x_min"],
            x__lte=bounds["x_max"],
            y__gte=bounds["y_min"],
            y__lte=bounds["y_max"],
        ).only(
            "id",
            "system_name",
            "body_id",
            "body_name",
            "x",
            "y",
            "scan_type",
            "resolution",
            "quality",
            "source_ship_id",
            "source_object_id",
            "data",
            "first_scanned_at",
            "last_scanned_at",
        )
        for row in rows:
            existing_by_key[_coverage_key(row.system_name, row.body_id, row.x, row.y, row.scan_type)] = row

    created = 0
    updated = 0
    now = timezone.now()
    create_rows: list[SurveyCoverage] = []
    update_rows: list[SurveyCoverage] = []

    for tile in tiles:
        data = dict(tile.data or {})
        data.update(
            {
                "loaded_from_dataset_id": int(dataset.id),
                "loaded_from_dataset_name": dataset.name,
                "loaded_from_cartridge_object_id": source_object_id,
                "loaded_via": "survey_data_cartridge",
            }
        )

        key = _coverage_key(tile.system_name, tile.body_id, tile.x, tile.y, tile.scan_type)
        existing = existing_by_key.get(key)
        incoming_resolution = int(tile.resolution or 0)
        incoming_quality = int(tile.quality or 0)
        body_name = tile.body_name or dataset.body_name or ""

        if existing is None:
            create_rows.append(
                SurveyCoverage(
                    owner_scope=owner_scope,
                    owner_id=int(owner_id),
                    system_name=tile.system_name,
                    body_id=tile.body_id,
                    body_name=body_name,
                    x=int(tile.x),
                    y=int(tile.y),
                    scan_type=tile.scan_type,
                    resolution=incoming_resolution,
                    quality=incoming_quality,
                    source_ship_id=dataset.source_ship_id,
                    source_object_id=source_object_id,
                    data=data,
                    first_scanned_at=now,
                    last_scanned_at=now,
                )
            )
            created += 1
            continue

        current_resolution = int(existing.resolution or 0)
        existing.resolution = max(current_resolution, incoming_resolution)
        existing.quality = max(int(existing.quality or 0), incoming_quality)
        existing.data = _merged_coverage_data(
            existing.data or {},
            data,
            current_resolution=current_resolution,
            incoming_resolution=incoming_resolution,
        )
        if body_name:
            existing.body_name = body_name
        if dataset.source_ship_id:
            existing.source_ship_id = dataset.source_ship_id
        if source_object_id is not None:
            existing.source_object_id = source_object_id
        existing.last_scanned_at = now
        update_rows.append(existing)
        updated += 1

    if create_rows:
        SurveyCoverage.objects.bulk_create(create_rows, batch_size=BULK_DATASET_IMPORT_BATCH_SIZE)

    if update_rows:
        SurveyCoverage.objects.bulk_update(
            update_rows,
            [
                "body_name",
                "resolution",
                "quality",
                "source_ship_id",
                "source_object_id",
                "data",
                "last_scanned_at",
            ],
            batch_size=BULK_DATASET_IMPORT_BATCH_SIZE,
        )

    next_offset = offset + len(tiles)

    return {
        "dataset_id": int(dataset.id),
        "dataset_name": dataset.name,
        "tile_count": len(tiles),
        "processed_total": next_offset,
        "next_offset": next_offset,
        "total_tiles": total,
        "created": created,
        "updated": updated,
        "merged": updated,
        "done": next_offset >= total,
        "summary": _summarize_dataset_tile_batch(tiles),
    }


def _list_payload_values(data: dict[str, Any], *keys: str) -> list[str]:
    """Return normalized string values from a scalar or list payload field."""
    for key in keys:
        value = data.get(key)
        if not value:
            continue
        values = value if isinstance(value, (list, tuple, set)) else [value]
        result = [
            str(item)
            for item in values
            if item is not None and item != "" and str(item).lower() != "none"
        ]
        if result:
            return result
    return []


def _summarize_dataset_tile_batch(tiles: Iterable[SurveyDatasetTile]) -> dict[str, Any]:
    """Return compact player-facing content summary for an imported batch."""
    terrain = Counter()
    hazards = Counter()
    resources = Counter()
    anomalies = Counter()
    resolutions: list[int] = []

    for tile in tiles:
        data = dict(tile.data or {})
        label = (
            data.get("terrain")
            or data.get("terrain_label")
            or data.get("terrain_name")
            or data.get("scan_type")
            or tile.scan_type
        )
        if label:
            terrain[str(label).lower()] += 1

        for hazard in _list_payload_values(data, "hazards", "hazard"):
            hazards[hazard] += 1

        for resource in _list_payload_values(data, "resource_signatures", "resources"):
            resources[resource] += 1

        for anomaly in _list_payload_values(data, "anomaly_signatures", "anomalies"):
            anomalies[anomaly] += 1

        try:
            resolutions.append(int(tile.resolution or 0))
        except Exception:
            pass

    return {
        "terrain": terrain.most_common(4),
        "hazards": hazards.most_common(4),
        "resources": resources.most_common(4),
        "anomalies": anomalies.most_common(4),
        "min_resolution": min(resolutions) if resolutions else 0,
        "max_resolution": max(resolutions) if resolutions else 0,
    }


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

    This compatibility path still completes synchronously, but it uses chunked
    bulk writes internally. Player commands should prefer the timed cartridge
    load operation so large imports become visible in-game progress.
    """
    total = int(dataset.tiles.count())
    offset = 0
    aggregate = {
        "dataset_id": int(dataset.id),
        "dataset_name": dataset.name,
        "tile_count": 0,
        "created": 0,
        "updated": 0,
        "merged": 0,
    }

    while offset < total:
        result = import_dataset_tiles_to_coverage_chunk(
            dataset=dataset,
            owner_scope=owner_scope,
            owner_id=int(owner_id),
            source_object_id=source_object_id,
            offset=offset,
            limit=BULK_DATASET_IMPORT_BATCH_SIZE,
            total_tiles=total,
        )
        aggregate["tile_count"] += int(result["tile_count"])
        aggregate["created"] += int(result["created"])
        aggregate["updated"] += int(result["updated"])
        aggregate["merged"] += int(result["merged"])
        offset = int(result["next_offset"])

    return aggregate


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
            f"{dataset.scan_type}, {format_valuation_brief(dataset)}]"
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

    lines.append("")
    lines.extend(valuation_detail_lines(dataset))

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
        f"({dataset.tile_count} tiles, {format_valuation_brief(dataset)})."
    )
