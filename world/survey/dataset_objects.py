"""
Helpers for tangible survey data cartridge objects.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from evennia.utils.create import create_object  # type: ignore

from world.survey.models import SurveyDataset
from world.survey.services import (
    BULK_DATASET_IMPORT_BATCH_SIZE,
    actor_owner_key,
    format_valuation_brief,
    import_dataset_tiles_to_coverage_chunk,
    render_dataset_detail,
    valuation_detail_lines,
)


SURVEY_CARTRIDGE_TYPECLASS = "world.survey.objects.SurveyDataCartridge"
SURVEY_CARTRIDGE_TAG = "survey_data_cartridge"
SURVEY_CARTRIDGE_TAG_CATEGORY = "survey"

SURVEY_DATASET_ID_ATTR = "survey_dataset_id"
LEGACY_DATASET_ID_ATTR = "dataset_id"
SURVEY_LOAD_OPERATION_ATTR = "survey_cartridge_load_operation"
SURVEY_LOAD_SCRIPT_KEY = "survey_cartridge_load_timer"
SURVEY_LOAD_SCRIPT_PATH = "world.survey.scripts.SurveyCartridgeLoadScript"
SURVEY_LOAD_INTERVAL_SECONDS = 3
SURVEY_LOAD_CHUNK_SIZE = BULK_DATASET_IMPORT_BATCH_SIZE


def _to_int(value: Any) -> int | None:
    """Best-effort int conversion."""
    try:
        return int(value)
    except Exception:
        return None


def _dbref(obj: Any) -> str:
    """Return Evennia dbref if available."""
    return str(getattr(obj, "dbref", "") or "")


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Read an Evennia AttributeHandler value safely."""
    try:
        return obj.attributes.get(name, default=default)
    except Exception:
        try:
            return getattr(obj.db, name)
        except Exception:
            return default


def _set_attr(obj: Any, name: str, value: Any) -> None:
    """Write an Evennia AttributeHandler value safely."""
    try:
        obj.attributes.add(name, value)
    except Exception:
        try:
            setattr(obj.db, name, value)
        except Exception:
            pass


def get_cartridge_dataset_id(obj: Any) -> int | None:
    """
    Return the SurveyDataset id linked to an object, if any.
    """
    dataset_id = _to_int(_get_attr(obj, SURVEY_DATASET_ID_ATTR))
    if dataset_id is not None:
        return dataset_id

    return _to_int(_get_attr(obj, LEGACY_DATASET_ID_ATTR))


def get_dataset_for_cartridge(obj: Any) -> SurveyDataset | None:
    """
    Return SurveyDataset linked to a cartridge object.
    """
    dataset_id = get_cartridge_dataset_id(obj)
    if dataset_id is None:
        return None

    try:
        return SurveyDataset.objects.get(id=int(dataset_id))
    except SurveyDataset.DoesNotExist:
        return None


def is_survey_data_cartridge(obj: Any) -> bool:
    """
    Return whether an object is a survey data cartridge.
    """
    if obj is None:
        return False

    try:
        if obj.tags.has(SURVEY_CARTRIDGE_TAG, category=SURVEY_CARTRIDGE_TAG_CATEGORY):
            return True
    except Exception:
        pass

    if _get_attr(obj, "item_type") == "survey_data_cartridge":
        return True

    return get_cartridge_dataset_id(obj) is not None


def _cartridge_key(dataset: SurveyDataset) -> str:
    """Return standard cartridge object key for a dataset."""
    return f"Survey Data Cartridge: {dataset.name}"


def _update_cartridge_metadata(obj: Any, dataset: SurveyDataset, creator: Any = None) -> None:
    """Store dataset metadata on an object."""
    _set_attr(obj, SURVEY_DATASET_ID_ATTR, int(dataset.id))
    _set_attr(obj, LEGACY_DATASET_ID_ATTR, int(dataset.id))
    _set_attr(obj, "survey_dataset_name", dataset.name)
    _set_attr(obj, "survey_dataset_body", f"{dataset.system_name}/{dataset.body_name or dataset.body_id}")
    _set_attr(obj, "survey_dataset_scan_type", dataset.scan_type)
    _set_attr(obj, "survey_dataset_tile_count", int(dataset.tile_count or 0))
    _set_attr(obj, "survey_dataset_value", format_valuation_brief(dataset))

    if creator is not None:
        try:
            _set_attr(obj, "materialized_by_id", int(creator.id))
        except Exception:
            pass

    try:
        obj.tags.add(SURVEY_CARTRIDGE_TAG, category=SURVEY_CARTRIDGE_TAG_CATEGORY)
    except Exception:
        pass

    obj.db.desc = (
        f"A compact survey data cartridge containing '{dataset.name}'. "
        f"The dataset covers {dataset.tile_count} tile(s) on "
        f"{dataset.system_name}/{dataset.body_name or dataset.body_id}."
    )


def materialize_dataset_cartridge(caller: Any, dataset_id: int) -> str:
    """
    Create a physical cartridge in caller inventory for an owned SurveyDataset.

    This does not delete or transfer the digital SurveyDataset record. It creates
    one tangible wrapper object that can later be traded, sold, stored, or loaded.
    """
    owner_scope, owner_id = actor_owner_key(caller)

    try:
        dataset = SurveyDataset.objects.get(
            id=int(dataset_id),
            owner_scope=owner_scope,
            owner_id=int(owner_id),
        )
    except SurveyDataset.DoesNotExist:
        return f"No owned survey dataset #{dataset_id} was found."

    if not dataset.is_copyable:
        existing = [
            obj
            for obj in getattr(caller, "contents", [])
            if is_survey_data_cartridge(obj) and get_cartridge_dataset_id(obj) == int(dataset.id)
        ]
        if existing:
            return (
                f"Dataset #{dataset.id} is not copyable, and you already have "
                "a cartridge for it."
            )

    location = caller
    try:
        home = caller.home or caller.location or caller
    except Exception:
        home = caller

    cartridge = create_object(
        SURVEY_CARTRIDGE_TYPECLASS,
        key=_cartridge_key(dataset),
        location=location,
        home=home,
    )

    try:
        cartridge.aliases.add(f"dataset {dataset.id}")
        cartridge.aliases.add(f"survey dataset {dataset.id}")
        cartridge.aliases.add(f"cartridge {dataset.id}")
        cartridge.aliases.add(str(dataset.id))
    except Exception:
        pass

    _update_cartridge_metadata(cartridge, dataset, creator=caller)

    return (
        f"Created {cartridge.key} ({cartridge.dbref}) for survey dataset "
        f"#{dataset.id} ({format_valuation_brief(dataset)})."
    )


def _iter_inventory_cartridges(caller: Any):
    """Yield survey cartridges in caller inventory."""
    for obj in list(getattr(caller, "contents", []) or []):
        if is_survey_data_cartridge(obj):
            yield obj


def render_cartridge_list(caller: Any) -> str:
    """Render survey cartridges currently carried by caller."""
    cartridges = list(_iter_inventory_cartridges(caller))

    if not cartridges:
        return "You are not carrying any survey data cartridges."

    dataset_ids = []
    cartridge_dataset_ids = []
    for obj in cartridges:
        dataset_id = get_cartridge_dataset_id(obj)
        cartridge_dataset_ids.append((obj, dataset_id))
        if dataset_id is not None:
            dataset_ids.append(int(dataset_id))

    datasets = SurveyDataset.objects.in_bulk(dataset_ids) if dataset_ids else {}

    lines = ["Survey data cartridges:"]
    for obj, dataset_id in cartridge_dataset_ids:
        dataset = datasets.get(int(dataset_id)) if dataset_id is not None else None
        if dataset is None:
            lines.append(f"  {obj.key} ({obj.dbref}) [missing dataset #{dataset_id}]")
            continue

        lines.append(
            f"  {obj.key} ({obj.dbref}) "
            f"[dataset #{dataset.id}, {dataset.tile_count} tiles, "
            f"r{dataset.min_resolution}-{dataset.max_resolution}, "
            f"{dataset.scan_type}, {format_valuation_brief(dataset)}]"
        )

    return "\n".join(lines)


def _read_load_operation(caller: Any) -> dict[str, Any]:
    """Read caller's active cartridge load operation."""
    try:
        raw = caller.attributes.get(SURVEY_LOAD_OPERATION_ATTR)
    except Exception:
        raw = None
    return dict(raw) if isinstance(raw, Mapping) else {}


def _write_load_operation(caller: Any, operation: dict[str, Any]) -> None:
    """Persist caller's active cartridge load operation."""
    caller.attributes.add(SURVEY_LOAD_OPERATION_ATTR, dict(operation))


def _clear_load_operation(caller: Any) -> None:
    """Clear caller's active cartridge load operation."""
    try:
        caller.attributes.remove(SURVEY_LOAD_OPERATION_ATTR)
    except Exception:
        pass


def _get_load_scripts(caller: Any) -> list[Any]:
    """Return active cartridge load timer scripts attached to caller."""
    try:
        scripts = caller.scripts.get(key=SURVEY_LOAD_SCRIPT_KEY)
    except Exception:
        return []

    if not scripts:
        return []
    if isinstance(scripts, (list, tuple)):
        return list(scripts)
    try:
        return list(scripts)
    except Exception:
        return [scripts]


def _stop_load_timer(caller: Any) -> None:
    """Stop all cartridge load timer scripts attached to caller."""
    for script in _get_load_scripts(caller):
        try:
            script.stop()
        except Exception:
            pass


def _start_load_timer(caller: Any) -> str:
    """Start or restart the cartridge load timer."""
    _stop_load_timer(caller)
    try:
        from evennia.utils.create import create_script  # type: ignore

        script = create_script(
            SURVEY_LOAD_SCRIPT_PATH,
            key=SURVEY_LOAD_SCRIPT_KEY,
            obj=caller,
            interval=SURVEY_LOAD_INTERVAL_SECONDS,
            start_delay=True,
            persistent=True,
            autostart=True,
        )
        script.interval = SURVEY_LOAD_INTERVAL_SECONDS
        script.start_delay = True
        script.persistent = True
        return ""
    except Exception as err:
        return f"Could not start survey cartridge load timer: {err}"


def _format_common(values: list[tuple[str, int]], *, limit: int = 3) -> str:
    """Format counted summary values."""
    if not values:
        return ""
    shown = [f"{label} ({count})" for label, count in values[:limit]]
    if len(values) > limit:
        shown.append(f"+{len(values) - limit} more")
    return ", ".join(shown)


def _format_load_operation(operation: dict[str, Any]) -> str:
    """Render active cartridge load status."""
    if not operation:
        return "No active survey cartridge load operation."

    total = int(operation.get("total_tiles") or 0)
    processed = int(operation.get("processed") or 0)
    percent = int((processed / total) * 100) if total else 100
    status = str(operation.get("status") or "running")

    return "\n".join(
        [
            "Survey cartridge load operation",
            f"  Status: {status}",
            f"  Dataset: #{operation.get('dataset_id')} {operation.get('dataset_name')}",
            f"  Cartridge: {operation.get('cartridge_key')}",
            f"  Progress: {processed}/{total} tiles ({percent}%)",
            f"  Coverage writes: {operation.get('created', 0)} new, {operation.get('updated', 0)} merged",
            f"  Chunk size: {operation.get('chunk_size', SURVEY_LOAD_CHUNK_SIZE)} tiles",
        ]
    )


def _format_load_step_message(operation: dict[str, Any], result: dict[str, Any]) -> str:
    """Render one player-facing cartridge decode progress message."""
    total = int(result.get("total_tiles") or operation.get("total_tiles") or 0)
    processed = int(result.get("processed_total") or operation.get("processed") or 0)
    chunk_count = int(result.get("tile_count") or 0)
    start = max(1, processed - chunk_count + 1) if chunk_count else processed
    percent = int((processed / total) * 100) if total else 100
    summary = result.get("summary") or {}

    lines = [
        "Survey cartridge upload: decoding data block.",
        f"Dataset #{operation.get('dataset_id')}: {operation.get('dataset_name')}",
        f"Tiles {start}-{processed} of {total} committed ({percent}%).",
        f"Coverage writes this block: {result.get('created', 0)} new, {result.get('updated', 0)} merged.",
    ]

    min_res = int(summary.get("min_resolution") or 0)
    max_res = int(summary.get("max_resolution") or 0)
    if min_res or max_res:
        if min_res == max_res:
            lines.append(f"Resolution stream: r{max_res}.")
        else:
            lines.append(f"Resolution stream: r{min_res}-r{max_res}.")

    terrain = _format_common(summary.get("terrain") or [])
    if terrain:
        lines.append(f"Terrain decoded: {terrain}.")

    hazards = _format_common(summary.get("hazards") or [])
    if hazards:
        lines.append(f"Hazard flags: {hazards}.")

    resources = _format_common(summary.get("resources") or [])
    if resources:
        lines.append(f"Resource signatures: {resources}.")

    anomalies = _format_common(summary.get("anomalies") or [])
    if anomalies:
        lines.append(f"Anomaly candidates: {anomalies}.")

    if result.get("done"):
        lines.append(
            f"Cartridge load complete: {operation.get('created', 0)} new, "
            f"{operation.get('updated', 0)} merged total."
        )
    else:
        lines.append("Cartridge buffer advances to the next data block.")

    return "\n".join(lines)


def _perform_load_step(caller: Any) -> tuple[str, bool]:
    """Process one cartridge load chunk. Return message and keep-running flag."""
    operation = _read_load_operation(caller)
    if not operation:
        return "No active survey cartridge load operation.", False

    if operation.get("status") != "running":
        return "", False

    try:
        dataset = SurveyDataset.objects.get(id=int(operation.get("dataset_id")))
    except SurveyDataset.DoesNotExist:
        _clear_load_operation(caller)
        return f"Survey cartridge load stopped: missing dataset #{operation.get('dataset_id')}.", False

    result = import_dataset_tiles_to_coverage_chunk(
        dataset=dataset,
        owner_scope=str(operation.get("owner_scope")),
        owner_id=int(operation.get("owner_id")),
        source_object_id=operation.get("source_object_id"),
        offset=int(operation.get("next_offset") or 0),
        limit=int(operation.get("chunk_size") or SURVEY_LOAD_CHUNK_SIZE),
        total_tiles=int(operation.get("total_tiles") or dataset.tile_count or dataset.tiles.count()),
    )

    operation["next_offset"] = int(result.get("next_offset") or 0)
    operation["processed"] = int(result.get("processed_total") or operation["next_offset"])
    operation["created"] = int(operation.get("created") or 0) + int(result.get("created") or 0)
    operation["updated"] = int(operation.get("updated") or 0) + int(result.get("updated") or 0)
    operation["merged"] = int(operation.get("merged") or 0) + int(result.get("merged") or 0)
    operation["updated_at"] = int(time.time())

    done = bool(result.get("done"))
    if done:
        operation["status"] = "complete"

    message = _format_load_step_message(operation, result)

    if done:
        _clear_load_operation(caller)
        return message, False

    _write_load_operation(caller, operation)
    return message, True


def run_survey_cartridge_load_tick(caller: Any) -> tuple[str, bool]:
    """Run one timed cartridge load tick for a Script."""
    return _perform_load_step(caller)


def _matches_object_query(obj: Any, query: str) -> bool:
    """Return whether an inventory object matches a loose user query."""
    q = (query or "").strip().lower()
    if not q:
        return False

    dbref = _dbref(obj).lower()
    if q == dbref or q == dbref.lstrip("#"):
        return True

    obj_id = getattr(obj, "id", None)
    if obj_id is not None and q == str(obj_id):
        return True

    key = str(getattr(obj, "key", "") or "").lower()
    if q == key or q in key:
        return True

    try:
        aliases = [str(alias).lower() for alias in obj.aliases.all()]
        if q in aliases:
            return True
    except Exception:
        pass

    dataset_id = get_cartridge_dataset_id(obj)
    if dataset_id is not None and q in {str(dataset_id), f"dataset {dataset_id}", f"cartridge {dataset_id}"}:
        return True

    return False


def find_inventory_cartridge(caller: Any, query: str):
    """
    Resolve a survey cartridge from caller inventory.
    """
    matches = [obj for obj in _iter_inventory_cartridges(caller) if _matches_object_query(obj, query)]

    if not matches:
        return None

    return matches[0]


def render_dataset_record_detail(dataset: SurveyDataset, *, cartridge: Any = None) -> str:
    """
    Render a SurveyDataset without applying owner filtering.

    Use this only after access has already been established, such as:
        - caller owns the digital dataset
        - caller is carrying a cartridge linked to the dataset
    """
    if cartridge is not None:
        lines = [
            f"Survey Data Cartridge: {dataset.name}",
            f"  Object: {getattr(cartridge, 'dbref', '—')}",
            f"  Dataset: #{dataset.id}",
        ]
    else:
        lines = [f"Survey Dataset #{dataset.id}: {dataset.name}"]

    lines.extend(
        [
            f"  Body: {dataset.system_name}/{dataset.body_name or dataset.body_id}",
            f"  Scan type: {dataset.scan_type}",
            f"  Tiles: {dataset.tile_count}",
            f"  Resolution: {dataset.min_resolution}-{dataset.max_resolution}",
            f"  Integrity: {dataset.integrity}%",
            f"  Transferable: {'yes' if dataset.is_transferable else 'no'}",
            f"  Copyable: {'yes' if dataset.is_copyable else 'no'}",
            f"  License: {dataset.license_mode}",
        ]
    )

    lines.append("")
    lines.extend(valuation_detail_lines(dataset))

    if dataset.description:
        lines.append("")
        lines.append(dataset.description)

    return "\n".join(lines)


def render_cartridge_detail(cartridge: Any, *, looker: Any = None) -> str:
    """
    Render cartridge appearance/detail.
    """
    dataset = get_dataset_for_cartridge(cartridge)
    if dataset is None:
        dataset_id = get_cartridge_dataset_id(cartridge)
        return (
            f"{getattr(cartridge, 'key', 'Survey Data Cartridge')}\n"
            f"This survey data cartridge references missing dataset #{dataset_id}."
        )

    return render_dataset_record_detail(dataset, cartridge=cartridge)


def render_dataset_or_cartridge_detail(
    caller: Any,
    query: str,
    *,
    viewer_scope: str,
    viewer_id: int,
) -> str:
    """
    Inspect either:
        - an owned digital dataset by id
        - a carried survey data cartridge by name/dbref/alias
    """
    query = (query or "").strip()
    if not query:
        return "Usage: survey inspect <dataset id or cartridge>"

    numeric = query.lstrip("#").isdigit()
    if numeric:
        return render_dataset_detail(
            int(query.lstrip("#")),
            viewer_scope=viewer_scope,
            viewer_id=int(viewer_id),
        )

    cartridge = find_inventory_cartridge(caller, query)
    if cartridge is None:
        return f"No owned dataset or carried survey data cartridge matching '{query}' was found."

    return render_cartridge_detail(cartridge, looker=caller)


def load_cartridge_into_coverage(caller: Any, query: str) -> str:
    """
    Load a carried survey data cartridge into caller's SurveyCoverage.

    This imports dataset tile snapshots as mutable owner coverage. The cartridge
    is not consumed.
    """
    query = (query or "").strip()
    if not query:
        return "Usage: survey load <cartridge>, survey load status, or survey load cancel"

    action = query.lower()
    if action in {"status", "progress"}:
        return _format_load_operation(_read_load_operation(caller))

    if action in {"cancel", "stop", "clear"}:
        if not _read_load_operation(caller):
            return "No active survey cartridge load operation."
        _stop_load_timer(caller)
        _clear_load_operation(caller)
        return "Cancelled active survey cartridge load operation."

    existing_operation = _read_load_operation(caller)
    if existing_operation:
        return (
            "A survey cartridge load is already running.\n"
            + _format_load_operation(existing_operation)
            + "\nUse survey load status or survey load cancel."
        )

    cartridge = find_inventory_cartridge(caller, query)
    if cartridge is None:
        return f"You are not carrying a survey data cartridge matching '{query}'."

    dataset = get_dataset_for_cartridge(cartridge)
    if dataset is None:
        dataset_id = get_cartridge_dataset_id(cartridge)
        return f"That cartridge references missing survey dataset #{dataset_id}."

    owner_scope, owner_id = actor_owner_key(caller)
    total_tiles = int(dataset.tile_count or dataset.tiles.count())
    if total_tiles <= 0:
        return f"Survey dataset #{dataset.id}: {dataset.name} contains no tiles to load."

    operation = {
        "status": "running",
        "dataset_id": int(dataset.id),
        "dataset_name": dataset.name,
        "cartridge_key": getattr(cartridge, "key", "survey data cartridge"),
        "source_object_id": getattr(cartridge, "id", None),
        "owner_scope": owner_scope,
        "owner_id": int(owner_id),
        "next_offset": 0,
        "processed": 0,
        "total_tiles": total_tiles,
        "chunk_size": SURVEY_LOAD_CHUNK_SIZE,
        "created": 0,
        "updated": 0,
        "merged": 0,
        "started_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    _write_load_operation(caller, operation)

    message, keep_running = _perform_load_step(caller)
    if not keep_running:
        _stop_load_timer(caller)
        return message

    timer_error = _start_load_timer(caller)
    if timer_error:
        operation = _read_load_operation(caller)
        operation["status"] = "paused"
        operation["last_error"] = timer_error
        _write_load_operation(caller, operation)
        return message + "\n" + timer_error

    operation = _read_load_operation(caller)
    progress = _format_load_operation(operation)

    return message + "\n\n" + progress
