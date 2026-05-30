\
from __future__ import annotations

from .models import StarSystem


def validate_system(system: StarSystem) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    body_keys = set()
    for body in system.bodies:
        if body.key in body_keys:
            errors.append(f"Duplicate body key: {body.key}")
        body_keys.add(body.key)

    field_keys = {field.key for field in system.fields}
    object_keys = set()

    for body in system.bodies:
        if body.parent_key and body.parent_key not in body_keys:
            errors.append(f"{body.key} references invalid parent {body.parent_key}")

        if body.body_type == "moon":
            parent = next((b for b in system.bodies if b.key == body.parent_key), None)
            if parent and parent.body_type != "planet":
                errors.append(f"Moon {body.key} does not orbit a planet")

        if body.body_type == "star" and body.parent_key:
            errors.append(f"Star {body.key} should not have a parent in v0.2")

        if body.orbit:
            if body.orbit.orbital_period <= 0:
                errors.append(f"{body.key} has non-positive orbital period")
            if body.orbit.semi_major_axis <= 0:
                errors.append(f"{body.key} has non-positive semi-major axis")
            if body.orbit.eccentricity > 0.35:
                warnings.append(f"{body.name} has high eccentricity")
            if body.orbit.inclination > 20:
                warnings.append(f"{body.name} has high inclination")
            if body.orbit.direction == "retrograde":
                warnings.append(f"{body.name} has a retrograde orbit")

        if body.rotation and body.rotation.rotation_period <= 0:
            errors.append(f"{body.key} has non-positive rotation period")

    for obj in system.objects:
        if obj.key in object_keys:
            errors.append(f"Duplicate object key: {obj.key}")
        object_keys.add(obj.key)

        valid_parent = obj.parent_key is None or obj.parent_key in body_keys or obj.parent_key in field_keys
        if not valid_parent:
            errors.append(f"{obj.key} references invalid parent {obj.parent_key}")

        if obj.persistence == "temporary" and not obj.expires_at:
            errors.append(f"Temporary object {obj.key} lacks expires_at")

    if not any(body.physical.habitability > 0.5 for body in system.bodies):
        warnings.append("No highly habitable worlds")
    if not system.objects:
        warnings.append("No artificial objects")
    if not system.fields:
        warnings.append("No spatial fields")
    if len([b for b in system.bodies if b.body_type == "planet"]) <= 2:
        warnings.append("Sparse system")

    return errors, warnings
