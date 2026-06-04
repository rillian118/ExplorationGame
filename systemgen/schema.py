"""
Stable JSON-facing schema for generated stellar systems.

This module is intentionally independent from Evennia. The standalone generator
can create these dataclasses, export them to JSON, and the Evennia game server
can import that JSON without importing procedural-generation code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "0.2"


@dataclass
class OrbitalElements:
    """Simplified orbital metadata for a body in a 2D orbital plane."""

    parent_id: Optional[str] = None
    semi_major_axis_au: float = 0.0
    orbital_period_days: float = 0.0
    angle_degrees: float = 0.0
    eccentricity: float = 0.0
    inclination_degrees: float = 0.0


@dataclass
class BodyRecord:
    """A star, planet, moon, belt, station, anomaly, or other system body."""

    id: str
    name: str
    kind: str
    classification: str = "unknown"
    summary: str = ""
    orbit: OrbitalElements = field(default_factory=OrbitalElements)
    radius_km: Optional[float] = None
    mass_earth: Optional[float] = None
    temperature_k: Optional[float] = None
    survey_difficulty: int = 1
    survey_tags: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemRecord:
    """Top-level persistent representation of a generated stellar system."""

    name: str
    seed: int
    schema_version: str = SCHEMA_VERSION
    primary_body_id: Optional[str] = None
    bodies: List[BodyRecord] = field(default_factory=list)
    generation_notes: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemRecord":
        bodies: List[BodyRecord] = []

        for raw_body in data.get("bodies", []) or []:
            raw_orbit = raw_body.get("orbit") or {}
            body = BodyRecord(
                id=raw_body["id"],
                name=raw_body["name"],
                kind=raw_body.get("kind", "unknown"),
                classification=raw_body.get("classification", "unknown"),
                summary=raw_body.get("summary", ""),
                orbit=OrbitalElements(**raw_orbit),
                radius_km=raw_body.get("radius_km"),
                mass_earth=raw_body.get("mass_earth"),
                temperature_k=raw_body.get("temperature_k"),
                survey_difficulty=int(raw_body.get("survey_difficulty", 1)),
                survey_tags=list(raw_body.get("survey_tags", []) or []),
                children=list(raw_body.get("children", []) or []),
                extra=dict(raw_body.get("extra", {}) or {}),
            )
            bodies.append(body)

        return cls(
            name=data["name"],
            seed=int(data["seed"]),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            primary_body_id=data.get("primary_body_id"),
            bodies=bodies,
            generation_notes=list(data.get("generation_notes", []) or []),
            extra=dict(data.get("extra", {}) or {}),
        )

    def get_body(self, name_or_id: str) -> Optional[BodyRecord]:
        needle = name_or_id.strip().lower()

        for body in self.bodies:
            if body.id.lower() == needle or body.name.lower() == needle:
                return body

        return None
