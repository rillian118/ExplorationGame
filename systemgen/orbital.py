\
from __future__ import annotations

import math

from .models import Orbit, Rotation, Vector3


TAU = math.tau


def orbital_period_years(semi_major_axis_au: float, parent_mass_solar: float) -> float:
    """Simplified Keplerian period in Earth years."""
    if semi_major_axis_au <= 0:
        raise ValueError("semi_major_axis_au must be positive")
    if parent_mass_solar <= 0:
        raise ValueError("parent_mass_solar must be positive")
    return math.sqrt(semi_major_axis_au ** 3 / parent_mass_solar)


def position_from_orbit(orbit: Orbit, elapsed_days: float) -> Vector3:
    """
    Calculate an approximate 3D position from stored orbit data.

    v0.2 intentionally uses a lightweight ephemeris:
    - circular base orbit
    - eccentricity stored and lightly applied
    - inclination used to offset z
    """
    period_days = max(orbit.orbital_period, 0.0001)
    direction = -1.0 if orbit.direction == "retrograde" else 1.0
    angle = (orbit.phase * TAU) + direction * TAU * (elapsed_days / period_days)

    # Lightweight eccentricity approximation.
    radius = orbit.semi_major_axis * (1.0 - orbit.eccentricity * math.cos(angle))
    x = math.cos(angle) * radius
    y = math.sin(angle) * radius

    inc = math.radians(orbit.inclination)
    z = math.sin(inc) * y

    return Vector3(x=x, y=y * math.cos(inc), z=z)


def local_day_fraction(rotation: Rotation, elapsed_hours: float) -> float:
    """Return local rotation phase as a 0.0-1.0 fraction."""
    period = max(rotation.rotation_period, 0.0001)
    return (rotation.phase + elapsed_hours / period) % 1.0


def bearing_degrees(origin: Vector3, target: Vector3) -> float:
    dx = target.x - origin.x
    dy = target.y - origin.y
    angle = math.degrees(math.atan2(dx, dy))
    return angle % 360.0


def distance(origin: Vector3, target: Vector3) -> float:
    dx = target.x - origin.x
    dy = target.y - origin.y
    dz = target.z - origin.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
