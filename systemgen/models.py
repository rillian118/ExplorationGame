"""
Evennia persistence objects for generated stellar systems.

For v0.2, each system is stored as a hidden Evennia object with JSON-compatible
system data on .db.system_data.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from evennia import DefaultObject, create_object, search_object, search_tag # type: ignore


SYSTEM_TAG = "space_system"
SYSTEM_TAG_CATEGORY = "space"
SYSTEM_KEY_PREFIX = "System: "


class SpaceSystemObject(DefaultObject):
    """Hidden object that stores one generated stellar system."""

    def at_object_creation(self):
        self.locks.add("view:false();get:false();puppet:false();edit:perm(Admin)")
        self.db.system_data = {}
        self.db.system_name = ""
        self.db.system_seed = None
        self.tags.add(SYSTEM_TAG, category=SYSTEM_TAG_CATEGORY)

    @property
    def system_data(self) -> Dict[str, Any]:
        return self.db.system_data or {}

    @system_data.setter
    def system_data(self, value: Dict[str, Any]) -> None:
        data = dict(value or {})
        self.db.system_data = data
        self.db.system_name = data.get("name", "")
        self.db.system_seed = data.get("seed")


def system_key(name: str) -> str:
    return f"{SYSTEM_KEY_PREFIX}{name.strip()}"


def read_system_data(obj: Any) -> Dict[str, Any]:
    """Safely read stored system data from a raw dict or Evennia object."""
    if not obj:
        return {}

    if isinstance(obj, dict):
        return obj

    try:
        data = obj.db.system_data
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        data = obj.attributes.get("system_data")
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        data = obj.system_data
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


def write_system_data(obj: Any, system_data: Dict[str, Any]) -> None:
    """
    Write system data directly to Evennia Attributes.

    This works even if obj is an older/stale DefaultObject rather than a
    SpaceSystemObject instance.
    """
    data = dict(system_data or {})

    obj.db.system_data = data
    obj.db.system_name = data.get("name", "")
    obj.db.system_seed = data.get("seed")

    obj.tags.add(SYSTEM_TAG, category=SYSTEM_TAG_CATEGORY)

    if data.get("name"):
        obj.tags.add(str(data["name"]), category=f"{SYSTEM_TAG_CATEGORY}:name")


def list_system_objects() -> List[Any]:
    """Return all tagged persistent system objects, populated objects first."""
    objects = list(search_tag(SYSTEM_TAG, category=SYSTEM_TAG_CATEGORY) or [])

    objects.sort(
        key=lambda obj: (
            0 if read_system_data(obj) else 1,
            str(getattr(obj, "key", "")).lower(),
        )
    )

    return objects


def find_system_object(name: str) -> Optional[Any]:
    """
    Find a persistent system object by display name or object key.

    Populated tagged objects are preferred over raw exact-key matches.
    """
    normalized = (name or "").strip()

    if not normalized:
        return None

    lower = normalized.lower()
    desired_key = system_key(normalized).lower()

    tagged_matches = []

    for obj in list_system_objects():
        data = read_system_data(obj)
        data_name = str(data.get("name", "")).lower()
        obj_key = str(getattr(obj, "key", "")).lower()

        if data_name == lower or obj_key == lower or obj_key == desired_key:
            tagged_matches.append(obj)

    populated = [obj for obj in tagged_matches if read_system_data(obj)]
    if populated:
        return populated[0]

    if tagged_matches:
        return tagged_matches[0]

    candidates = search_object(system_key(normalized), exact=True) or []

    populated_candidates = [obj for obj in candidates if read_system_data(obj)]
    if populated_candidates:
        return populated_candidates[0]

    if candidates:
        return candidates[0]

    return None


def create_or_update_system_object(system_data: Dict[str, Any]) -> Any:
    """Create or update the hidden Evennia object for a generated system."""
    name = system_data.get("name")

    if not name:
        raise ValueError("System data must include a non-empty 'name'.")

    obj = find_system_object(name)

    if obj is None:
        obj = create_object(
            "world.space.models.SpaceSystemObject",
            key=system_key(name),
            nohome=True,
        )

    write_system_data(obj, system_data)
    return obj


def body_records(system_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    return system_data.get("bodies", []) or []


def find_body(system_data: Dict[str, Any], name_or_id: str) -> Optional[Dict[str, Any]]:
    needle = name_or_id.strip().lower()

    for body in body_records(system_data):
        if str(body.get("id", "")).lower() == needle:
            return body

        if str(body.get("name", "")).lower() == needle:
            return body

    return None