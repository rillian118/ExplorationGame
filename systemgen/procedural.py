"""
Deterministic v0.2 procedural stellar-system generator.

This is intentionally conservative: it produces gameplay-usable system records
without trying to be a complete astrophysics simulation. The exported schema is
stable; the generation internals can become more sophisticated later.
"""

from __future__ import annotations

import random
from typing import List, Tuple

from .schema import BodyRecord, OrbitalElements, SystemRecord


STAR_CLASSES: List[Tuple[str, float, float, int, str]] = [
    ("M-class red dwarf", 0.45, 0.55, 3300, "A dim red main sequence star."),
    ("K-class orange dwarf", 0.80, 0.85, 4500, "A long-lived orange main sequence star."),
    ("G-class main sequence", 1.00, 1.00, 5778, "A stable yellow-white main sequence star."),
    ("F-class main sequence", 1.25, 1.30, 6500, "A bright white main sequence star."),
]

PLANET_CLASSES = [
    "scorched rocky planet",
    "rocky inner planet",
    "dry terrestrial planet",
    "temperate terrestrial planet",
    "ice-rich terrestrial planet",
    "sub-Neptune",
    "ice giant",
    "gas giant",
]

ROMAN_NUMERALS = [
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"
]


def _kepler_period_days(axis_au: float, star_mass_solar: float) -> float:
    """Very rough orbital period from semi-major axis and stellar mass."""
    years = (axis_au ** 3 / max(star_mass_solar, 0.1)) ** 0.5
    return years * 365.25


def _planet_profile(rng: random.Random, axis_au: float) -> tuple[str, float, float, float, int, str]:
    """Return classification, radius_km, mass_earth, temp_k, difficulty, summary."""
    if axis_au < 0.55:
        classification = rng.choice(["scorched rocky planet", "rocky inner planet"])
        radius = rng.uniform(2200, 6000)
        mass = rng.uniform(0.15, 0.9)
        temp = rng.uniform(420, 760)
        difficulty = 2
        summary = "A heat-blasted inner world with limited surface stability."
    elif axis_au < 1.8:
        classification = rng.choice(["dry terrestrial planet", "temperate terrestrial planet", "ice-rich terrestrial planet"])
        radius = rng.uniform(4500, 7600)
        mass = rng.uniform(0.45, 1.8)
        temp = rng.uniform(220, 330)
        difficulty = 3
        summary = "A terrestrial world with survey-relevant surface conditions."
    elif axis_au < 4.0:
        classification = rng.choice(["ice-rich terrestrial planet", "sub-Neptune", "ice giant"])
        radius = rng.uniform(7000, 26000)
        mass = rng.uniform(2.0, 25.0)
        temp = rng.uniform(90, 220)
        difficulty = 3
        summary = "A cold outer world with volatile-rich readings."
    else:
        classification = rng.choice(["ice giant", "gas giant"])
        radius = rng.uniform(24000, 76000)
        mass = rng.uniform(20.0, 330.0)
        temp = rng.uniform(60, 160)
        difficulty = 4
        summary = "A large outer planet with complex atmospheric signatures."

    return classification, radius, mass, temp, difficulty, summary


def _moon_count(rng: random.Random, classification: str) -> int:
    if classification == "gas giant":
        return rng.randint(2, 5)
    if classification in {"ice giant", "sub-Neptune"}:
        return rng.randint(0, 3)
    if "terrestrial" in classification and rng.random() < 0.35:
        return 1
    return 0


def generate_system(name: str, seed: int) -> SystemRecord:
    """Generate a deterministic SystemRecord for the given name and seed."""
    rng = random.Random(seed)

    star_class, star_mass, star_radius_scale, star_temp, star_summary = rng.choice(STAR_CLASSES)
    primary_id = "star-1"

    bodies: List[BodyRecord] = [
        BodyRecord(
            id=primary_id,
            name=f"{name} A",
            kind="star",
            classification=star_class,
            summary=star_summary,
            orbit=OrbitalElements(parent_id=None),
            radius_km=696_340 * star_radius_scale,
            mass_earth=332_946 * star_mass,
            temperature_k=star_temp,
            survey_difficulty=1,
        )
    ]

    planet_count = rng.randint(4, 8)
    axis = rng.uniform(0.28, 0.55)

    for index in range(1, planet_count + 1):
        # Increase spacing outward with mild deterministic variation.
        if index > 1:
            axis *= rng.uniform(1.45, 2.05)

        classification, radius, mass, temp, difficulty, summary = _planet_profile(rng, axis)
        planet_id = f"planet-{index}"
        planet_name = f"{name} {ROMAN_NUMERALS[index - 1]}"

        planet = BodyRecord(
            id=planet_id,
            name=planet_name,
            kind="planet",
            classification=classification,
            summary=summary,
            orbit=OrbitalElements(
                parent_id=primary_id,
                semi_major_axis_au=round(axis, 4),
                orbital_period_days=round(_kepler_period_days(axis, star_mass), 2),
                angle_degrees=round(rng.uniform(0, 360), 1),
                eccentricity=round(rng.uniform(0.0, 0.12), 3),
                inclination_degrees=round(rng.uniform(0.0, 4.0), 2),
            ),
            radius_km=round(radius),
            mass_earth=round(mass, 3),
            temperature_k=round(temp),
            survey_difficulty=difficulty,
            survey_tags=[],
        )
        bodies.append(planet)

        moon_ids: List[str] = []
        for moon_index in range(1, _moon_count(rng, classification) + 1):
            moon_id = f"{planet_id}-moon-{moon_index}"
            moon_ids.append(moon_id)
            moon_distance_au = rng.uniform(0.0012, 0.0085)
            bodies.append(
                BodyRecord(
                    id=moon_id,
                    name=f"{planet_name}-{chr(96 + moon_index)}",
                    kind="moon",
                    classification=rng.choice(["small rocky moon", "icy moon", "large rocky moon"]),
                    summary="A natural satellite with localized survey potential.",
                    orbit=OrbitalElements(
                        parent_id=planet_id,
                        semi_major_axis_au=round(moon_distance_au, 6),
                        orbital_period_days=round(rng.uniform(6.0, 65.0), 2),
                        angle_degrees=round(rng.uniform(0, 360), 1),
                        eccentricity=round(rng.uniform(0.0, 0.08), 3),
                        inclination_degrees=round(rng.uniform(0.0, 6.0), 2),
                    ),
                    radius_km=round(rng.uniform(450, 2900)),
                    mass_earth=round(rng.uniform(0.001, 0.04), 4),
                    temperature_k=round(max(30, temp - rng.uniform(5, 45))),
                    survey_difficulty=max(1, difficulty - 1),
                )
            )

        planet.children = moon_ids

    return SystemRecord(
        name=name,
        seed=seed,
        primary_body_id=primary_id,
        bodies=bodies,
        generation_notes=[
            "Generated by systemgen.procedural v0.2.",
            "Orbital values are deterministic gameplay approximations.",
        ],
        extra={"generator": "systemgen.procedural", "generator_version": "0.2"},
    )
