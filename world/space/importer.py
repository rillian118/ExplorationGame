"""Import generated system JSON into Evennia persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

from .models import create_or_update_system_object


def load_system_json(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and validate a generated stellar-system JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_system_data(data)
    return data


def validate_system_data(data: Dict[str, Any]) -> None:
    """Validate the minimum schema required by the Evennia import bridge."""
    if not isinstance(data, dict):
        raise ValueError("System JSON must contain a top-level object.")

    if not data.get("name"):
        raise ValueError("System JSON requires a non-empty 'name'.")

    if "seed" not in data:
        raise ValueError("System JSON requires a 'seed'.")

    if not isinstance(data.get("bodies", []), list):
        raise ValueError("System JSON field 'bodies' must be a list.")

    for index, body in enumerate(data.get("bodies", [])):
        if not body.get("id") or not body.get("name"):
            raise ValueError(f"Body at index {index} requires both 'id' and 'name'.")


def import_system_json(path: Union[str, Path]):
    """Load a system JSON file and persist it as a hidden Evennia object."""
    data = load_system_json(path)
    return create_or_update_system_object(data)
