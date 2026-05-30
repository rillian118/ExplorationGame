\
from __future__ import annotations

import json
from dataclasses import asdict

from .models import StarSystem, SystemBody
from .orbital import bearing_degrees, distance, position_from_orbit
from .validators import validate_system


def render_json(system: StarSystem, pretty: bool = True) -> str:
    if pretty:
        return json.dumps(system.to_dict(), indent=2)
    return json.dumps(system.to_dict(), separators=(",", ":"))


def render_summary(system: StarSystem) -> str:
    star = system.primary_star
    star_profile = star.physical.resource_profile

    lines: list[str] = [
        f"{system.name} System",
        f"Generation Version: {system.generation_version}",
        f"Seed: {system.seed}",
        "",
        "System Profile:",
        f"  Age: {system.system_age} billion years",
        f"  Metallicity: {system.metallicity} solar",
        f"  Resource Rating: {system.resource_rating}/10",
        f"  Settlement Rating: {system.settlement_rating}/10",
        f"  Danger Rating: {system.danger_rating}/10",
        "",
        "Primary Star:",
        f"  {star.name}, {star_profile.get('stellar_label', star.physical.world_class)}",
        f"  Color: {star_profile.get('color', 'unknown')}",
        f"  Mass: {star.physical.mass} solar",
        f"  Luminosity: {star_profile.get('luminosity_solar')} solar",
        f"  Habitable Zone: {star_profile.get('habitable_zone_inner')}-{star_profile.get('habitable_zone_outer')} AU",
        "",
        "Major Bodies:",
    ]

    planets = [body for body in system.bodies if body.body_type == "planet"]
    for planet in planets:
        moon_count = len([body for body in system.bodies if body.parent_key == planet.key and body.body_type == "moon"])
        lines.extend(render_body_summary(planet, moon_count))

    if system.fields:
        lines.extend(["", "Fields:"])
        for field in system.fields:
            range_text = ""
            if field.inner_radius is not None and field.outer_radius is not None:
                range_text = f"{field.inner_radius}-{field.outer_radius} AU"
            lines.extend([
                f"  {field.name}",
                f"    Type: {field.field_type}",
                f"    Shape: {field.shape}",
                f"    Range: {range_text or 'localized'}",
                f"    Density: {field.density}",
                f"    Resources: {', '.join(k for k, v in field.resource_profile.items() if v)}",
            ])

    if system.objects:
        lines.extend(["", "Artificial Objects:"])
        for obj in system.objects:
            parent = obj.parent_key or "free-space"
            lines.extend([
                f"  {obj.name}",
                f"    Type: {obj.object_type}",
                f"    Parent: {parent}",
                f"    Persistence: {obj.persistence}",
            ])

    errors, warnings = validate_system(system)
    if errors or warnings:
        lines.extend(["", "Validation:"])
        for error in errors:
            lines.append(f"  ERROR: {error}")
        for warning in warnings:
            lines.append(f"  Warning: {warning}")

    return "\n".join(lines)


def render_body_summary(body: SystemBody, moon_count: int) -> list[str]:
    orbit = body.orbit
    rotation = body.rotation

    lines = [
        f"  {body.name}",
        f"    Class: {body.physical.world_class}",
    ]

    if orbit:
        lines.extend([
            f"    Orbit: {orbit.semi_major_axis} AU",
            f"    Period: {orbit.orbital_period} days",
            f"    Eccentricity: {orbit.eccentricity}",
            f"    Inclination: {orbit.inclination} degrees",
        ])

    if rotation:
        lock = " [tidally locked]" if rotation.tidally_locked else ""
        lines.append(f"    Rotation: {rotation.rotation_period} hours{lock}")

    lines.extend([
        f"    Atmosphere: {body.physical.atmosphere}",
        f"    Hydrosphere: {body.physical.hydrosphere}",
        f"    Gravity: {body.physical.gravity}g",
        f"    Habitability: {body.physical.habitability}",
        f"    Moons: {moon_count}",
    ])

    return lines


def render_mud(system: StarSystem, elapsed_days: float = 0.0) -> str:
    origin = system.primary_star

    lines: list[str] = [
        f"{system.name} System",
        f"Primary: {system.primary_star.name}, {system.primary_star.physical.resource_profile.get('stellar_label')}",
        "",
        "Major contacts:",
    ]

    star_pos = None
    planets = [body for body in system.bodies if body.body_type == "planet"]
    for planet in planets:
        if planet.orbit:
            pos = position_from_orbit(planet.orbit, elapsed_days)
            bearing = int(round(bearing_degrees(star_pos or pos.__class__(0, 0, 0), pos)))
            range_au = distance(pos.__class__(0, 0, 0), pos)
        else:
            bearing = 0
            range_au = 0.0

        zone = classify_mud_zone(system, planet)
        lines.append(
            f"  {planet.name:<16} {planet.physical.world_class:<22} {zone:<14} "
            f"bearing {bearing:03d} range {range_au:.2f} AU"
        )

    for field in system.fields:
        if field.field_type == "asteroid_belt":
            lines.append(
                f"  {field.name:<16} asteroid belt          outer system   diffuse"
            )

    if system.objects:
        lines.extend(["", "Artificial contacts:"])
        for obj in system.objects:
            parent = obj.parent_key or "free-space"
            lines.append(f"  {obj.name:<28} {obj.object_type:<10} {parent}")

    return "\n".join(lines)


def classify_mud_zone(system: StarSystem, body: SystemBody) -> str:
    if not body.orbit:
        return "local"
    hz_inner = system.primary_star.physical.resource_profile["habitable_zone_inner"]
    hz_outer = system.primary_star.physical.resource_profile["habitable_zone_outer"]
    orbit = body.orbit.semi_major_axis
    if orbit < hz_inner:
        return "inner orbit"
    if hz_inner <= orbit <= hz_outer:
        return "habitable zone"
    return "outer orbit"
