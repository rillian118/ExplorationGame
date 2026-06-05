"""Ship objects and location-state helpers for space gameplay.

Ships are stored as persistent Evennia objects. Their location state is a small
JSON-compatible Attribute describing where the ship is in the generated space
model: in-system, orbiting, landed, docked, or in transit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from evennia import DefaultObject, create_object, search_object, search_tag  # type: ignore

from .models import find_body, find_system_object, read_system_data


SHIP_TAG = "space_ship"
SHIP_TAG_CATEGORY = "space"
SHIP_KEY_PREFIX = "Ship: "


VALID_LOCATION_MODES = {
    "unknown",
    "in_system",
    "orbiting",
    "landed",
    "docked",
    "in_transit",
}


UNLANDABLE_CLASSIFICATION_TERMS = {
    "gas giant",
    "sub-neptune",
    "sub neptune",
    "ice giant",
}


def ship_key(name: str) -> str:
    """Return the persistent object key used for a ship object."""
    return f"{SHIP_KEY_PREFIX}{name.strip()}"


def default_location_state() -> Dict[str, Any]:
    """Return an empty/default ship location state."""
    return {
        "mode": "unknown",
        "system": None,
        "body_id": None,
        "body_name": None,
        "site_id": None,
        "dock_id": None,
        "coordinates": None,
        "position": None,
        "notes": [],
    }


class SpaceShipObject(DefaultObject):
    """Persistent ship entity.

    The interior rooms of a ship can be normal Evennia rooms. This object is the
    movable ship entity that stores navigation/location state.
    """

    def at_object_creation(self):
        self.locks.add("get:false();puppet:false();edit:perm(Admin)")
        self.tags.add(SHIP_TAG, category=SHIP_TAG_CATEGORY)
        self.attributes.add("ship_name", self.key.replace(SHIP_KEY_PREFIX, "", 1))
        self.attributes.add("location_state", default_location_state())
        self.attributes.add("bridge_room", None)
        self.attributes.add("airlock_room", None)
        self.attributes.add("owner", None)

    @property
    def ship_name(self) -> str:
        value = self.attributes.get("ship_name")
        return str(value or self.key.replace(SHIP_KEY_PREFIX, "", 1))

    @property
    def location_state(self) -> Dict[str, Any]:
        return read_ship_location(self)

    @location_state.setter
    def location_state(self, value: Dict[str, Any]) -> None:
        write_ship_location(self, value)


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def read_ship_location(ship: Any) -> Dict[str, Any]:
    """Read a ship location state from an Evennia object or raw mapping."""
    if ship is None:
        return default_location_state()

    if isinstance(ship, Mapping):
        state = dict(ship)
        merged = default_location_state()
        merged.update(state)
        return merged

    for reader in (
        lambda obj: obj.attributes.get("location_state"),
        lambda obj: obj.db.location_state,
    ):
        try:
            state = reader(ship)
            if isinstance(state, Mapping):
                merged = default_location_state()
                merged.update(dict(state))
                return merged
        except Exception:
            pass

    return default_location_state()


def write_ship_location(ship: Any, state: Dict[str, Any]) -> None:
    """Write a normalized location state onto a ship object."""
    if ship is None:
        raise ValueError("Cannot write location state to None.")

    merged = default_location_state()
    merged.update(dict(state or {}))

    mode = str(merged.get("mode") or "unknown")
    if mode not in VALID_LOCATION_MODES:
        raise ValueError(f"Invalid ship location mode: {mode}")

    merged["mode"] = mode
    ship.attributes.add("location_state", merged)


def list_ship_objects() -> List[Any]:
    """Return all tagged ship objects."""
    ships = list(search_tag(SHIP_TAG, category=SHIP_TAG_CATEGORY) or [])
    ships.sort(key=lambda obj: str(getattr(obj, "key", "")).lower())
    return ships


def find_ship(query: str) -> Optional[Any]:
    """Find a ship by dbref, key, bare name, or stored ship_name."""
    query = (query or "").strip()
    if not query:
        return None

    direct = search_object(query, exact=True) or []
    for obj in direct:
        try:
            if obj.tags.has(SHIP_TAG, category=SHIP_TAG_CATEGORY):
                return obj
        except Exception:
            pass

    prefixed = search_object(ship_key(query), exact=True) or []
    for obj in prefixed:
        try:
            if obj.tags.has(SHIP_TAG, category=SHIP_TAG_CATEGORY):
                return obj
        except Exception:
            pass

    lower = query.lower()
    desired_key = ship_key(query).lower()
    for ship in list_ship_objects():
        ship_name = str(ship.attributes.get("ship_name") or "").lower()
        obj_key = str(getattr(ship, "key", "")).lower()
        if lower in {ship_name, obj_key} or obj_key == desired_key:
            return ship

    return None


def create_ship(name: str, owner: Any = None) -> Any:
    """Create a persistent ship object, or return the existing one."""
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Ship name is required.")

    existing = find_ship(clean_name)
    if existing is not None:
        return existing

    ship = create_object(
        "world.space.shipstate.SpaceShipObject",
        key=ship_key(clean_name),
        nohome=True,
    )
    ship.tags.add(SHIP_TAG, category=SHIP_TAG_CATEGORY)
    ship.attributes.add("ship_name", clean_name)
    ship.attributes.add("location_state", default_location_state())

    if owner is not None:
        ship.attributes.add("owner", getattr(owner, "id", None))

    return ship


def _resolve_system_and_body(system_name: str, body_query: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    system_obj = find_system_object(system_name)
    if system_obj is None:
        raise ValueError(f"No imported system named '{system_name}' was found.")

    system_data = read_system_data(system_obj)
    if not system_data:
        raise ValueError(f"System '{system_name}' has no stored system data.")

    body = find_body(system_data, body_query)
    if body is None:
        raise ValueError(f"No body named '{body_query}' was found in {system_data.get('name')}.")

    return system_data, body


def is_body_physically_landable(body: Dict[str, Any]) -> bool:
    """Return whether this body can be used for prototype surface landing."""
    kind = str(body.get("kind", "")).lower()
    classification = str(body.get("classification", "")).lower()

    if kind not in {"planet", "moon"}:
        return False

    return not any(term in classification for term in UNLANDABLE_CLASSIFICATION_TERMS)


def set_ship_in_system(ship: Any, system_name: str) -> Dict[str, Any]:
    """Set a ship to open in-system space."""
    system_obj = find_system_object(system_name)
    if system_obj is None:
        raise ValueError(f"No imported system named '{system_name}' was found.")

    system_data = read_system_data(system_obj)
    if not system_data:
        raise ValueError(f"System '{system_name}' has no stored system data.")

    state = default_location_state()
    state.update(
        {
            "mode": "in_system",
            "system": system_data.get("name"),
            "notes": ["Ship is present in local system space."],
        }
    )
    write_ship_location(ship, state)
    return state


def set_ship_orbiting(ship: Any, system_name: str, body_query: str) -> Dict[str, Any]:
    """Set a ship to orbit a body in a generated system."""
    system_data, body = _resolve_system_and_body(system_name, body_query)

    state = default_location_state()
    state.update(
        {
            "mode": "orbiting",
            "system": system_data.get("name"),
            "body_id": body.get("id"),
            "body_name": body.get("name"),
            "notes": [f"Ship is in stable orbit around {body.get('name')}."]
        }
    )
    write_ship_location(ship, state)
    return state


def set_ship_landed(ship: Any, system_name: str, body_query: str, x: int, y: int) -> Dict[str, Any]:
    """Set a ship to a landed prototype state at a generated surface coordinate."""
    system_data, body = _resolve_system_and_body(system_name, body_query)

    if not is_body_physically_landable(body):
        raise ValueError(f"{body.get('name', body_query)} is not landable by the prototype surface system.")

    state = default_location_state()
    state.update(
        {
            "mode": "landed",
            "system": system_data.get("name"),
            "body_id": body.get("id"),
            "body_name": body.get("name"),
            "coordinates": {"x": int(x), "y": int(y)},
            "notes": [f"Ship is landed on {body.get('name')} at surface coordinates {int(x)}, {int(y)}."],
        }
    )
    write_ship_location(ship, state)
    return state


def set_current_ship_for_caller(caller: Any, ship: Any) -> None:
    """Remember a caller's active/current ship by dbref."""
    caller.attributes.add("current_ship", getattr(ship, "dbref", None))


def clear_current_ship_for_caller(caller: Any) -> None:
    """Clear the caller's active/current ship."""
    caller.attributes.remove("current_ship")


def get_current_ship_for_caller(caller: Any) -> Optional[Any]:
    """Resolve a caller's current ship, if one has been selected."""
    try:
        current = caller.attributes.get("current_ship")
    except Exception:
        current = None

    if current:
        found = find_ship(str(current))
        if found is not None:
            return found

    # Future hook: if caller.location is an interior ship room, that room may
    # store ship_dbref or ship_id. This keeps the API ready for real interiors.
    try:
        room = caller.location
        room_ship = room.attributes.get("ship_dbref") or room.attributes.get("ship_id")
    except Exception:
        room_ship = None

    if room_ship:
        return find_ship(str(room_ship))

    return None


def get_current_system_name_for_caller(caller: Any) -> Optional[str]:
    """Return the caller's current ship system, if available."""
    ship = get_current_ship_for_caller(caller)
    if ship is None:
        return None

    state = read_ship_location(ship)
    system_name = state.get("system")
    return str(system_name) if system_name else None


def format_ship_status(ship: Any) -> str:
    """Format a player-facing ship status summary."""
    state = read_ship_location(ship)
    name = ship.attributes.get("ship_name") or getattr(ship, "key", "Unknown ship")

    lines = [f"|w{name}|n", f"Object: {getattr(ship, 'dbref', 'unknown')}"]
    mode = state.get("mode") or "unknown"
    lines.append(f"Location mode: {mode}")

    if state.get("system"):
        lines.append(f"System: {state.get('system')}")

    if state.get("body_name"):
        lines.append(f"Body: {state.get('body_name')} ({state.get('body_id')})")
    elif state.get("body_id"):
        lines.append(f"Body ID: {state.get('body_id')}")

    coordinates = _as_dict(state.get("coordinates"))
    if coordinates:
        lines.append(f"Surface coordinates: {coordinates.get('x')}, {coordinates.get('y')}")

    if state.get("site_id"):
        lines.append(f"Site: {state.get('site_id')}")

    if state.get("dock_id"):
        lines.append(f"Dock: {state.get('dock_id')}")

    notes = state.get("notes") or []
    if notes:
        lines.append("")
        lines.append("Notes:")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)
