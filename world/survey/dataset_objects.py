"""
Helpers for tangible survey data cartridge objects.
"""

from __future__ import annotations

from typing import Any

from evennia.utils.create import create_object  # type: ignore

from world.survey.models import SurveyDataset
from world.survey.services import (
    actor_owner_key,
    import_dataset_tiles_to_coverage,
    render_dataset_detail,
)


SURVEY_CARTRIDGE_TYPECLASS = "world.survey.objects.SurveyDataCartridge"
SURVEY_CARTRIDGE_TAG = "survey_data_cartridge"
SURVEY_CARTRIDGE_TAG_CATEGORY = "survey"

SURVEY_DATASET_ID_ATTR = "survey_dataset_id"
LEGACY_DATASET_ID_ATTR = "dataset_id"


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
        f"#{dataset.id}."
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

    lines = ["Survey data cartridges:"]
    for obj in cartridges:
        dataset = get_dataset_for_cartridge(obj)
        if dataset is None:
            dataset_id = get_cartridge_dataset_id(obj)
            lines.append(f"  {obj.key} ({obj.dbref}) [missing dataset #{dataset_id}]")
            continue

        lines.append(
            f"  {obj.key} ({obj.dbref}) "
            f"[dataset #{dataset.id}, {dataset.tile_count} tiles, "
            f"r{dataset.min_resolution}-{dataset.max_resolution}, {dataset.scan_type}]"
        )

    return "\n".join(lines)


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
        return "Usage: survey load <cartridge>"

    cartridge = find_inventory_cartridge(caller, query)
    if cartridge is None:
        return f"You are not carrying a survey data cartridge matching '{query}'."

    dataset = get_dataset_for_cartridge(cartridge)
    if dataset is None:
        dataset_id = get_cartridge_dataset_id(cartridge)
        return f"That cartridge references missing survey dataset #{dataset_id}."

    owner_scope, owner_id = actor_owner_key(caller)
    result = import_dataset_tiles_to_coverage(
        dataset=dataset,
        owner_scope=owner_scope,
        owner_id=int(owner_id),
        source_object_id=getattr(cartridge, "id", None),
    )

    return (
        f"Loaded survey dataset #{result['dataset_id']}: {result['dataset_name']} "
        f"from {getattr(cartridge, 'key', 'survey data cartridge')}. "
        f"{result['tile_count']} tiles processed "
        f"({result['created']} new, {result['updated']} existing updated/merged)."
    )
