from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Vector3:
    x: float
    y: float
    z: float = 0.0

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class Orbit:
    parent_key: str
    semi_major_axis: float
    eccentricity: float
    inclination: float
    orbital_period: float
    phase: float
    direction: str = "prograde"


@dataclass
class Rotation:
    rotation_period: float
    axial_tilt: float
    phase: float
    tidally_locked: bool = False


@dataclass
class PhysicalProfile:
    radius: float
    mass: float
    gravity: float
    temperature: float
    atmosphere: str
    hydrosphere: str
    world_class: str
    habitability: float
    resource_profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemBody:
    key: str
    name: str
    body_type: str
    parent_key: Optional[str]
    orbit: Optional[Orbit]
    rotation: Optional[Rotation]
    physical: PhysicalProfile
    surface_map_id: Optional[str] = None
    children: list[str] = field(default_factory=list)


@dataclass
class SpatialField:
    key: str
    name: str
    field_type: str
    parent_key: Optional[str]
    shape: str
    inner_radius: Optional[float]
    outer_radius: Optional[float]
    position: Optional[Vector3]
    density: float
    resource_profile: dict[str, Any] = field(default_factory=dict)
    hazard_profile: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialObject:
    key: str
    name: str
    object_type: str
    system_key: str
    parent_key: Optional[str]
    position: Vector3
    velocity: Vector3
    orbit_parent_key: Optional[str]
    persistence: str
    owner: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class StarSystem:
    key: str
    seed: int
    generation_version: str
    position: Vector3
    name: str
    primary_star: SystemBody
    bodies: list[SystemBody]
    fields: list[SpatialField]
    objects: list[SpatialObject]
    created_at: Optional[str] = None
    system_age: float = 0.0
    metallicity: float = 1.0
    danger_rating: int = 0
    settlement_rating: int = 0
    resource_rating: int = 0
    survey_level: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
