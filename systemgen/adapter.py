"""Adapters between early generator outputs and the stable v0.2 schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from .schema import BodyRecord, OrbitalElements, SystemRecord


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _body_record_from_mapping(raw: Mapping[str, Any], fallback_id: str, parent_id: Optional[str] = None) -> BodyRecord:
    raw_orbit = raw.get("orbit") or {}
    orbit = OrbitalElements(
        parent_id=raw_orbit.get("parent_id", parent_id),
        semi_major_axis_au=_as_float(raw_orbit.get("semi_major_axis_au", raw.get("semi_major_axis_au", raw.get("orbit_radius_au", 0.0)))),
        orbital_period_days=_as_float(raw_orbit.get("orbital_period_days", raw.get("orbital_period_days", 0.0))),
        angle_degrees=_as_float(raw_orbit.get("angle_degrees", raw.get("angle_degrees", 0.0))),
        eccentricity=_as_float(raw_orbit.get("eccentricity", raw.get("eccentricity", 0.0))),
        inclination_degrees=_as_float(raw_orbit.get("inclination_degrees", raw.get("inclination_degrees", 0.0))),
    )

    return BodyRecord(
        id=str(raw.get("id", fallback_id)),
        name=str(raw.get("name", fallback_id)),
        kind=str(raw.get("kind", "body")),
        classification=str(raw.get("classification", raw.get("planet_type", raw.get("spectral_class", "unknown")))),
        summary=str(raw.get("summary", "")),
        orbit=orbit,
        radius_km=raw.get("radius_km"),
        mass_earth=raw.get("mass_earth"),
        temperature_k=raw.get("temperature_k"),
        survey_difficulty=_as_int(raw.get("survey_difficulty", 1), 1),
        survey_tags=list(raw.get("survey_tags", []) or []),
        children=list(raw.get("children", []) or []),
        extra=dict(raw.get("extra", {}) or {}),
    )


def adapt_generated_system(raw: Any) -> SystemRecord:
    """
    Convert several likely generator output forms into a SystemRecord.

    Accepted inputs:
      - SystemRecord
      - v0.2-compatible dict with a bodies list
      - early object/dict with name, seed, star/primary, planets, and moons
    """
    if isinstance(raw, SystemRecord):
        return raw

    if isinstance(raw, Mapping) and "bodies" in raw:
        return SystemRecord.from_dict(dict(raw))

    name = str(_get(raw, "name", "Unnamed System"))
    seed = _as_int(_get(raw, "seed", 0), 0)
    bodies: list[BodyRecord] = []

    star = _get(raw, "star", None) or _get(raw, "primary", None)
    primary_body_id: Optional[str] = None

    if star is not None:
        if isinstance(star, Mapping):
            star_record = _body_record_from_mapping(star, "star-1")
            star_record.kind = "star"
            if not star_record.name or star_record.name == "star-1":
                star_record.name = f"{name} A"
        else:
            star_record = BodyRecord(
                id=str(_get(star, "id", "star-1")),
                name=str(_get(star, "name", f"{name} A")),
                kind="star",
                classification=str(_get(star, "classification", _get(star, "spectral_class", "star"))),
                summary=str(_get(star, "summary", "Primary stellar body.")),
                temperature_k=_get(star, "temperature_k", None),
                radius_km=_get(star, "radius_km", None),
            )
        primary_body_id = star_record.id
        bodies.append(star_record)

    for index, planet in enumerate(_get(raw, "planets", []) or [], start=1):
        planet_id = str(_get(planet, "id", f"planet-{index}"))
        planet_name = str(_get(planet, "name", f"{name} {index}"))

        if isinstance(planet, Mapping):
            planet_record = _body_record_from_mapping(planet, planet_id, primary_body_id)
            planet_record.id = planet_id
            planet_record.name = planet_name
            planet_record.kind = str(planet.get("kind", "planet"))
        else:
            planet_record = BodyRecord(
                id=planet_id,
                name=planet_name,
                kind=str(_get(planet, "kind", "planet")),
                classification=str(_get(planet, "classification", _get(planet, "planet_type", "planet"))),
                summary=str(_get(planet, "summary", "Planetary body.")),
                orbit=OrbitalElements(
                    parent_id=primary_body_id,
                    semi_major_axis_au=_as_float(_get(planet, "orbit_radius_au", _get(planet, "semi_major_axis_au", index))),
                    orbital_period_days=_as_float(_get(planet, "orbital_period_days", index * 365.0)),
                    angle_degrees=_as_float(_get(planet, "angle_degrees", 0.0)),
                ),
                radius_km=_get(planet, "radius_km", None),
                mass_earth=_get(planet, "mass_earth", None),
                temperature_k=_get(planet, "temperature_k", None),
                survey_difficulty=_as_int(_get(planet, "survey_difficulty", 1), 1),
            )

        moon_ids: list[str] = []
        for moon_index, moon in enumerate(_get(planet, "moons", []) or [], start=1):
            moon_id = str(_get(moon, "id", f"{planet_id}-moon-{moon_index}"))
            moon_ids.append(moon_id)

            if isinstance(moon, Mapping):
                moon_record = _body_record_from_mapping(moon, moon_id, planet_id)
                moon_record.kind = "moon"
            else:
                moon_record = BodyRecord(
                    id=moon_id,
                    name=str(_get(moon, "name", f"{planet_name}-{moon_index}")),
                    kind="moon",
                    classification=str(_get(moon, "classification", "moon")),
                    summary=str(_get(moon, "summary", "Natural satellite.")),
                    orbit=OrbitalElements(
                        parent_id=planet_id,
                        semi_major_axis_au=_as_float(_get(moon, "orbit_radius_au", 0.002)),
                        orbital_period_days=_as_float(_get(moon, "orbital_period_days", 28.0)),
                        angle_degrees=_as_float(_get(moon, "angle_degrees", 0.0)),
                    ),
                    survey_difficulty=_as_int(_get(moon, "survey_difficulty", 1), 1),
                )

            bodies.append(moon_record)

        if moon_ids and not planet_record.children:
            planet_record.children = moon_ids

        bodies.append(planet_record)

    return SystemRecord(
        name=name,
        seed=seed,
        primary_body_id=primary_body_id,
        bodies=bodies,
        generation_notes=["Adapted from early generator output."],
    )
