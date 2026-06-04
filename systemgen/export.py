"""JSON import/export helpers and CLI for generated stellar-system records."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, Union

from .adapter import adapt_generated_system
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


def create_demo_system(name: str, seed: int) -> SystemRecord:
    """Create the old small deterministic demo system for import/testing."""
    primary_id = "star-1"

    bodies = [
        BodyRecord(
            id=primary_id,
            name=f"{name} A",
            kind="star",
            classification="G-class main sequence",
            summary="A stable yellow-white main sequence star.",
            temperature_k=5778,
            radius_km=696340,
            survey_difficulty=1,
        ),
        BodyRecord(
            id="planet-1",
            name=f"{name} I",
            kind="planet",
            classification="rocky inner planet",
            summary="A hot rocky world orbiting close to the primary.",
            orbit=OrbitalElements(
                parent_id=primary_id,
                semi_major_axis_au=0.42,
                orbital_period_days=96.0,
                angle_degrees=35.0,
            ),
            radius_km=3300,
            mass_earth=0.35,
            temperature_k=480,
            survey_difficulty=2,
        ),
        BodyRecord(
            id="planet-2",
            name=f"{name} II",
            kind="planet",
            classification="temperate terrestrial planet",
            summary="A terrestrial world with moderate survey potential.",
            orbit=OrbitalElements(
                parent_id=primary_id,
                semi_major_axis_au=1.08,
                orbital_period_days=410.0,
                angle_degrees=140.0,
            ),
            radius_km=6400,
            mass_earth=1.05,
            temperature_k=288,
            survey_difficulty=3,
            children=["planet-2-moon-1"],
        ),
        BodyRecord(
            id="planet-2-moon-1",
            name=f"{name} II-a",
            kind="moon",
            classification="large rocky moon",
            summary="A tidally locked moon with exposed mineral formations.",
            orbit=OrbitalElements(
                parent_id="planet-2",
                semi_major_axis_au=0.0026,
                orbital_period_days=27.0,
                angle_degrees=210.0,
            ),
            radius_km=1700,
            mass_earth=0.012,
            temperature_k=240,
            survey_difficulty=2,
        ),
        BodyRecord(
            id="planet-3",
            name=f"{name} III",
            kind="planet",
            classification="gas giant",
            summary="A large gas giant with strong magnetospheric readings.",
            orbit=OrbitalElements(
                parent_id=primary_id,
                semi_major_axis_au=5.4,
                orbital_period_days=4320.0,
                angle_degrees=275.0,
            ),
            radius_km=69000,
            mass_earth=310.0,
            temperature_k=130,
            survey_difficulty=4,
        ),
    ]

    return SystemRecord(
        name=name,
        seed=seed,
        primary_body_id=primary_id,
        bodies=bodies,
        generation_notes=[
            "Demo v0.2 system generated from systemgen.export CLI.",
            "Use --mode procedural for the procedural generator path.",
        ],
    )


def generate_procedural_system(name: str, seed: int) -> SystemRecord:
    """Generate through the stable generator entry point and adapt if needed."""
    from .generators import generate_system

    raw = generate_system(name=name, seed=seed)
    return adapt_generated_system(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a stellar system JSON file.")
    parser.add_argument("--name", required=True, help="System name, e.g. Astalon")
    parser.add_argument("--seed", required=True, type=int, help="Deterministic generation seed")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--mode",
        choices=("procedural", "demo"),
        default="procedural",
        help="Export source. Default: procedural.",
    )
    args = parser.parse_args()

    if args.mode == "demo":
        system = create_demo_system(args.name, args.seed)
    else:
        system = generate_procedural_system(args.name, args.seed)

    out_path = write_system_json(system, args.out)
    body_count = len(system.bodies)
    print(f"Wrote system JSON: {out_path} ({system.name}, seed={system.seed}, bodies={body_count})")


if __name__ == "__main__":
    main()
