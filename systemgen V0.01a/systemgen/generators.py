\
from __future__ import annotations

import random
from typing import Optional

from .models import (
    Orbit,
    PhysicalProfile,
    Rotation,
    SpatialField,
    SpatialObject,
    StarSystem,
    SystemBody,
    Vector3,
)
from .orbital import orbital_period_years
from .tables import (
    ARCHITECTURES,
    MOON_CLASSES,
    RESOURCE_TYPES,
    STAR_CLASS_WEIGHTS,
    STAR_PROFILES,
    SYSTEM_NAME_ROOTS,
    WORLD_CLASSES,
)

GENERATION_VERSION = "stellar-v0.2"


def weighted_choice(rng: random.Random, weighted_items: list[tuple[str, int]]) -> str:
    total = sum(weight for _, weight in weighted_items)
    roll = rng.uniform(0, total)
    cumulative = 0.0
    for item, weight in weighted_items:
        cumulative += weight
        if roll <= cumulative:
            return item
    return weighted_items[-1][0]


def slugify(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def generate_system(seed: int, name: Optional[str] = None) -> StarSystem:
    rng = random.Random(seed)

    system_name = name or rng.choice(SYSTEM_NAME_ROOTS)
    system_key = slugify(system_name)

    age = round(rng.uniform(0.5, 11.5), 2)
    metallicity = round(rng.uniform(0.2, 2.0), 2)
    resource_rating = clamp_int(round((metallicity / 2.0) * 10 + rng.uniform(-2, 2)), 0, 10)
    danger_rating = rng.randint(0, 10)
    settlement_rating = clamp_int(rng.randint(0, 10) + (1 if resource_rating >= 7 else 0), 0, 10)

    primary_star = generate_primary_star(rng, system_name)
    star_mass = primary_star.physical.mass
    luminosity = primary_star.physical.resource_profile["luminosity_solar"]
    hz_inner = primary_star.physical.resource_profile["habitable_zone_inner"]
    hz_outer = primary_star.physical.resource_profile["habitable_zone_outer"]

    architecture = rng.choice(ARCHITECTURES)
    planet_count = determine_planet_count(rng, primary_star.physical.world_class, architecture)

    bodies: list[SystemBody] = [primary_star]
    fields: list[SpatialField] = []
    objects: list[SpatialObject] = []

    previous_orbit = rng.uniform(0.15, 0.35)
    planet_keys: list[str] = []

    for i in range(planet_count):
        semi_major_axis = next_orbit_radius(rng, previous_orbit, architecture)
        previous_orbit = semi_major_axis
        zone = classify_zone(semi_major_axis, hz_inner, hz_outer)

        planet = generate_planet(
            rng=rng,
            system_name=system_name,
            index=i + 1,
            parent_key=primary_star.key,
            semi_major_axis=semi_major_axis,
            star_mass=star_mass,
            zone=zone,
            metallicity=metallicity,
        )

        bodies.append(planet)
        primary_star.children.append(planet.key)
        planet_keys.append(planet.key)

        moons = generate_moons(rng, system_name, planet, len(bodies))
        for moon in moons:
            bodies.append(moon)
            planet.children.append(moon.key)

    fields.extend(generate_fields(rng, system_key, planet_keys, architecture, resource_rating))
    objects.extend(generate_artificial_objects(rng, system_key, bodies, fields, settlement_rating, resource_rating, danger_rating))

    return StarSystem(
        key=system_key,
        seed=seed,
        generation_version=GENERATION_VERSION,
        position=Vector3(
            x=round(rng.uniform(-1000, 1000), 3),
            y=round(rng.uniform(-1000, 1000), 3),
            z=round(rng.uniform(-50, 50), 3),
        ),
        name=system_name,
        primary_star=primary_star,
        bodies=bodies,
        fields=fields,
        objects=objects,
        system_age=age,
        metallicity=metallicity,
        danger_rating=danger_rating,
        settlement_rating=settlement_rating,
        resource_rating=resource_rating,
        survey_level=0,
    )


def generate_primary_star(rng: random.Random, system_name: str) -> SystemBody:
    star_class = weighted_choice(rng, STAR_CLASS_WEIGHTS)
    profile = STAR_PROFILES[star_class]

    mass = round(rng.uniform(*profile["mass_range"]), 3)
    radius = round(rng.uniform(*profile["radius_range"]), 3)
    luminosity = round(rng.uniform(*profile["luminosity_range"]), 4)
    temperature = round(rng.uniform(*profile["temperature_range"]), 0)

    hz_inner = round((luminosity / 1.1) ** 0.5, 3)
    hz_outer = round((luminosity / 0.53) ** 0.5, 3)

    physical = PhysicalProfile(
        radius=radius,
        mass=mass,
        gravity=0.0,
        temperature=temperature,
        atmosphere="plasma",
        hydrosphere="none",
        world_class=star_class,
        habitability=0.0,
        resource_profile={
            "stellar_label": profile["label"],
            "color": profile["color"],
            "luminosity_solar": luminosity,
            "habitable_zone_inner": hz_inner,
            "habitable_zone_outer": hz_outer,
        },
    )

    return SystemBody(
        key=f"{slugify(system_name)}_a",
        name=f"{system_name}-A",
        body_type="star",
        parent_key=None,
        orbit=None,
        rotation=None,
        physical=physical,
    )


def determine_planet_count(rng: random.Random, star_class: str, architecture: str) -> int:
    ranges = {
        "M": (2, 7),
        "K": (3, 9),
        "G": (4, 10),
        "F": (3, 8),
        "A": (2, 7),
        "white_dwarf": (0, 4),
        "red_giant": (0, 5),
    }
    low, high = ranges.get(star_class, (3, 8))
    count = rng.randint(low, high)
    if architecture == "sparse_system":
        count = max(0, count - rng.randint(1, 3))
    if architecture in {"wide_outer_system", "gas_giant_dominated"}:
        count += rng.randint(0, 2)
    return count


def next_orbit_radius(rng: random.Random, previous: float, architecture: str) -> float:
    if architecture == "compact_inner_system":
        multiplier = rng.uniform(1.35, 1.8)
    elif architecture == "wide_outer_system":
        multiplier = rng.uniform(1.8, 2.7)
    elif architecture == "sparse_system":
        multiplier = rng.uniform(1.9, 3.0)
    else:
        multiplier = rng.uniform(1.5, 2.25)
    return round(previous * multiplier, 3)


def classify_zone(orbit_au: float, hz_inner: float, hz_outer: float) -> str:
    if orbit_au < hz_inner * 0.75:
        return "inner"
    if hz_inner <= orbit_au <= hz_outer:
        return "habitable"
    if orbit_au <= hz_outer * 3.0:
        return "outer"
    return "frozen"


def generate_planet(
    rng: random.Random,
    system_name: str,
    index: int,
    parent_key: str,
    semi_major_axis: float,
    star_mass: float,
    zone: str,
    metallicity: float,
) -> SystemBody:
    world_class = rng.choice(WORLD_CLASSES[zone])
    roman = to_roman(index)
    key = f"{slugify(system_name)}_{index}"

    period_days = round(orbital_period_years(semi_major_axis, star_mass) * 365.25, 2)
    eccentricity = round(random_eccentricity(rng), 3)
    inclination = round(random_inclination(rng), 2)
    direction = "retrograde" if rng.random() < 0.02 else "prograde"

    orbit = Orbit(
        parent_key=parent_key,
        semi_major_axis=semi_major_axis,
        eccentricity=eccentricity,
        inclination=inclination,
        orbital_period=period_days,
        phase=round(rng.random(), 4),
        direction=direction,
    )

    rotation = generate_rotation(rng, world_class, period_days, semi_major_axis)
    physical = generate_physical_profile(rng, world_class, zone, metallicity)

    surface_map_id = f"surface:{key}" if world_class not in {"gas_giant", "ice_giant"} else None

    return SystemBody(
        key=key,
        name=f"{system_name} {roman}",
        body_type="planet",
        parent_key=parent_key,
        orbit=orbit,
        rotation=rotation,
        physical=physical,
        surface_map_id=surface_map_id,
    )


def generate_rotation(rng: random.Random, world_class: str, orbital_period_days: float, semi_major_axis: float) -> Rotation:
    tidally_locked = False

    if semi_major_axis < 0.12 and rng.random() < 0.65:
        tidally_locked = True

    if tidally_locked:
        rotation_period = orbital_period_days * 24.0
    elif world_class in {"gas_giant", "ice_giant"}:
        rotation_period = rng.uniform(6, 20)
    else:
        rotation_period = rng.uniform(10, 80)

    return Rotation(
        rotation_period=round(rotation_period, 2),
        axial_tilt=round(random_axial_tilt(rng), 2),
        phase=round(rng.random(), 4),
        tidally_locked=tidally_locked,
    )


def generate_physical_profile(rng: random.Random, world_class: str, zone: str, metallicity: float) -> PhysicalProfile:
    if world_class == "gas_giant":
        radius = rng.uniform(4.0, 12.0)
        mass = rng.uniform(20.0, 320.0)
        atmosphere = "dense"
        hydrosphere = "exotic"
        habitability = 0.0
    elif world_class == "ice_giant":
        radius = rng.uniform(3.0, 5.0)
        mass = rng.uniform(10.0, 25.0)
        atmosphere = "dense"
        hydrosphere = "methane"
        habitability = 0.0
    else:
        radius = rng.uniform(0.2, 1.8)
        mass = max(0.02, radius ** rng.uniform(2.4, 3.2))
        atmosphere = choose_atmosphere(rng, world_class)
        hydrosphere = choose_hydrosphere(rng, world_class)
        habitability = estimate_habitability(world_class, atmosphere, hydrosphere)

    gravity = mass / max(radius * radius, 0.01)
    temperature = estimate_temperature(rng, world_class, zone)

    resources = {
        resource: round(clamp(rng.random() * metallicity, 0.0, 1.0), 2)
        for resource in RESOURCE_TYPES
    }

    return PhysicalProfile(
        radius=round(radius, 3),
        mass=round(mass, 3),
        gravity=round(gravity, 3),
        temperature=round(temperature, 1),
        atmosphere=atmosphere,
        hydrosphere=hydrosphere,
        world_class=world_class,
        habitability=round(habitability, 2),
        resource_profile=resources,
    )


def choose_atmosphere(rng: random.Random, world_class: str) -> str:
    table = {
        "temperate_world": ["thin", "breathable", "breathable", "dense"],
        "ocean_world": ["breathable", "dense", "toxic"],
        "desert_world": ["thin", "breathable", "dense"],
        "toxic_world": ["toxic", "dense", "corrosive"],
        "greenhouse_world": ["dense", "toxic", "corrosive"],
        "ice_world": ["none", "trace", "thin"],
        "barren_rock": ["none", "trace", "thin"],
        "scorched_rock": ["none", "trace", "toxic"],
        "iron_world": ["none", "trace"],
        "lava_world": ["trace", "toxic", "corrosive"],
    }
    return rng.choice(table.get(world_class, ["none", "trace"]))


def choose_hydrosphere(rng: random.Random, world_class: str) -> str:
    table = {
        "temperate_world": ["liquid_water", "brine", "ice"],
        "ocean_world": ["liquid_water", "liquid_water", "brine"],
        "desert_world": ["none", "brine", "ice"],
        "toxic_world": ["brine", "exotic", "none"],
        "greenhouse_world": ["none", "lava", "exotic"],
        "ice_world": ["ice", "ice", "brine"],
        "dwarf_ice": ["ice", "methane"],
        "lava_world": ["lava", "none"],
    }
    return rng.choice(table.get(world_class, ["none"]))


def estimate_habitability(world_class: str, atmosphere: str, hydrosphere: str) -> float:
    score = 0.0
    if world_class in {"temperate_world", "ocean_world", "desert_world"}:
        score += 0.35
    if atmosphere == "breathable":
        score += 0.35
    elif atmosphere in {"thin", "dense"}:
        score += 0.15
    if hydrosphere in {"liquid_water", "brine"}:
        score += 0.2
    if world_class in {"toxic_world", "greenhouse_world", "lava_world"}:
        score -= 0.25
    return clamp(score, 0.0, 1.0)


def estimate_temperature(rng: random.Random, world_class: str, zone: str) -> float:
    base_by_zone = {
        "inner": rng.uniform(360, 900),
        "habitable": rng.uniform(230, 330),
        "outer": rng.uniform(80, 220),
        "frozen": rng.uniform(15, 100),
    }
    temp = base_by_zone[zone]
    if world_class == "greenhouse_world":
        temp += rng.uniform(80, 250)
    if world_class == "lava_world":
        temp += rng.uniform(300, 700)
    return temp


def generate_moons(rng: random.Random, system_name: str, planet: SystemBody, body_offset: int) -> list[SystemBody]:
    wc = planet.physical.world_class
    if wc == "gas_giant":
        moon_count = rng.randint(4, 20)
    elif wc == "ice_giant":
        moon_count = rng.randint(3, 14)
    elif wc in {"dwarf_ice", "dwarf_rock"}:
        moon_count = rng.randint(0, 2)
    else:
        moon_count = rng.randint(0, 3)

    moons: list[SystemBody] = []
    for i in range(moon_count):
        moon_class = rng.choice(MOON_CLASSES)
        semi_major_axis = round(0.002 + i * rng.uniform(0.002, 0.006), 5)
        period_days = round(rng.uniform(1.5, 80.0) * (i + 1) ** 0.5, 2)
        key = f"{planet.key}_m{i + 1}"

        orbit = Orbit(
            parent_key=planet.key,
            semi_major_axis=semi_major_axis,
            eccentricity=round(random_eccentricity(rng), 3),
            inclination=round(random_inclination(rng), 2),
            orbital_period=period_days,
            phase=round(rng.random(), 4),
            direction="retrograde" if rng.random() < 0.08 else "prograde",
        )
        rotation = Rotation(
            rotation_period=period_days * 24.0,
            axial_tilt=round(random_axial_tilt(rng), 2),
            phase=round(rng.random(), 4),
            tidally_locked=True,
        )
        physical = generate_physical_profile(rng, moon_class, "outer", 1.0)
        moons.append(
            SystemBody(
                key=key,
                name=f"{planet.name}-{i + 1}",
                body_type="moon",
                parent_key=planet.key,
                orbit=orbit,
                rotation=rotation,
                physical=physical,
                surface_map_id=f"surface:{key}",
            )
        )
    return moons


def generate_fields(
    rng: random.Random,
    system_key: str,
    planet_keys: list[str],
    architecture: str,
    resource_rating: int,
) -> list[SpatialField]:
    fields: list[SpatialField] = []
    belt_chance = 0.35
    if architecture in {"belt_heavy_system", "post_disruption_system"}:
        belt_chance += 0.35
    if resource_rating >= 7:
        belt_chance += 0.15

    if rng.random() < belt_chance:
        inner = round(rng.uniform(2.0, 5.0), 2)
        outer = round(inner + rng.uniform(0.3, 1.2), 2)
        fields.append(
            SpatialField(
                key=f"{system_key}_belt_1",
                name=f"{system_key.title().replace('_', ' ')} Belt",
                field_type="asteroid_belt",
                parent_key=None,
                shape="belt",
                inner_radius=inner,
                outer_radius=outer,
                position=None,
                density=round(rng.uniform(0.2, 0.9), 2),
                resource_profile={
                    "common_metals": round(rng.uniform(0.4, 1.0), 2),
                    "rare_metals": round(rng.uniform(0.1, 0.8), 2),
                    "volatiles": round(rng.uniform(0.0, 0.7), 2),
                },
                hazard_profile={
                    "micrometeorites": round(rng.uniform(0.1, 0.8), 2),
                    "navigation_difficulty": round(rng.uniform(0.1, 0.7), 2),
                },
            )
        )

    return fields


def generate_artificial_objects(
    rng: random.Random,
    system_key: str,
    bodies: list[SystemBody],
    fields: list[SpatialField],
    settlement_rating: int,
    resource_rating: int,
    danger_rating: int,
) -> list[SpatialObject]:
    objects: list[SpatialObject] = []

    candidate_planets = [
        body for body in bodies
        if body.body_type == "planet" and body.physical.world_class not in {"gas_giant", "ice_giant"}
    ]
    candidate_planets.sort(key=lambda b: b.physical.habitability, reverse=True)

    if settlement_rating >= 4 and candidate_planets:
        parent = candidate_planets[0]
        objects.append(
            SpatialObject(
                key=f"{system_key}_highport_1",
                name=f"{parent.name} Highport",
                object_type="station",
                system_key=system_key,
                parent_key=parent.key,
                position=Vector3(0.0, 0.0, 0.001),
                velocity=Vector3(0.0, 0.0, 0.0),
                orbit_parent_key=parent.key,
                persistence="permanent",
                owner="local_authority",
                state={"role": "orbital_highport", "services": ["dock", "trade", "repair"]},
            )
        )

    if resource_rating >= 6 and fields:
        field = fields[0]
        objects.append(
            SpatialObject(
                key=f"{system_key}_mining_relay_1",
                name=f"{field.name} Mining Relay",
                object_type="station",
                system_key=system_key,
                parent_key=field.key,
                position=Vector3(field.inner_radius or 0.0, 0.0, 0.0),
                velocity=Vector3(0.0, 0.0, 0.0),
                orbit_parent_key=None,
                persistence="permanent",
                owner="mining_consortium",
                state={"role": "mining_relay", "services": ["dock", "ore_exchange"]},
            )
        )

    if danger_rating >= 6:
        objects.append(
            SpatialObject(
                key=f"{system_key}_warning_beacon_1",
                name="Unregistered Warning Beacon",
                object_type="beacon",
                system_key=system_key,
                parent_key=None,
                position=Vector3(
                    round(rng.uniform(-5, 5), 3),
                    round(rng.uniform(-5, 5), 3),
                    round(rng.uniform(-0.2, 0.2), 3),
                ),
                velocity=Vector3(0.0, 0.0, 0.0),
                orbit_parent_key=None,
                persistence="permanent",
                owner=None,
                state={"signal_strength": "weak", "message": "hazard_warning"},
            )
        )

    return objects


def random_eccentricity(rng: random.Random) -> float:
    roll = rng.random()
    if roll < 0.82:
        return rng.uniform(0.0, 0.12)
    if roll < 0.97:
        return rng.uniform(0.12, 0.35)
    return rng.uniform(0.35, 0.65)


def random_inclination(rng: random.Random) -> float:
    roll = rng.random()
    if roll < 0.84:
        return rng.uniform(0.0, 5.0)
    if roll < 0.98:
        return rng.uniform(5.0, 20.0)
    return rng.uniform(20.0, 60.0)


def random_axial_tilt(rng: random.Random) -> float:
    if rng.random() < 0.92:
        return rng.uniform(0.0, 35.0)
    return rng.uniform(35.0, 80.0)


def to_roman(number: int) -> str:
    pairs = [
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    result = ""
    n = number
    for value, symbol in pairs:
        while n >= value:
            result += symbol
            n -= value
    return result


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))
