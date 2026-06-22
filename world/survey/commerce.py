"""
Survey data commerce helpers.

V1 supports builder-marked NPC exchanges and short-lived room-based P2P offers.
Persistent public listings can build on the same offer/transaction records later.
"""

from __future__ import annotations

import math
import shlex
from collections import Counter
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from world.player.credits import format_credits, get_credits, grant_credits, spend_credits
from world.survey.models import (
    OWNER_NPC_MARKET,
    SurveyCopyEvent,
    SurveyDataset,
    SurveyDatasetTile,
    SurveyMarketTransaction,
    SurveyTradeOffer,
)
from world.survey.services import actor_owner_key, dataset_valuation


SURVEY_EXCHANGE_ATTR = "survey_exchange"
OFFER_EXPIRY_MINUTES = 15
NPC_MARKET_OWNER_ID_DEFAULT = 0

GRADE_BANDS = {
    "routine": (100, 300, 0, 299),
    "useful": (500, 1500, 300, 899),
    "valuable": (2500, 6000, 900, 1999),
    "exceptional": (10000, 25000, 2000, 5000),
}


def _obj_id(obj: Any) -> int | None:
    value = getattr(obj, "id", None) or getattr(obj, "dbid", None)
    try:
        return int(value)
    except Exception:
        return None


def _actor_name(actor: Any) -> str:
    return str(getattr(actor, "key", None) or getattr(actor, "name", None) or actor or "")


def _room_id(actor: Any) -> int | None:
    try:
        return _obj_id(actor.location)
    except Exception:
        return None


def _read_attr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return obj.attributes.get(name, default=default)
    except Exception:
        try:
            return getattr(obj.db, name)
        except Exception:
            return default


def _write_attr(obj: Any, name: str, value: Any) -> None:
    try:
        obj.attributes.add(name, value)
    except Exception:
        try:
            setattr(obj.db, name, value)
        except Exception:
            pass


def _remove_attr(obj: Any, name: str) -> None:
    try:
        obj.attributes.remove(name)
    except Exception:
        try:
            delattr(obj.db, name)
        except Exception:
            pass


def _tokenize(text: str) -> list[str]:
    try:
        return shlex.split(text or "", comments=False, posix=True)
    except ValueError:
        return (text or "").split()


def _object_from_id(object_id: int | None):
    if object_id is None:
        return None
    try:
        from evennia.objects.models import ObjectDB  # type: ignore

        return ObjectDB.objects.get(id=int(object_id))
    except Exception:
        return None


def _matches_actor(obj: Any, query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return False

    dbref = str(getattr(obj, "dbref", "") or "").lower()
    if q == dbref or q == dbref.lstrip("#"):
        return True

    obj_id = _obj_id(obj)
    if obj_id is not None and q == str(obj_id):
        return True

    key = str(getattr(obj, "key", "") or "").lower()
    if q == key:
        return True

    try:
        aliases = [str(alias).lower() for alias in obj.aliases.all()]
        return q in aliases
    except Exception:
        return False


def find_character_in_room(caller: Any, query: str):
    """Resolve a nearby character/player object from caller's room."""
    try:
        contents = list(caller.location.contents or [])
    except Exception:
        contents = []

    for obj in contents:
        if obj is caller:
            continue
        if _matches_actor(obj, query):
            return obj
    return None


def set_exchange_room(caller: Any, name: str) -> str:
    """Mark caller's current room as an NPC survey exchange."""
    room = getattr(caller, "location", None)
    if room is None:
        return "You are nowhere."

    clean_name = (name or "").strip() or "Survey Exchange"
    room_id = _obj_id(room) or NPC_MARKET_OWNER_ID_DEFAULT
    data = {
        "enabled": True,
        "name": clean_name,
        "exchange_key": f"room-{room_id}",
        "set_by": _actor_name(caller),
        "set_by_id": _obj_id(caller),
        "set_at": timezone.now().isoformat(),
    }
    _write_attr(room, SURVEY_EXCHANGE_ATTR, data)
    return f"Marked this room as survey exchange '{clean_name}'."


def clear_exchange_room(caller: Any) -> str:
    """Remove the NPC survey exchange marker from caller's current room."""
    room = getattr(caller, "location", None)
    if room is None:
        return "You are nowhere."
    _remove_attr(room, SURVEY_EXCHANGE_ATTR)
    return "Cleared the survey exchange marker from this room."


def get_exchange_context(caller: Any) -> dict[str, Any] | None:
    """Return current room exchange metadata, if enabled."""
    room = getattr(caller, "location", None)
    if room is None:
        return None

    raw = _read_attr(room, SURVEY_EXCHANGE_ATTR)
    if not isinstance(raw, Mapping) or not raw.get("enabled"):
        return None

    data = dict(raw)
    data.setdefault("name", "Survey Exchange")
    data.setdefault("exchange_key", f"room-{_obj_id(room) or 0}")
    data["room_id"] = _obj_id(room)
    return data


def handle_survey_exchange_admin_command(caller: Any, args: str, switches: list[str] | None = None) -> str:
    """Handle @surveyexchange builder command."""
    switches = switches or []
    if "clear" in switches:
        return clear_exchange_room(caller)
    return set_exchange_room(caller, args)


def _metadata(dataset: SurveyDataset) -> dict[str, Any]:
    return dict(dataset.metadata or {})


def ensure_dataset_lineage(dataset: SurveyDataset, source_dataset: SurveyDataset | None = None) -> dict[str, Any]:
    """Ensure dataset has lineage metadata and return it."""
    metadata = _metadata(dataset)
    lineage = dict(metadata.get("lineage") or {})
    source_lineage = dict((source_dataset.metadata or {}).get("lineage") or {}) if source_dataset else {}

    root_dataset_id = (
        lineage.get("root_dataset_id")
        or source_lineage.get("root_dataset_id")
        or (source_dataset.id if source_dataset is not None else dataset.id)
    )
    source_dataset_id = lineage.get("source_dataset_id")
    if source_dataset is not None:
        source_dataset_id = source_dataset.id
    elif not source_dataset_id:
        source_dataset_id = None

    changed = False
    if lineage.get("root_dataset_id") != root_dataset_id:
        lineage["root_dataset_id"] = int(root_dataset_id)
        changed = True
    if lineage.get("source_dataset_id") != source_dataset_id:
        lineage["source_dataset_id"] = int(source_dataset_id) if source_dataset_id else None
        changed = True

    lineage.setdefault("copy_count", 0)
    lineage.setdefault("copy_breakdown", {"digital_license": 0, "cartridge": 0})
    metadata["lineage"] = lineage

    if changed or metadata != (dataset.metadata or {}):
        dataset.metadata = metadata
        dataset.save(update_fields=["metadata", "updated_at"])

    return lineage


def _lineage_root_id(dataset: SurveyDataset) -> int:
    lineage = ensure_dataset_lineage(dataset)
    return int(lineage.get("root_dataset_id") or dataset.id)


def lineage_copy_summary(dataset: SurveyDataset) -> dict[str, Any]:
    """Return cumulative copy counts for a dataset's lineage."""
    lineage = ensure_dataset_lineage(dataset)
    root_id = int(lineage.get("root_dataset_id") or dataset.id)

    counts = Counter()
    for row in SurveyCopyEvent.objects.filter(root_dataset_id=root_id).values_list("event_type", flat=True):
        counts[str(row)] += 1

    total = sum(counts.values())
    if total <= 0:
        breakdown = lineage.get("copy_breakdown") or {}
        counts.update({str(key): int(value or 0) for key, value in breakdown.items()})
        total = int(lineage.get("copy_count") or sum(counts.values()) or 0)

    return {
        "root_dataset_id": root_id,
        "source_dataset_id": lineage.get("source_dataset_id"),
        "total": int(total),
        "digital_license": int(counts.get(SurveyCopyEvent.EVENT_DIGITAL_LICENSE, 0)),
        "cartridge": int(counts.get(SurveyCopyEvent.EVENT_CARTRIDGE, 0)),
    }


def _sync_lineage_summary(dataset: SurveyDataset) -> dict[str, Any]:
    summary = lineage_copy_summary(dataset)
    metadata = _metadata(dataset)
    lineage = dict(metadata.get("lineage") or {})
    lineage.update(
        {
            "root_dataset_id": int(summary["root_dataset_id"]),
            "source_dataset_id": summary.get("source_dataset_id"),
            "copy_count": int(summary["total"]),
            "copy_breakdown": {
                "digital_license": int(summary["digital_license"]),
                "cartridge": int(summary["cartridge"]),
            },
        }
    )
    metadata["lineage"] = lineage
    if metadata != (dataset.metadata or {}):
        dataset.metadata = metadata
        dataset.save(update_fields=["metadata", "updated_at"])
    return summary


def copy_lineage_detail_lines(dataset: SurveyDataset) -> list[str]:
    """Return player-facing lineage/copy lines."""
    summary = _sync_lineage_summary(dataset)
    lines = [
        "Copy lineage: "
        f"{summary['total']} known copies "
        f"({summary['digital_license']} digital, {summary['cartridge']} cartridge)"
    ]
    if int(summary["root_dataset_id"]) != int(dataset.id):
        lines.append(f"Lineage root: dataset #{summary['root_dataset_id']}")
    if summary.get("source_dataset_id"):
        lines.append(f"Source dataset: #{summary['source_dataset_id']}")
    return lines


def record_copy_event(
    *,
    source_dataset: SurveyDataset,
    event_type: str,
    actor: Any = None,
    object_id: int | None = None,
    copied_dataset: SurveyDataset | None = None,
    transaction_record: SurveyMarketTransaction | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[SurveyCopyEvent, dict[str, Any]]:
    """Record one cumulative copy event and return the new lineage summary."""
    root_id = _lineage_root_id(source_dataset)
    actor_scope = ""
    actor_id = None
    if actor is not None:
        try:
            actor_scope, actor_id = actor_owner_key(actor)
        except Exception:
            actor_scope = ""
            actor_id = _obj_id(actor)

    event = SurveyCopyEvent.objects.create(
        dataset=copied_dataset or source_dataset,
        source_dataset=source_dataset,
        transaction=transaction_record,
        root_dataset_id=root_id,
        event_type=event_type,
        actor_scope=actor_scope,
        actor_id=actor_id,
        object_id=object_id,
        metadata=dict(metadata or {}),
    )

    summary = _sync_lineage_summary(source_dataset)
    root_dataset = SurveyDataset.objects.filter(id=root_id).first()
    if root_dataset is not None and root_dataset.id != source_dataset.id:
        _sync_lineage_summary(root_dataset)
    if copied_dataset is not None:
        _sync_lineage_summary(copied_dataset)
    return event, summary


def _copy_dataset_tiles(source: SurveyDataset, target: SurveyDataset) -> None:
    tiles = [
        SurveyDatasetTile(
            dataset=target,
            system_name=tile.system_name,
            body_id=tile.body_id,
            body_name=tile.body_name,
            x=tile.x,
            y=tile.y,
            scan_type=tile.scan_type,
            resolution=tile.resolution,
            quality=tile.quality,
            data=dict(tile.data or {}),
        )
        for tile in source.tiles.all().order_by("id")
    ]
    if tiles:
        SurveyDatasetTile.objects.bulk_create(tiles)


def create_licensed_dataset_copy(
    *,
    source: SurveyDataset,
    owner_scope: str,
    owner_id: int,
    is_transferable: bool,
    is_copyable: bool,
    license_mode: str,
    transaction_record: SurveyMarketTransaction | None = None,
    actor: Any = None,
) -> SurveyDataset:
    """Create a buyer-owned digital licensed copy of a dataset."""
    source_lineage = ensure_dataset_lineage(source)
    metadata = _metadata(source)
    metadata["lineage"] = {
        "root_dataset_id": int(source_lineage.get("root_dataset_id") or source.id),
        "source_dataset_id": int(source.id),
        "copy_count": 0,
        "copy_breakdown": {"digital_license": 0, "cartridge": 0},
    }
    metadata["licensed_copy"] = {
        "source_dataset_id": int(source.id),
        "created_at": timezone.now().isoformat(),
    }

    copied = SurveyDataset.objects.create(
        name=source.name,
        description=source.description,
        owner_scope=owner_scope,
        owner_id=int(owner_id),
        creator_id=source.creator_id,
        source_ship_id=source.source_ship_id,
        system_name=source.system_name,
        body_id=source.body_id,
        body_name=source.body_name,
        scan_type=source.scan_type,
        min_resolution=source.min_resolution,
        max_resolution=source.max_resolution,
        tile_count=source.tile_count,
        integrity=source.integrity,
        is_transferable=bool(is_transferable),
        is_copyable=bool(is_copyable),
        license_mode=license_mode,
        metadata=metadata,
    )
    _copy_dataset_tiles(source, copied)
    record_copy_event(
        source_dataset=source,
        event_type=SurveyCopyEvent.EVENT_DIGITAL_LICENSE,
        actor=actor,
        copied_dataset=copied,
        transaction_record=transaction_record,
        metadata={"copy_dataset_id": int(copied.id)},
    )
    return copied


def _grade_band_amount(dataset: SurveyDataset) -> tuple[int, str]:
    valuation = dataset_valuation(dataset)
    grade = str(valuation.get("grade") or "routine")
    points = int(valuation.get("points") or 0)
    if grade == "empty" or points <= 0:
        return 0, "empty"

    low, high, point_low, point_high = GRADE_BANDS.get(grade, GRADE_BANDS["routine"])
    if point_high <= point_low:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, (points - point_low) / (point_high - point_low)))
    return int(round(low + ((high - low) * ratio))), grade


def _is_sol_system(dataset: SurveyDataset) -> bool:
    return str(dataset.system_name or "").strip().lower() in {"sol", "solar", "solar system"}


def _body_label(dataset: SurveyDataset) -> str:
    return str(dataset.body_name or dataset.body_id or "").strip().lower()


def _is_earth_dataset(dataset: SurveyDataset) -> bool:
    body = _body_label(dataset)
    return _is_sol_system(dataset) and body in {"earth", "terra", "sol iii", "sol 3"}


def _metadata_distance_ly(value: Any) -> float | None:
    if isinstance(value, dict):
        for key in ("distance_ly", "distance_light_years", "ly_from_sol"):
            if key in value:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    pass
        for nested_key in ("system", "origin", "distance"):
            found = _metadata_distance_ly(value.get(nested_key))
            if found is not None:
                return found
    return None


def _distance_modifier(dataset: SurveyDataset) -> tuple[float, str]:
    body = _body_label(dataset)
    if _is_sol_system(dataset):
        if body in {"luna", "moon", "the moon", "earth moon"}:
            return 1.10, "Luna survey tier"
        if body in {"mercury", "venus", "mars"}:
            return 1.25, "inner planet survey tier"
        return 1.60, "outer planet survey tier"

    distance_ly = _metadata_distance_ly(dataset.metadata or {})
    if distance_ly is None:
        return 1.80, "non-Sol survey tier, distance unknown"
    if distance_ly <= 5:
        return 1.80, f"near interstellar survey tier ({distance_ly:g} LY)"
    if distance_ly <= 20:
        return 2.20, f"deep interstellar survey tier ({distance_ly:g} LY)"
    return 2.60, f"far interstellar survey tier ({distance_ly:g} LY)"


def _rarity_modifier(dataset: SurveyDataset) -> tuple[float, int]:
    prior_sales = SurveyMarketTransaction.objects.filter(
        transaction_type=SurveyMarketTransaction.TYPE_NPC_BUYOUT,
        dataset__system_name=dataset.system_name,
        dataset__body_id=dataset.body_id,
        dataset__scan_type=dataset.scan_type,
    ).count()
    return max(0.50, 1.0 - (0.12 * prior_sales)), prior_sales


def _copy_modifier(dataset: SurveyDataset) -> tuple[float, dict[str, Any]]:
    summary = _sync_lineage_summary(dataset)
    total = int(summary["total"])
    if total <= 0:
        return 1.0, summary
    return max(0.55, 1.0 / (1.0 + (0.15 * total))), summary


def appraise_npc_dataset(dataset: SurveyDataset) -> dict[str, Any]:
    """Return NPC exchange appraisal data for one dataset."""
    if _is_earth_dataset(dataset):
        return {
            "ok": False,
            "error": "Earth survey data is not accepted; no survey exchange pays for home-world basics.",
        }

    base, grade = _grade_band_amount(dataset)
    distance_factor, distance_label = _distance_modifier(dataset)
    rarity_factor, prior_sales = _rarity_modifier(dataset)
    copy_factor, copy_summary = _copy_modifier(dataset)
    payout = int(math.floor(base * distance_factor * rarity_factor * copy_factor))

    return {
        "ok": payout > 0,
        "base": base,
        "grade": grade,
        "distance_factor": distance_factor,
        "distance_label": distance_label,
        "rarity_factor": rarity_factor,
        "prior_sales": prior_sales,
        "copy_factor": copy_factor,
        "copy_summary": copy_summary,
        "payout": max(0, payout),
        "error": "" if payout > 0 else "This dataset has no exchange value.",
    }


def _owned_dataset(caller: Any, dataset_text: str) -> tuple[SurveyDataset | None, str]:
    if not (dataset_text or "").lstrip("#").isdigit():
        return None, "Dataset id must be a number."
    owner_scope, owner_id = actor_owner_key(caller)
    try:
        return (
            SurveyDataset.objects.get(
                id=int(dataset_text.lstrip("#")),
                owner_scope=owner_scope,
                owner_id=int(owner_id),
            ),
            "",
        )
    except SurveyDataset.DoesNotExist:
        return None, f"No owned survey dataset #{dataset_text.lstrip('#')} was found."


def _format_appraisal(exchange: dict[str, Any], dataset: SurveyDataset, appraisal: dict[str, Any]) -> str:
    if not appraisal.get("ok"):
        return appraisal.get("error") or "This dataset cannot be appraised here."

    copy_summary = appraisal["copy_summary"]
    lines = [
        f"{exchange.get('name', 'Survey Exchange')} appraisal",
        f"  Dataset: #{dataset.id} {dataset.name}",
        f"  Body: {dataset.system_name}/{dataset.body_name or dataset.body_id}",
        f"  Grade band: {appraisal['grade']} base {format_credits(appraisal['base'])}",
        f"  Distance: x{appraisal['distance_factor']:.2f} ({appraisal['distance_label']})",
        f"  Rarity: x{appraisal['rarity_factor']:.2f} ({appraisal['prior_sales']} prior NPC buyout(s))",
        "  Copy uncertainty: "
        f"x{appraisal['copy_factor']:.2f} "
        f"({copy_summary['total']} known copies: "
        f"{copy_summary['digital_license']} digital, {copy_summary['cartridge']} cartridge)",
        f"  Exclusive buyout offer: {format_credits(appraisal['payout'])}",
        "",
        f"Use survey exchange sell {dataset.id} confirm to accept.",
    ]
    return "\n".join(lines)


def render_exchange_status(caller: Any) -> str:
    exchange = get_exchange_context(caller)
    if exchange is None:
        return "No survey exchange is available here."
    return "\n".join(
        [
            f"{exchange.get('name', 'Survey Exchange')}",
            "  survey exchange appraise <dataset>",
            "  survey exchange sell <dataset> confirm",
        ]
    )


def handle_survey_exchange_command(caller: Any, args: str) -> str:
    """Handle player-facing survey exchange commands."""
    exchange = get_exchange_context(caller)
    if exchange is None:
        return "No survey exchange is available here."

    tokens = _tokenize(args)
    if not tokens:
        return render_exchange_status(caller)

    action = tokens[0].lower()
    if action == "appraise":
        if len(tokens) < 2:
            return "Usage: survey exchange appraise <dataset>"
        dataset, error = _owned_dataset(caller, tokens[1])
        if error:
            return error
        return _format_appraisal(exchange, dataset, appraise_npc_dataset(dataset))

    if action == "sell":
        if len(tokens) < 3 or tokens[-1].lower() != "confirm":
            return "Usage: survey exchange sell <dataset> confirm"
        dataset, error = _owned_dataset(caller, tokens[1])
        if error:
            return error
        return sell_dataset_to_npc_exchange(caller, dataset, exchange)

    return "Usage: survey exchange, survey exchange appraise <dataset>, survey exchange sell <dataset> confirm"


@transaction.atomic
def sell_dataset_to_npc_exchange(caller: Any, dataset: SurveyDataset, exchange: dict[str, Any]) -> str:
    """Perform an exclusive NPC buyout."""
    dataset = SurveyDataset.objects.select_for_update().get(id=int(dataset.id))
    seller_scope, seller_id = actor_owner_key(caller)
    if dataset.owner_scope != seller_scope or int(dataset.owner_id) != int(seller_id):
        return f"You no longer own survey dataset #{dataset.id}."

    appraisal = appraise_npc_dataset(dataset)
    if not appraisal.get("ok"):
        return appraisal.get("error") or "This dataset cannot be sold here."

    payout = int(appraisal["payout"])
    root_id = _lineage_root_id(dataset)
    metadata = _metadata(dataset)
    commerce = dict(metadata.get("commerce") or {})
    commerce["npc_buyout"] = {
        "exchange_key": exchange.get("exchange_key"),
        "exchange_name": exchange.get("name"),
        "seller_id": int(seller_id),
        "payout": payout,
        "sold_at": timezone.now().isoformat(),
    }
    metadata["commerce"] = commerce

    dataset.owner_scope = OWNER_NPC_MARKET
    dataset.owner_id = int(exchange.get("room_id") or NPC_MARKET_OWNER_ID_DEFAULT)
    dataset.is_transferable = False
    dataset.is_copyable = False
    dataset.license_mode = "npc_archive"
    dataset.metadata = metadata
    dataset.save(
        update_fields=[
            "owner_scope",
            "owner_id",
            "is_transferable",
            "is_copyable",
            "license_mode",
            "metadata",
            "updated_at",
        ]
    )

    SurveyMarketTransaction.objects.create(
        transaction_type=SurveyMarketTransaction.TYPE_NPC_BUYOUT,
        dataset=dataset,
        dataset_name=dataset.name,
        root_dataset_id=root_id,
        source_dataset_id=dataset.id,
        seller_scope=seller_scope,
        seller_id=int(seller_id),
        seller_name=_actor_name(caller),
        buyer_scope=OWNER_NPC_MARKET,
        buyer_id=int(exchange.get("room_id") or NPC_MARKET_OWNER_ID_DEFAULT),
        buyer_name=str(exchange.get("name") or "Survey Exchange"),
        price=payout,
        exchange_key=str(exchange.get("exchange_key") or ""),
        exchange_name=str(exchange.get("name") or ""),
        metadata={"appraisal": appraisal},
    )

    new_balance = grant_credits(caller, payout)
    return (
        f"Sold survey dataset #{dataset.id}: {dataset.name} to "
        f"{exchange.get('name', 'Survey Exchange')} for {format_credits(payout)}.\n"
        f"New balance: {format_credits(new_balance)}."
    )


def _parse_bool(value: str) -> bool | None:
    value = (value or "").strip().lower()
    if value in {"yes", "true", "on", "1"}:
        return True
    if value in {"no", "false", "off", "0"}:
        return False
    return None


def _validate_requested_rights(
    dataset: SurveyDataset,
    *,
    mode: str,
    requested_transferable: bool,
    requested_copyable: bool,
    requested_license_mode: str,
) -> str:
    if mode == SurveyTradeOffer.MODE_TRANSFER and not dataset.is_transferable:
        return f"Dataset #{dataset.id} is not transferable."
    if mode == SurveyTradeOffer.MODE_LICENSE and not dataset.is_copyable:
        return f"Dataset #{dataset.id} is not copyable, so it cannot be licensed."
    if requested_transferable and not dataset.is_transferable:
        return "Requested transferable rights would loosen the source DRM."
    if requested_copyable and not dataset.is_copyable:
        return "Requested copyable rights would loosen the source DRM."
    source_license = str(dataset.license_mode or "transferable")
    if source_license != "transferable" and requested_license_mode != source_license:
        return "Requested license mode would loosen or alter restricted source DRM."
    return ""


def _parse_offer_options(dataset: SurveyDataset, mode: str, tokens: list[str]) -> tuple[dict[str, Any] | None, str]:
    options = {
        "requested_is_transferable": bool(dataset.is_transferable),
        "requested_is_copyable": bool(dataset.is_copyable),
        "requested_license_mode": str(dataset.license_mode or "transferable"),
    }
    idx = 0
    while idx < len(tokens):
        key = tokens[idx].lower()
        if idx + 1 >= len(tokens):
            return None, f"Missing value for option '{tokens[idx]}'."
        value = tokens[idx + 1]
        if key == "copyable":
            parsed = _parse_bool(value)
            if parsed is None:
                return None, "copyable must be yes or no."
            options["requested_is_copyable"] = parsed
        elif key == "transferable":
            parsed = _parse_bool(value)
            if parsed is None:
                return None, "transferable must be yes or no."
            options["requested_is_transferable"] = parsed
        elif key == "license":
            clean = value.strip()
            if not clean or len(clean) > 64:
                return None, "license mode must be 1-64 characters."
            options["requested_license_mode"] = clean
        else:
            return None, f"Unknown offer option '{tokens[idx]}'."
        idx += 2

    error = _validate_requested_rights(
        dataset,
        mode=mode,
        requested_transferable=options["requested_is_transferable"],
        requested_copyable=options["requested_is_copyable"],
        requested_license_mode=options["requested_license_mode"],
    )
    if error:
        return None, error
    return options, ""


def create_trade_offer(caller: Any, args: str) -> str:
    """Create a room-bound P2P trade offer."""
    tokens = _tokenize(args)
    if len(tokens) < 4:
        return (
            "Usage: survey trade offer <player> <dataset> <transfer|license> <credits> "
            "[copyable yes|no] [transferable yes|no] [license <mode>]"
        )

    buyer = find_character_in_room(caller, tokens[0])
    if buyer is None:
        return f"No nearby player matching '{tokens[0]}' was found."

    dataset, error = _owned_dataset(caller, tokens[1])
    if error:
        return error

    mode = tokens[2].lower()
    if mode not in {SurveyTradeOffer.MODE_TRANSFER, SurveyTradeOffer.MODE_LICENSE}:
        return "Offer mode must be transfer or license."

    try:
        price = int(tokens[3])
    except ValueError:
        return "Offer price must be a whole number of credits."
    if price < 0:
        return "Offer price cannot be negative."

    options, error = _parse_offer_options(dataset, mode, tokens[4:])
    if error:
        return error

    seller_scope, seller_id = actor_owner_key(caller)
    buyer_scope, buyer_id = actor_owner_key(buyer)
    expires_at = timezone.now() + timedelta(minutes=OFFER_EXPIRY_MINUTES)

    offer = SurveyTradeOffer.objects.create(
        dataset=dataset,
        dataset_name=dataset.name,
        seller_scope=seller_scope,
        seller_id=int(seller_id),
        seller_name=_actor_name(caller),
        buyer_scope=buyer_scope,
        buyer_id=int(buyer_id),
        buyer_name=_actor_name(buyer),
        mode=mode,
        price=price,
        requested_is_transferable=options["requested_is_transferable"],
        requested_is_copyable=options["requested_is_copyable"],
        requested_license_mode=options["requested_license_mode"],
        seller_location_id=_room_id(caller),
        buyer_location_id=_room_id(buyer),
        expires_at=expires_at,
        metadata={
            "source_dataset_id": int(dataset.id),
            "source_lineage": lineage_copy_summary(dataset),
        },
    )

    try:
        buyer.msg(
            f"{_actor_name(caller)} offers to {mode} survey dataset #{dataset.id}: "
            f"{dataset.name} for {format_credits(price)}. "
            f"Use survey trade accept {offer.id} or survey trade decline {offer.id}."
        )
    except Exception:
        pass

    return (
        f"Created trade offer #{offer.id} for {_actor_name(buyer)}: {mode} "
        f"dataset #{dataset.id} for {format_credits(price)}. "
        f"Expires in {OFFER_EXPIRY_MINUTES} minutes."
    )


def _expire_pending_offers() -> None:
    now = timezone.now()
    SurveyTradeOffer.objects.filter(
        status=SurveyTradeOffer.STATUS_PENDING,
        expires_at__lt=now,
    ).update(status=SurveyTradeOffer.STATUS_EXPIRED, completed_at=now)


def render_trade_offers(caller: Any) -> str:
    """List pending offers involving caller."""
    _expire_pending_offers()
    owner_scope, owner_id = actor_owner_key(caller)
    offers = list(
        SurveyTradeOffer.objects.filter(
            Q(seller_scope=owner_scope, seller_id=int(owner_id))
            | Q(buyer_scope=owner_scope, buyer_id=int(owner_id)),
            status=SurveyTradeOffer.STATUS_PENDING,
        ).order_by("expires_at", "id")[:20]
    )
    if not offers:
        return "No pending survey trade offers."

    lines = ["Pending survey trade offers:"]
    now = timezone.now()
    for offer in offers:
        role = "seller" if offer.seller_id == int(owner_id) and offer.seller_scope == owner_scope else "buyer"
        seconds = max(0, int((offer.expires_at - now).total_seconds()))
        lines.append(
            f"  #{offer.id} ({role}): {offer.seller_name} -> {offer.buyer_name}, "
            f"{offer.mode} {offer.dataset_name or 'dataset'} for "
            f"{format_credits(offer.price)}, expires in {seconds // 60}m"
        )
    return "\n".join(lines)


def _offer_for_action(caller: Any, offer_id_text: str) -> tuple[SurveyTradeOffer | None, str]:
    if not (offer_id_text or "").isdigit():
        return None, "Offer id must be a number."
    try:
        offer = SurveyTradeOffer.objects.get(id=int(offer_id_text))
    except SurveyTradeOffer.DoesNotExist:
        return None, f"No survey trade offer #{offer_id_text} was found."
    if offer.status != SurveyTradeOffer.STATUS_PENDING:
        return None, f"Survey trade offer #{offer.id} is {offer.status}."
    if offer.expires_at < timezone.now():
        offer.status = SurveyTradeOffer.STATUS_EXPIRED
        offer.completed_at = timezone.now()
        offer.save(update_fields=["status", "completed_at", "updated_at"])
        return None, f"Survey trade offer #{offer.id} has expired."
    return offer, ""


def _same_room(a: Any, b: Any) -> bool:
    try:
        return a.location is not None and a.location == b.location
    except Exception:
        return False


@transaction.atomic
def accept_trade_offer(caller: Any, offer_id_text: str) -> str:
    """Accept a pending P2P offer."""
    offer, error = _offer_for_action(caller, offer_id_text)
    if error:
        return error

    buyer_scope, buyer_id = actor_owner_key(caller)
    if offer.buyer_scope != buyer_scope or int(offer.buyer_id) != int(buyer_id):
        return f"Only {offer.buyer_name} can accept survey trade offer #{offer.id}."

    seller = _object_from_id(offer.seller_id)
    if seller is None:
        return f"{offer.seller_name or 'The seller'} is not available."
    if not _same_room(caller, seller):
        return "The seller must be in the same room to complete this offer."

    dataset = SurveyDataset.objects.select_for_update().filter(id=offer.dataset_id).first()
    if dataset is None:
        return f"Survey trade offer #{offer.id} references a missing dataset."
    if dataset.owner_scope != offer.seller_scope or int(dataset.owner_id) != int(offer.seller_id):
        return f"{offer.seller_name} no longer owns dataset #{dataset.id}."

    rights_error = _validate_requested_rights(
        dataset,
        mode=offer.mode,
        requested_transferable=offer.requested_is_transferable,
        requested_copyable=offer.requested_is_copyable,
        requested_license_mode=offer.requested_license_mode,
    )
    if rights_error:
        return rights_error

    balance = get_credits(caller)
    if balance < offer.price:
        return f"You need {format_credits(offer.price)} but only have {format_credits(balance)}."

    now = timezone.now()
    root_id = _lineage_root_id(dataset)

    if offer.mode == SurveyTradeOffer.MODE_TRANSFER:
        dataset.owner_scope = buyer_scope
        dataset.owner_id = int(buyer_id)
        dataset.is_transferable = bool(offer.requested_is_transferable)
        dataset.is_copyable = bool(offer.requested_is_copyable)
        dataset.license_mode = offer.requested_license_mode
        metadata = _metadata(dataset)
        metadata["last_p2p_transfer"] = {
            "offer_id": int(offer.id),
            "seller_id": int(offer.seller_id),
            "buyer_id": int(buyer_id),
            "price": int(offer.price),
            "transferred_at": now.isoformat(),
        }
        dataset.metadata = metadata
        dataset.save(
            update_fields=[
                "owner_scope",
                "owner_id",
                "is_transferable",
                "is_copyable",
                "license_mode",
                "metadata",
                "updated_at",
            ]
        )
        transaction_type = SurveyMarketTransaction.TYPE_P2P_TRANSFER
        result_dataset = dataset
        action = "transferred"
    else:
        transaction_type = SurveyMarketTransaction.TYPE_P2P_LICENSE
        result_dataset = create_licensed_dataset_copy(
            source=dataset,
            owner_scope=buyer_scope,
            owner_id=int(buyer_id),
            is_transferable=offer.requested_is_transferable,
            is_copyable=offer.requested_is_copyable,
            license_mode=offer.requested_license_mode,
            actor=seller,
        )
        action = f"licensed as dataset #{result_dataset.id}"

    tx = SurveyMarketTransaction.objects.create(
        transaction_type=transaction_type,
        dataset=result_dataset,
        dataset_name=result_dataset.name,
        root_dataset_id=root_id,
        source_dataset_id=dataset.id,
        seller_scope=offer.seller_scope,
        seller_id=int(offer.seller_id),
        seller_name=offer.seller_name,
        buyer_scope=buyer_scope,
        buyer_id=int(buyer_id),
        buyer_name=_actor_name(caller),
        price=int(offer.price),
        metadata={"offer_id": int(offer.id), "mode": offer.mode},
    )

    if offer.mode == SurveyTradeOffer.MODE_LICENSE:
        SurveyCopyEvent.objects.filter(
            dataset=result_dataset,
            source_dataset=dataset,
            transaction__isnull=True,
            event_type=SurveyCopyEvent.EVENT_DIGITAL_LICENSE,
        ).update(transaction=tx)

    offer.status = SurveyTradeOffer.STATUS_ACCEPTED
    offer.completed_at = now
    offer.save(update_fields=["status", "completed_at", "updated_at"])

    ok, buyer_balance = spend_credits(caller, offer.price)
    if not ok:
        raise RuntimeError("Buyer credit balance changed before settlement could complete.")
    seller_balance = grant_credits(seller, offer.price)

    try:
        seller.msg(
            f"{_actor_name(caller)} accepted survey trade offer #{offer.id}; "
            f"dataset #{dataset.id} {action} for {format_credits(offer.price)}. "
            f"Your balance is {format_credits(seller_balance)}."
        )
    except Exception:
        pass

    return (
        f"Accepted survey trade offer #{offer.id}; dataset #{dataset.id} {action} "
        f"for {format_credits(offer.price)}.\n"
        f"Your balance: {format_credits(buyer_balance)}."
    )


def decline_trade_offer(caller: Any, offer_id_text: str) -> str:
    offer, error = _offer_for_action(caller, offer_id_text)
    if error:
        return error
    owner_scope, owner_id = actor_owner_key(caller)
    if not (
        (offer.buyer_scope == owner_scope and int(offer.buyer_id) == int(owner_id))
        or (offer.seller_scope == owner_scope and int(offer.seller_id) == int(owner_id))
    ):
        return f"You are not part of survey trade offer #{offer.id}."
    offer.status = SurveyTradeOffer.STATUS_DECLINED
    offer.completed_at = timezone.now()
    offer.save(update_fields=["status", "completed_at", "updated_at"])
    return f"Declined survey trade offer #{offer.id}."


def cancel_trade_offer(caller: Any, offer_id_text: str) -> str:
    offer, error = _offer_for_action(caller, offer_id_text)
    if error:
        return error
    owner_scope, owner_id = actor_owner_key(caller)
    if offer.seller_scope != owner_scope or int(offer.seller_id) != int(owner_id):
        return f"Only {offer.seller_name} can cancel survey trade offer #{offer.id}."
    offer.status = SurveyTradeOffer.STATUS_CANCELLED
    offer.completed_at = timezone.now()
    offer.save(update_fields=["status", "completed_at", "updated_at"])
    return f"Cancelled survey trade offer #{offer.id}."


def handle_survey_trade_command(caller: Any, args: str) -> str:
    """Handle player-facing survey trade commands."""
    tokens = _tokenize(args)
    if not tokens or tokens[0].lower() in {"offers", "list"}:
        return render_trade_offers(caller)

    action = tokens[0].lower()
    rest = args.split(None, 1)[1].strip() if len(args.split(None, 1)) > 1 else ""

    if action == "offer":
        return create_trade_offer(caller, rest)
    if action == "accept":
        return accept_trade_offer(caller, tokens[1] if len(tokens) > 1 else "")
    if action == "decline":
        return decline_trade_offer(caller, tokens[1] if len(tokens) > 1 else "")
    if action == "cancel":
        return cancel_trade_offer(caller, tokens[1] if len(tokens) > 1 else "")

    return (
        "Usage: survey trade offers, survey trade offer <player> <dataset> "
        "<transfer|license> <credits>, survey trade accept <id>, "
        "survey trade decline <id>, survey trade cancel <id>"
    )
