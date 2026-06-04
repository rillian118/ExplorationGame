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
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
]

MOON_SUFFIXES = "abcdefghijklmnopqrstuvwxyz"


def _kepler_period_days(axis_au: float, star_mass_solar: float) -> float:
    """Very rough orbital period from semi-major axis and stellar mass."""
    years = (axis_au**3 / max(star_mass_solar, 0.1)) ** 0.5
    return years * 365.25


def _planet_profile(
    rng: random.Random, axis_au: float
) -> tuple[str, float, float, float, int, str]:
    """Return classification, radius_km, mass_earth, temp_k, difficulty, summary."""
    if axis_au < 0.55:
        classification = rng.choice(["scorched rocky planet", "rocky inner planet"])
        radius = rng.uniform(2200, 6000)
        mass = rng.uniform(0.15, 0.9)
        temp = rng.uniform(420, 760)
        difficulty = 2
        summary = "A heat-blasted inner world with limited surface stability."
    elif axis_au < 1.8:
        classification = rng.choice(
            ["dry terrestrial planet", "temperate terrestrial planet", "ice-rich terrestrial planet"]
        )
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


def _build_sorted_moons(
    rng: random.Random,
    *,
    planet_id: str,
    planet_name: str,
    moon_count: int,
    planet_temperature_k: float,
    planet_survey_difficulty: int,
) -> List[BodyRecord]:
    """
    Generate moons, sort them by orbital distance, then assign suffixes.

    This keeps displayed moon names aligned with the order players see in the
    orbital tree: inner moons become -a, then -b, then -c, etc.
    """
    moon_specs = []

    for _ in range(moon_count):
        moon_distance_au = rng.uniform(0.0012, 0.0085)
        moon_specs.append(
            {
                "distance_au": moon_distance_au,
                "classification": rng.choice(["small rocky moon", "icy moon", "large rocky moon"]),
                "period_days": rng.uniform(6.0, 65.0),
                "angle_degrees": rng.uniform(0, 360),
                "eccentricity": rng.uniform(0.0, 0.08),
                "inclination_degrees": rng.uniform(0.0, 6.0),
                "radius_km": rng.uniform(450, 2900),
                "mass_earth": rng.uniform(0.001, 0.04),
                "temperature_k": max(30, planet_temperature_k - rng.uniform(5, 45)),
            }
        )

    moon_specs.sort(key=lambda spec: spec["distance_au"])

    moons: List[BodyRecord] = []
    for index, spec in enumerate(moon_specs, start=1):
        suffix = MOON_SUFFIXES[index - 1]
        moon_id = f"{planet_id}-moon-{index}"
        moons.append(
            BodyRecord(
                id=moon_id,
                name=f"{planet_name}-{suffix}",
                kind="moon",
                classification=spec["classification"],
                summary="A natural satellite with localized survey potential.",
                orbit=OrbitalElements(
                    parent_id=planet_id,
                    semi_major_axis_au=round(spec["distance_au"], 6),
                    orbital_period_days=round(spec["period_days"], 2),
                    angle_degrees=round(spec["angle_degrees"], 1),
                    eccentricity=round(spec["eccentricity"], 3),
                    inclination_degrees=round(spec["inclination_degrees"], 2),
                ),
                radius_km=round(spec["radius_km"]),
                mass_earth=round(spec["mass_earth"], 4),
                temperature_k=round(spec["temperature_k"]),
                survey_difficulty=max(1, planet_survey_difficulty - 1),
            )
        )

    return moons

def _normalize_moon_suffixes(bodies: List[BodyRecord]) -> None:
    """
    Rename moons so suffixes match orbital order.

    For each planet:
      innermost moon -> -a
      next moon      -> -b
      next moon      -> -c

    Also rewrites moon IDs and the parent planet's children list.
    """
    planets = [body for body in bodies if body.kind == "planet"]

    for planet in planets:
        moons = [
            body
            for body in bodies
            if body.kind == "moon"
            and body.orbit
            and body.orbit.parent_id == planet.id
        ]

        if not moons:
            planet.children = []
            continue

        moons.sort(
            key=lambda moon: (
                moon.orbit.semi_major_axis_au if moon.orbit else 0.0,
                moon.name,
            )
        )

        new_child_ids: List[str] = []

        for index, moon in enumerate(moons, start=1):
            suffix = chr(96 + index)  # 1 -> a, 2 -> b, 3 -> c
            moon.id = f"{planet.id}-moon-{index}"
            moon.name = f"{planet.name}-{suffix}"
            new_child_ids.append(moon.id)

        planet.children = new_child_ids

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

        moons = _build_sorted_moons(
            rng,
            planet_id=planet_id,
            planet_name=planet_name,
            moon_count=_moon_count(rng, classification),
            planet_temperature_k=temp,
            planet_survey_difficulty=difficulty,
        )
        planet.children = [moon.id for moon in moons]
        bodies.extend(moons)

    _normalize_moon_suffixes(bodies)

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
