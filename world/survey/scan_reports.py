"""
Survey scan report rendering.

This module turns raw scan results into player-facing reports. The output is
semantic first: useful for screen readers, and still useful for sighted players.

Hotfix v0.1a:
    - Avoid using full room descriptions as terrain labels.
    - Parse compact terrain/elevation/temperature/radiation from generated
      room summaries when discrete fields are missing.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


TERRAIN_RE = re.compile(r"terrain here is\s+([^,.]+)", re.IGNORECASE)
ELEVATION_RE = re.compile(r"elevation near\s+([0-9,]+(?:\.\d+)?)\s+meters", re.IGNORECASE)
TEMP_K_RE = re.compile(r"([0-9]+(?:\.\d+)?)\s*K\b", re.IGNORECASE)
RADIATION_RE = re.compile(r"radiation level\s+([0-9]+(?:\.\d+)?)", re.IGNORECASE)
GRAVITY_RE = re.compile(r"([0-9]+(?:\.\d+)?)g\s+gravity", re.IGNORECASE)


def _value(data: dict[str, Any], *keys: str):
    """Return first non-empty value from data."""
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def _summary_text(data: dict[str, Any]) -> str:
    """Return descriptive summary text, if present."""
    value = _value(data, "summary", "description", "desc")
    return str(value or "")


def parse_terrain_from_summary(summary: str) -> str | None:
    """Extract compact terrain label from generated room prose."""
    if not summary:
        return None

    match = TERRAIN_RE.search(summary)
    if match:
        return match.group(1).strip().lower()

    return None


def parse_number_from_summary(summary: str, pattern: re.Pattern[str]) -> float | None:
    """Extract one numeric value from summary text."""
    if not summary:
        return None

    match = pattern.search(summary)
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except Exception:
        return None


def compact_tile_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Return data with compact terrain/elevation/temp/radiation fields populated.

    This is intentionally tolerant of older rows where only `summary` was stored.
    """
    compact = dict(data or {})
    summary = _summary_text(compact)

    terrain = _value(compact, "terrain", "terrain_name", "terrain_label", "name")
    if not terrain:
        terrain = parse_terrain_from_summary(summary)
    if terrain:
        compact["terrain"] = str(terrain).strip().lower()

    if _value(compact, "elevation_m", "elevation") is None:
        elevation = parse_number_from_summary(summary, ELEVATION_RE)
        if elevation is not None:
            compact["elevation_m"] = int(elevation) if elevation.is_integer() else elevation

    if _value(compact, "temperature_k", "temperature") is None:
        temp = parse_number_from_summary(summary, TEMP_K_RE)
        if temp is not None:
            compact["temperature_k"] = int(temp) if temp.is_integer() else temp

    if compact.get("radiation") is None:
        radiation = parse_number_from_summary(summary, RADIATION_RE)
        if radiation is not None:
            compact["radiation"] = radiation

    if compact.get("gravity") is None:
        gravity = parse_number_from_summary(summary, GRAVITY_RE)
        if gravity is not None:
            compact["gravity"] = gravity

    return compact


def _terrain_label(data: dict[str, Any]) -> str:
    """Return normalized compact terrain label."""
    compact = compact_tile_data(data)
    terrain = _value(compact, "terrain", "terrain_name", "terrain_label", "name")
    if not terrain:
        return "unknown terrain"

    terrain = str(terrain).strip()
    if len(terrain) > 80:
        parsed = parse_terrain_from_summary(terrain)
        if parsed:
            return parsed
        return terrain[:77].rstrip() + "..."

    return terrain.lower()


def _float_or_none(value: Any) -> float | None:
    """Best-effort float conversion."""
    try:
        return float(value)
    except Exception:
        return None


def _format_number(value: float | int | None, *, decimals: int = 2) -> str:
    """Format numeric values without unnecessary decimals."""
    if value is None:
        return "unknown"

    try:
        value = float(value)
    except Exception:
        return str(value)

    if value.is_integer():
        return str(int(value))

    return f"{value:.{decimals}f}"


def _direction(center_x: int, center_y: int, x: int, y: int) -> str:
    """Return compass relation from scan center."""
    dx = int(x) - int(center_x)
    dy = int(y) - int(center_y)

    if dx == 0 and dy == 0:
        return "center"

    vertical = ""
    horizontal = ""

    # Lower y is north in the current surface coordinate convention.
    if dy < 0:
        vertical = "north"
    elif dy > 0:
        vertical = "south"

    if dx < 0:
        horizontal = "west"
    elif dx > 0:
        horizontal = "east"

    return f"{vertical}{horizontal}".strip() or "center"


def _numeric_extreme(records: list[dict[str, Any]], *keys: str, high: bool = True):
    """Return record with numeric max/min for one of the provided keys."""
    candidates = []
    for record in records:
        data = compact_tile_data(record.get("data") or {})
        value = _float_or_none(_value(data, *keys))
        if value is None:
            continue

        candidates.append((value, record))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[-1] if high else candidates[0]


def render_orbital_scan_report(
    *,
    ship_name: str,
    body_name: str,
    center_x: int,
    center_y: int,
    radius: int,
    records: list[dict[str, Any]],
    created_count: int,
    updated_count: int,
    limit_notes: list[str] | None = None,
) -> str:
    """
    Render a semantic orbital scan report.

    records item shape:
        {
            "x": int,
            "y": int,
            "data": dict,
            "resolution": int,
            "quality": int,
            "existed": bool,
        }
    """
    total = len(records)
    terrain_counts = Counter(_terrain_label(record.get("data") or {}) for record in records)
    resolutions = sorted({int(record.get("resolution") or 0) for record in records})
    resolution_label = ", ".join(str(value) for value in resolutions if value) or "unknown"
    qualities = sorted({int(record.get("quality") or 0) for record in records})
    quality_label = ", ".join(str(value) for value in qualities if value) or "unknown"

    lines = [
        "Orbital terrain survey complete.",
        f"Ship: {ship_name}",
        f"Body: {body_name}",
        f"Scan center: {center_x},{center_y}",
        f"Scan footprint: radius {radius}, {total} tile(s)",
        f"Scan resolution: {resolution_label}",
        f"Scan quality: {quality_label}",
        f"Coverage update: {created_count} new, {updated_count} existing updated/merged.",
    ]

    if limit_notes:
        lines.append(f"Scan limits applied: {'; '.join(limit_notes)}.")

    if terrain_counts:
        lines.append("")
        lines.append("Terrain summary:")
        for terrain, count in terrain_counts.most_common():
            lines.append(f"  {terrain}: {count} tile(s)")

    low_elev = _numeric_extreme(records, "elevation_m", "elevation", high=False)
    high_elev = _numeric_extreme(records, "elevation_m", "elevation", high=True)
    if low_elev or high_elev:
        lines.append("")
        lines.append("Elevation summary:")

        if high_elev:
            value, record = high_elev
            relation = _direction(center_x, center_y, record["x"], record["y"])
            lines.append(
                f"  Highest: {_format_number(value, decimals=0)} m at "
                f"{record['x']},{record['y']} ({relation} of center)"
            )

        if low_elev:
            value, record = low_elev
            relation = _direction(center_x, center_y, record["x"], record["y"])
            lines.append(
                f"  Lowest: {_format_number(value, decimals=0)} m at "
                f"{record['x']},{record['y']} ({relation} of center)"
            )

    max_radiation = _numeric_extreme(records, "radiation", high=True)
    if max_radiation:
        value, record = max_radiation
        relation = _direction(center_x, center_y, record["x"], record["y"])
        lines.append("")
        lines.append(
            f"Radiation summary: highest reading {_format_number(value)} "
            f"at {record['x']},{record['y']} ({relation} of center)."
        )

    low_temp = _numeric_extreme(records, "temperature_k", "temperature", high=False)
    high_temp = _numeric_extreme(records, "temperature_k", "temperature", high=True)
    if low_temp or high_temp:
        lines.append("")
        lines.append("Temperature summary:")
        if high_temp:
            value, record = high_temp
            relation = _direction(center_x, center_y, record["x"], record["y"])
            lines.append(
                f"  Highest: {_format_number(value, decimals=0)} K at "
                f"{record['x']},{record['y']} ({relation} of center)"
            )
        if low_temp:
            value, record = low_temp
            relation = _direction(center_x, center_y, record["x"], record["y"])
            lines.append(
                f"  Lowest: {_format_number(value, decimals=0)} K at "
                f"{record['x']},{record['y']} ({relation} of center)"
            )

    hazard_records = []
    for record in records:
        data = compact_tile_data(record.get("data") or {})
        if data.get("hazard") or data.get("hazards"):
            hazard_records.append(record)

    lines.append("")
    if hazard_records:
        lines.append(f"Hazard summary: {len(hazard_records)} flagged tile(s).")
        for record in hazard_records:
            relation = _direction(center_x, center_y, record["x"], record["y"])
            lines.append(f"  {record['x']},{record['y']}: {relation} of center")
    else:
        lines.append("Hazard summary: no explicit hazard flags detected in this pass.")

    lines.append("")
    lines.append("Useful follow-up commands:")
    lines.append("  survey map brief")
    lines.append("  survey map list")
    lines.append(f"  survey detail {center_x} {center_y}")
    lines.append("  survey export <name>")

    return "\n".join(lines)
