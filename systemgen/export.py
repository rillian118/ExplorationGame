"""
JSON import/export helpers for systemgen records.

The intended workflow is:

    generated = generate_system(...)
    record = adapt_generated_system(generated)
    write_system_json(record, "Astalon.system.json")

If your generator already returns dictionaries, you can bypass the adapter and
call write_system_json() with a SystemRecord or compatible dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from .schema import BodyRecord, OrbitalElements, SystemRecord

JsonLike = Union[SystemRecord, Mapping[str, Any]]


def system_to_dict(system: JsonLike) -> Dict[str, Any]:
    if isinstance(system, SystemRecord):
        return system.to_dict()
    return dict(system)


def write_system_json(system: JsonLike, path: Union[str, Path]) -> Path:
    """Write a generated system to a stable, pretty-printed JSON file."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = system_to_dict(system)
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def read_system_json(path: Union[str, Path]) -> SystemRecord:
    """Read a generated system JSON file into a SystemRecord."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SystemRecord.from_dict(data)


def adapt_generated_system(raw: Any) -> SystemRecord:
    """Best-effort adapter for early generator outputs.

    This accepts either:
    - a SystemRecord,
    - a dict that already matches the v0.2 schema,
    - a simple object/dict with name, seed, star, planets, and moons fields.

    You can replace or specialize this once the generator's internal objects are
    settled.  The importer only needs the exported JSON schema to remain stable.
    """
    if isinstance(raw, SystemRecord):
        return raw

    if isinstance(raw, Mapping) and "bodies" in raw:
        return SystemRecord.from_dict(dict(raw))

    def get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key, default)
        return getattr(obj, key, default)

    name = str(get(raw, "name", "Unnamed System"))
    seed = int(get(raw, "seed", 0))
    bodies = []

    star = get(raw, "star", None) or get(raw, "primary", None)
    if star is not None:
        star_name = str(get(star, "name", f"{name} A"))
        bodies.append(
            BodyRecord(
                id="star-1",
                name=star_name,
                kind="star",
                classification=str(get(star, "classification", get(star, "spectral_class", "star"))),
                summary=str(get(star, "summary", "Primary stellar body.")),
                temperature_k=get(star, "temperature_k", None),
                radius_km=get(star, "radius_km", None),
            )
        )
        primary_body_id = "star-1"
    else:
        primary_body_id = None

    for idx, planet in enumerate(get(raw, "planets", []) or [], start=1):
        planet_id = f"planet-{idx}"
        planet_name = str(get(planet, "name", f"{name} {idx}"))
        orbit = OrbitalElements(
            parent_id=primary_body_id,
            semi_major_axis_au=float(get(planet, "orbit_radius_au", get(planet, "semi_major_axis_au", idx))),
            orbital_period_days=float(get(planet, "orbital_period_days", idx * 365.0)),
            angle_degrees=float(get(planet, "angle_degrees", 0.0)),
        )
        bodies.append(
            BodyRecord(
                id=planet_id,
                name=planet_name,
                kind=str(get(planet, "kind", "planet")),
                classification=str(get(planet, "classification", get(planet, "planet_type", "planet"))),
                summary=str(get(planet, "summary", "Planetary body.")),
                orbit=orbit,
                radius_km=get(planet, "radius_km", None),
                mass_earth=get(planet, "mass_earth", None),
                temperature_k=get(planet, "temperature_k", None),
                survey_difficulty=int(get(planet, "survey_difficulty", 1)),
            )
        )

        for moon_idx, moon in enumerate(get(planet, "moons", []) or [], start=1):
            moon_id = f"planet-{idx}-moon-{moon_idx}"
            bodies.append(
                BodyRecord(
                    id=moon_id,
                    name=str(get(moon, "name", f"{planet_name}-{moon_idx}")),
                    kind="moon",
                    classification=str(get(moon, "classification", "moon")),
                    summary=str(get(moon, "summary", "Natural satellite.")),
                    orbit=OrbitalElements(
                        parent_id=planet_id,
                        semi_major_axis_au=float(get(moon, "orbit_radius_au", 0.002)),
                        orbital_period_days=float(get(moon, "orbital_period_days", 28.0)),
                        angle_degrees=float(get(moon, "angle_degrees", 0.0)),
                    ),
                    survey_difficulty=int(get(moon, "survey_difficulty", 1)),
                )
            )

    return SystemRecord(
        name=name,
        seed=seed,
        primary_body_id=primary_body_id,
        bodies=bodies,
        generation_notes=["Adapted from early generator output."],
    )
