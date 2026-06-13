"""
Prototype ship access-control helpers.

This is the v0.1 authorization layer for ship ownership, crew, and passengers.

Access is stored on the ship object as a JSON-compatible Attribute:

    ship.attributes["ship_access"] = {
        "owner": <character object id or None>,
        "crew": [<character object ids>],
        "passenger": [<character object ids>],
    }

The older ship.attributes["owner"] field is still honored as the canonical
initial owner fallback because existing prototype ships already use it.

Roles:
    owner: Full control. Can manage access, board, land, take off, operate.
    crew: Can board, land, take off, operate.
    passenger: Can board/disembark only.
    admin: Overrides all access checks.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from evennia import search_object  # type: ignore


SHIP_ACCESS_ATTR = "ship_access"

ROLE_OWNER = "owner"
ROLE_CREW = "crew"
ROLE_PASSENGER = "passenger"

VALID_ROLES = {ROLE_OWNER, ROLE_CREW, ROLE_PASSENGER}

ROLE_ALIASES = {
    "owner": ROLE_OWNER,
    "captain": ROLE_OWNER,
    "crew": ROLE_CREW,
    "crewmember": ROLE_CREW,
    "pilot": ROLE_CREW,
    "operator": ROLE_CREW,
    "passenger": ROLE_PASSENGER,
    "guest": ROLE_PASSENGER,
    "visitor": ROLE_PASSENGER,
}

ACTION_BOARD = "board"
ACTION_DISEMBARK = "disembark"
ACTION_LAND = "land"
ACTION_TAKEOFF = "takeoff"
ACTION_OPERATE = "operate"
ACTION_MANAGE = "manage_access"
ACTION_INTERIOR = "interior"


def _actor_id(actor: Any) -> int | None:
    """Return the Evennia object id for a character/player object."""
    try:
        return int(actor.id)
    except Exception:
        return None


def _is_admin(actor: Any) -> bool:
    """Return True if actor should bypass ship access checks."""
    for perm in ("Admins", "Admin", "Developers", "Developer"):
        try:
            if actor.check_permstring(perm):
                return True
        except Exception:
            pass

    try:
        return bool(actor.permissions.check("Admins"))
    except Exception:
        return False


def normalize_ship_role(role: str) -> str | None:
    """Normalize user-facing role text to a valid ship role."""
    return ROLE_ALIASES.get((role or "").strip().lower())


def _as_int_list(value: Any) -> list[int]:
    """Normalize arbitrary stored role values to a list of ints."""
    if value is None:
        return []

    if isinstance(value, (str, bytes)):
        values = [value]
    else:
        try:
            values = list(value)
        except Exception:
            values = [value]

    result = []
    for item in values:
        try:
            result.append(int(item))
        except Exception:
            pass

    seen = set()
    deduped = []
    for item in result:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)

    return deduped


def get_ship_owner_id(ship: Any) -> int | None:
    """Return the owner id from ship_access or legacy ship.attributes['owner']."""
    if ship is None:
        return None

    try:
        access = ship.attributes.get(SHIP_ACCESS_ATTR)
    except Exception:
        access = None

    if isinstance(access, Mapping):
        owner = access.get(ROLE_OWNER)
        if owner is not None:
            try:
                return int(owner)
            except Exception:
                pass

    try:
        owner = ship.attributes.get("owner")
        if owner is not None:
            return int(owner)
    except Exception:
        pass

    return None


def read_ship_access(ship: Any) -> dict[str, Any]:
    """Read normalized ship access state."""
    if ship is None:
        return {ROLE_OWNER: None, ROLE_CREW: [], ROLE_PASSENGER: []}

    try:
        raw = ship.attributes.get(SHIP_ACCESS_ATTR)
    except Exception:
        raw = None

    data = dict(raw) if isinstance(raw, Mapping) else {}

    owner = data.get(ROLE_OWNER)
    if owner is None:
        owner = get_ship_owner_id(ship)

    try:
        owner = int(owner) if owner is not None else None
    except Exception:
        owner = None

    return {
        ROLE_OWNER: owner,
        ROLE_CREW: _as_int_list(data.get(ROLE_CREW)),
        ROLE_PASSENGER: _as_int_list(data.get(ROLE_PASSENGER)),
    }


def write_ship_access(ship: Any, access: Mapping[str, Any]) -> dict[str, Any]:
    """Write normalized ship access data and mirror owner to legacy owner attr."""
    if ship is None:
        raise ValueError("Cannot write ship access to None.")

    data = {ROLE_OWNER: None, ROLE_CREW: [], ROLE_PASSENGER: []}
    data.update(dict(access or {}))

    normalized = {
        ROLE_OWNER: None,
        ROLE_CREW: _as_int_list(data.get(ROLE_CREW)),
        ROLE_PASSENGER: _as_int_list(data.get(ROLE_PASSENGER)),
    }

    owner = data.get(ROLE_OWNER)
    if owner is not None:
        try:
            normalized[ROLE_OWNER] = int(owner)
        except Exception:
            normalized[ROLE_OWNER] = None

    owner_id = normalized[ROLE_OWNER]
    if owner_id is not None:
        normalized[ROLE_CREW] = [pid for pid in normalized[ROLE_CREW] if pid != owner_id]
        normalized[ROLE_PASSENGER] = [pid for pid in normalized[ROLE_PASSENGER] if pid != owner_id]

    crew_ids = set(normalized[ROLE_CREW])
    normalized[ROLE_PASSENGER] = [
        pid for pid in normalized[ROLE_PASSENGER] if pid not in crew_ids
    ]

    ship.attributes.add(SHIP_ACCESS_ATTR, normalized)
    ship.attributes.add("owner", normalized[ROLE_OWNER])

    return normalized


def ensure_ship_access(ship: Any, owner: Any = None) -> dict[str, Any]:
    """Ensure ship access data exists."""
    data = read_ship_access(ship)

    if data[ROLE_OWNER] is None and owner is not None:
        data[ROLE_OWNER] = _actor_id(owner)

    return write_ship_access(ship, data)


def set_ship_owner(ship: Any, actor: Any) -> dict[str, Any]:
    """Set the ship owner to actor."""
    data = read_ship_access(ship)
    data[ROLE_OWNER] = _actor_id(actor)
    return write_ship_access(ship, data)


def set_ship_role(ship: Any, actor: Any, role: str) -> dict[str, Any]:
    """Set actor's role on the ship."""
    normalized_role = normalize_ship_role(role)
    if normalized_role is None:
        raise ValueError("Role must be owner, crew, or passenger.")

    actor_id = _actor_id(actor)
    if actor_id is None:
        raise ValueError("Could not resolve target actor id.")

    data = read_ship_access(ship)

    for list_role in (ROLE_CREW, ROLE_PASSENGER):
        data[list_role] = [pid for pid in data[list_role] if pid != actor_id]

    if normalized_role == ROLE_OWNER:
        data[ROLE_OWNER] = actor_id
    else:
        data[normalized_role].append(actor_id)

    return write_ship_access(ship, data)


def remove_ship_role(ship: Any, actor: Any) -> dict[str, Any]:
    """Remove actor from ship access. Does not remove the owner by accident."""
    actor_id = _actor_id(actor)
    if actor_id is None:
        raise ValueError("Could not resolve target actor id.")

    data = read_ship_access(ship)

    if data[ROLE_OWNER] == actor_id:
        raise ValueError("Cannot remove the ship owner. Transfer ownership first.")

    data[ROLE_CREW] = [pid for pid in data[ROLE_CREW] if pid != actor_id]
    data[ROLE_PASSENGER] = [pid for pid in data[ROLE_PASSENGER] if pid != actor_id]

    return write_ship_access(ship, data)


def get_actor_ship_role(ship: Any, actor: Any) -> str | None:
    """Return actor's effective role on the ship, ignoring admin override."""
    actor_id = _actor_id(actor)
    if actor_id is None:
        return None

    data = read_ship_access(ship)

    if data[ROLE_OWNER] == actor_id:
        return ROLE_OWNER
    if actor_id in data[ROLE_CREW]:
        return ROLE_CREW
    if actor_id in data[ROLE_PASSENGER]:
        return ROLE_PASSENGER

    return None


def has_ship_access(actor: Any, ship: Any, action: str) -> bool:
    """Return whether actor can perform action on ship."""
    if actor is None or ship is None:
        return False

    if _is_admin(actor):
        return True

    role = get_actor_ship_role(ship, actor)

    if action in {ACTION_BOARD, ACTION_DISEMBARK}:
        return role in {ROLE_OWNER, ROLE_CREW, ROLE_PASSENGER}
    if action in {ACTION_LAND, ACTION_TAKEOFF, ACTION_OPERATE}:
        return role in {ROLE_OWNER, ROLE_CREW}
    if action in {ACTION_MANAGE, ACTION_INTERIOR}:
        return role == ROLE_OWNER

    return False


def require_ship_access(actor: Any, ship: Any, action: str) -> tuple[bool, str]:
    """Return (allowed, error_message)."""
    if has_ship_access(actor, ship, action):
        return True, ""

    role = get_actor_ship_role(ship, actor)
    if role:
        return False, f"Your ship role ({role}) cannot perform that action."

    return False, "You do not have access to that ship."


def _object_label_from_id(object_id: int | None) -> str:
    """Best-effort object label for an access list id."""
    if object_id is None:
        return "—"

    try:
        from evennia.objects.models import ObjectDB  # type: ignore

        obj = ObjectDB.objects.get(id=int(object_id))
        return f"{getattr(obj, 'key', obj)} #{obj.id}"
    except Exception:
        return f"#{object_id}"


def render_ship_access(ship: Any, viewer: Any = None) -> str:
    """Render a compact access roster for a ship."""
    if ship is None:
        return "No ship supplied."

    try:
        ship_name = ship.attributes.get("ship_name") or ship.key
    except Exception:
        ship_name = getattr(ship, "key", "Unknown ship")

    data = read_ship_access(ship)
    lines = [f"Ship access for {ship_name}:"]
    lines.append(f"  Owner: {_object_label_from_id(data[ROLE_OWNER])}")

    if data[ROLE_CREW]:
        lines.append("  Crew:")
        for pid in data[ROLE_CREW]:
            lines.append(f"    - {_object_label_from_id(pid)}")
    else:
        lines.append("  Crew: —")

    if data[ROLE_PASSENGER]:
        lines.append("  Passengers:")
        for pid in data[ROLE_PASSENGER]:
            lines.append(f"    - {_object_label_from_id(pid)}")
    else:
        lines.append("  Passengers: —")

    return "\n".join(lines)


def resolve_access_target(query: str):
    """Resolve a character/object by query for access assignments."""
    query = (query or "").strip()
    if not query:
        return None

    matches = search_object(query, exact=True) or []
    if matches:
        return matches[0]

    matches = search_object(query) or []
    if len(matches) == 1:
        return matches[0]

    return None


def handle_ship_access_command(caller: Any, ship: Any, rest: str) -> str:
    """Handle user-facing `ship access` subcommands."""
    if ship is None:
        return "No current ship selected. Use 'ship board <ship>' first."

    ensure_ship_access(ship)

    rest = (rest or "").strip()
    if not rest or rest.lower() in {"list", "show"}:
        allowed, error = require_ship_access(caller, ship, ACTION_MANAGE)
        if not allowed and not has_ship_access(caller, ship, ACTION_BOARD):
            return error
        return render_ship_access(ship, caller)

    parts = rest.split()
    subcmd = parts[0].lower()

    allowed, error = require_ship_access(caller, ship, ACTION_MANAGE)
    if not allowed:
        return error

    if subcmd in {"add", "set", "role"}:
        if len(parts) < 3:
            return "Usage: ship access add <player> <owner|crew|passenger>"

        target_query = " ".join(parts[1:-1])
        role = parts[-1]
        target = resolve_access_target(target_query)
        if target is None:
            return f"No character/object named '{target_query}' was found."

        try:
            set_ship_role(ship, target, role)
        except Exception as err:
            return f"Could not update ship access: {err}"

        return f"Set {getattr(target, 'key', target)} as {normalize_ship_role(role)}."

    if subcmd in {"remove", "del", "delete"}:
        if len(parts) < 2:
            return "Usage: ship access remove <player>"

        target_query = " ".join(parts[1:])
        target = resolve_access_target(target_query)
        if target is None:
            return f"No character/object named '{target_query}' was found."

        try:
            remove_ship_role(ship, target)
        except Exception as err:
            return f"Could not remove ship access: {err}"

        return f"Removed {getattr(target, 'key', target)} from ship access."

    return (
        "Usage: ship access, ship access add <player> <role>, "
        "ship access remove <player>"
    )
