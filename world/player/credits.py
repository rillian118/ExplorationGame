"""
Lightweight character credit balances.

This is intentionally attribute-backed for the first commerce slice. A later
economy can replace the storage while keeping the command-facing behavior.
"""

from __future__ import annotations

from typing import Any


CREDITS_ATTR = "credits"
DEFAULT_STARTING_CREDITS = 1000


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_credits(actor: Any) -> int:
    """Return actor credits, creating the default starting balance if unset."""
    if actor is None:
        return 0

    try:
        value = actor.attributes.get(CREDITS_ATTR, default=None)
    except Exception:
        value = None

    if value is None:
        set_credits(actor, DEFAULT_STARTING_CREDITS)
        return DEFAULT_STARTING_CREDITS

    credits = max(0, _to_int(value, DEFAULT_STARTING_CREDITS))
    if credits != value:
        set_credits(actor, credits)
    return credits


def set_credits(actor: Any, amount: int) -> int:
    """Set actor credits to a non-negative integer and return the stored value."""
    amount = max(0, int(amount))
    try:
        actor.attributes.add(CREDITS_ATTR, amount)
    except Exception:
        try:
            setattr(actor.db, CREDITS_ATTR, amount)
        except Exception:
            pass
    return amount


def grant_credits(actor: Any, amount: int) -> int:
    """Add credits to actor and return the new balance."""
    return set_credits(actor, get_credits(actor) + int(amount))


def spend_credits(actor: Any, amount: int) -> tuple[bool, int]:
    """
    Try to spend credits.

    Returns (success, resulting_or_current_balance).
    """
    amount = max(0, int(amount))
    current = get_credits(actor)
    if current < amount:
        return False, current
    return True, set_credits(actor, current - amount)


def format_credits(amount: int) -> str:
    """Return a compact credits label."""
    return f"{int(amount):,} credits"
