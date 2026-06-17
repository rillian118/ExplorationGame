"""
Accessible survey map/readout renderers.

The survey map system deliberately separates data selection from presentation.

The same SurveyCoverage rows can be rendered as:
    - visual: compact ANSI/spatial map
    - brief: semantic screen-reader-friendly summary
    - list: directional/tile list
    - detail: focused tile report

No color or symbol is the only source of meaning.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from world.survey.map_styles import render_visual_legend, terrain_label_from_data, tile_symbol
from world.survey.models import SurveyCoverage
from world.survey.services import actor_owner_key
from world.player.preferences import get_player_preference


DEFAULT_MAP_RADIUS = 2
MAX_MAP_RADIUS = 8


@dataclass
class SurveyMapView:
    """Intermediate representation used by all map renderers."""

    owner_scope: str
    owner_id: int
    system_name: str
    body_id: str
    body_name: str
    center_x: int
    center_y: int
    radius: int
    tiles: dict[tuple[int, int], SurveyCoverage]
    requested_count: int
    known_count: int
    unknown_count: int


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Best-effort integer conversion."""
    try:
        return int(value)
    except Exception:
        return default


def _format_body(row_or_view: Any) -> str:
    """Return body label."""
    system = getattr(row_or_view, "system_name", "") or ""
    body = getattr(row_or_view, "body_name", "") or getattr(row_or_view, "body_id", "") or ""
    return f"{system}/{body}"


def _list_values(value: Any) -> list[str]:
    """Return a readable string list from a scalar or list-like value."""
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    return [str(item) for item in values if item is not None and item != ""]


def _format_values(value: Any) -> str:
    """Format scalar/list-like detail values."""
    return ", ".join(_list_values(value))


def _coverage_queryset(owner_scope: str, owner_id: int):
    return SurveyCoverage.objects.filter(
        owner_scope=owner_scope,
        owner_id=int(owner_id),
    )


def _current_ship_target(caller: Any) -> tuple[str, str, str] | None:
    """Return current ship target body, if available."""
    try:
        from world.space.shipstate import get_current_ship_for_caller, read_ship_location

        ship = get_current_ship_for_caller(caller)
        if ship is None:
            return None

        state = read_ship_location(ship) or {}
        system_name = state.get("system")
        body_id = state.get("body_id")
        body_name = state.get("body_name") or body_id

        if system_name and body_id:
            return str(system_name), str(body_id), str(body_name or body_id)
    except Exception:
        pass

    return None


def _surface_room_target(caller: Any) -> tuple[str, str, str, int | None, int | None] | None:
    """Return current surface room body/coords, if available."""
    try:
        from world.surface.models import get_surface_address

        address = get_surface_address(caller.location) or {}
        if not address:
            return None

        system_name = address.get("system_name")
        body_id = address.get("body_id")
        body_name = address.get("body_name") or body_id
        x = _safe_int(address.get("x"))
        y = _safe_int(address.get("y"))

        if system_name and body_id:
            return str(system_name), str(body_id), str(body_name or body_id), x, y
    except Exception:
        pass

    return None


def _choose_body(caller: Any, owner_scope: str, owner_id: int, body_query: str = "") -> tuple[str, str, str] | None:
    """
    Choose a body for map rendering.

    Priority:
        1. explicit body query matched against known coverage
        2. current ship target if coverage exists there
        3. current surface room if coverage exists there
        4. only body in known coverage
        5. most-covered body
    """
    qs = _coverage_queryset(owner_scope, owner_id)
    if not qs.exists():
        return None

    body_query = (body_query or "").strip().lower()

    if body_query:
        rows = list(qs.order_by("system_name", "body_id", "body_name"))
        for row in rows:
            labels = {
                str(row.body_id).lower(),
                str(row.body_name or "").lower(),
                f"{row.system_name}/{row.body_id}".lower(),
                f"{row.system_name}/{row.body_name or row.body_id}".lower(),
            }
            if body_query in labels or any(body_query in label for label in labels if label):
                return row.system_name, row.body_id, row.body_name or row.body_id

    ship_target = _current_ship_target(caller)
    if ship_target:
        system_name, body_id, body_name = ship_target
        if qs.filter(system_name=system_name, body_id=body_id).exists():
            return system_name, body_id, body_name

    surface_target = _surface_room_target(caller)
    if surface_target:
        system_name, body_id, body_name, _x, _y = surface_target
        if qs.filter(system_name=system_name, body_id=body_id).exists():
            return system_name, body_id, body_name

    counts = Counter()
    labels = {}
    for row in qs.iterator():
        key = (row.system_name, row.body_id)
        counts[key] += 1
        labels[key] = row.body_name or row.body_id

    if not counts:
        return None

    (system_name, body_id), _count = counts.most_common(1)[0]
    return system_name, body_id, labels.get((system_name, body_id), body_id)


def _choose_center(
    caller: Any,
    body_qs,
    *,
    explicit_x: int | None = None,
    explicit_y: int | None = None,
) -> tuple[int, int]:
    """Choose map center."""
    if explicit_x is not None and explicit_y is not None:
        return int(explicit_x), int(explicit_y)

    surface_target = _surface_room_target(caller)
    if surface_target:
        _system, _body_id, _body_name, x, y = surface_target
        if x is not None and y is not None:
            return int(x), int(y)

    latest = body_qs.order_by("-last_scanned_at", "-id").first()
    if latest is not None:
        return int(latest.x), int(latest.y)

    first = body_qs.order_by("x", "y").first()
    if first is not None:
        return int(first.x), int(first.y)

    return 0, 0


def _parse_map_args(args: str) -> dict[str, Any]:
    """
    Parse simple map args.

    Supported:
        survey map
        survey map visual
        survey map brief
        survey map list
        survey map center 10 25
        survey map radius 3
        survey map brief radius 3
        survey map brief center 10 25 radius 3
        survey map Astalon I
    """
    tokens = (args or "").split()
    result = {
        "mode": None,
        "explicit_mode": False,
        "center_x": None,
        "center_y": None,
        "radius": DEFAULT_MAP_RADIUS,
        "body_query": "",
    }

    body_tokens: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i].lower()

        if token in {"visual", "brief", "list", "semantic"}:
            result["mode"] = "brief" if token == "semantic" else token
            result["explicit_mode"] = True
            i += 1
            continue

        if token == "center" and i + 2 < len(tokens):
            x = _safe_int(tokens[i + 1])
            y = _safe_int(tokens[i + 2])
            if x is not None and y is not None:
                result["center_x"] = x
                result["center_y"] = y
                i += 3
                continue

        if token == "radius" and i + 1 < len(tokens):
            radius = _safe_int(tokens[i + 1])
            if radius is not None:
                result["radius"] = max(0, min(MAX_MAP_RADIUS, int(radius)))
                i += 2
                continue

        body_tokens.append(tokens[i])
        i += 1

    result["body_query"] = " ".join(body_tokens).strip()
    return result


def build_survey_map_view(
    caller: Any,
    *,
    body_query: str = "",
    center_x: int | None = None,
    center_y: int | None = None,
    radius: int = DEFAULT_MAP_RADIUS,
) -> SurveyMapView | None:
    """Build map view from caller coverage."""
    owner_scope, owner_id = actor_owner_key(caller)

    body = _choose_body(caller, owner_scope, owner_id, body_query=body_query)
    if body is None:
        return None

    system_name, body_id, body_name = body
    body_qs = _coverage_queryset(owner_scope, owner_id).filter(
        system_name=system_name,
        body_id=body_id,
    )

    cx, cy = _choose_center(caller, body_qs, explicit_x=center_x, explicit_y=center_y)
    radius = max(0, min(MAX_MAP_RADIUS, int(radius)))

    x_min = cx - radius
    x_max = cx + radius
    y_min = cy - radius
    y_max = cy + radius

    rows = body_qs.filter(x__gte=x_min, x__lte=x_max, y__gte=y_min, y__lte=y_max)
    tiles = {(int(row.x), int(row.y)): row for row in rows}

    requested_count = (radius * 2 + 1) * (radius * 2 + 1)
    known_count = len(tiles)
    unknown_count = requested_count - known_count

    return SurveyMapView(
        owner_scope=owner_scope,
        owner_id=owner_id,
        system_name=system_name,
        body_id=body_id,
        body_name=body_name,
        center_x=cx,
        center_y=cy,
        radius=radius,
        tiles=tiles,
        requested_count=requested_count,
        known_count=known_count,
        unknown_count=unknown_count,
    )


def _tile_terrain(row: SurveyCoverage | None) -> str:
    """Return terrain label for a tile."""
    if row is None:
        return "unknown"

    return terrain_label_from_data(row.data or {}, fallback=row.scan_type or "known terrain")


def _tile_symbol(row: SurveyCoverage | None, *, is_center: bool = False) -> str:
    """Return visual map symbol for a tile."""
    return tile_symbol(
        row.data if row is not None else None,
        terrain_label=_tile_terrain(row) if row is not None else None,
        is_center=is_center,
        is_unknown=row is None,
    )


def _terrain_counts(view: SurveyMapView) -> Counter:
    """Return terrain count summary."""
    counts = Counter()
    for row in view.tiles.values():
        counts[_tile_terrain(row)] += 1
    return counts


def _known_elevation_extremes(view: SurveyMapView) -> tuple[tuple[int, int, float] | None, tuple[int, int, float] | None]:
    """Return lowest and highest known elevation tiles when available."""
    points: list[tuple[int, int, float]] = []
    for (x, y), row in view.tiles.items():
        data = row.data or {}
        raw = data.get("elevation_m") or data.get("elevation")
        try:
            points.append((x, y, float(raw)))
        except Exception:
            continue

    if not points:
        return None, None

    points.sort(key=lambda item: item[2])
    return points[0], points[-1]


def _direction_from_center(view: SurveyMapView, x: int, y: int) -> str:
    """Return compass-ish relation from map center."""
    dx = int(x) - int(view.center_x)
    dy = int(y) - int(view.center_y)

    if dx == 0 and dy == 0:
        return "center"

    vertical = ""
    horizontal = ""

    # In surface coords, lower y is north, higher y is south.
    if dy < 0:
        vertical = "north"
    elif dy > 0:
        vertical = "south"

    if dx < 0:
        horizontal = "west"
    elif dx > 0:
        horizontal = "east"

    return f"{vertical}{horizontal}".strip() or "center"


def render_survey_map_visual(view: SurveyMapView) -> str:
    """Render compact visual map."""
    x_min = view.center_x - view.radius
    x_max = view.center_x + view.radius
    y_min = view.center_y - view.radius
    y_max = view.center_y + view.radius
    x_axis = " ".join(str(x % 10) for x in range(x_min, x_max + 1))

    lines = [
        f"|wSurvey Map:|n {view.system_name}/{view.body_name}",
        f"Center: {view.center_x},{view.center_y}   Radius: {view.radius}",
        f"Known: {view.known_count} of {view.requested_count} tiles",
        "",
        f"   x: {x_axis}",
    ]

    for y in range(y_min, y_max + 1):
        chars = []
        for x in range(x_min, x_max + 1):
            chars.append(
                _tile_symbol(
                    view.tiles.get((x, y)),
                    is_center=(x == view.center_x and y == view.center_y),
                )
            )
        lines.append(f"{y:>4}: " + " ".join(chars))

    lines.extend(
        [
            "",
            render_visual_legend(),
            "Axis labels show coordinate ones digits.",
            "",
            "Screen-reader alternatives: survey map brief, survey map list, survey detail <x> <y>",
        ]
    )

    return "\n".join(lines)


def render_survey_map_brief(view: SurveyMapView) -> str:
    """Render semantic map summary for screen readers."""
    counts = _terrain_counts(view)
    low, high = _known_elevation_extremes(view)

    lines = [
        f"Survey Map Brief: {view.system_name}/{view.body_name}",
        f"Region centered on {view.center_x},{view.center_y}. Radius {view.radius}.",
        f"{view.requested_count} tiles requested. {view.known_count} surveyed. {view.unknown_count} unknown.",
    ]

    if counts:
        lines.append("")
        lines.append("Known terrain:")
        for terrain, count in counts.most_common():
            lines.append(f"  {terrain}: {count} tiles")
    else:
        lines.append("")
        lines.append("No surveyed tiles in this region.")

    if high is not None:
        hx, hy, helev = high
        relation = _direction_from_center(view, hx, hy)
        lines.append("")
        lines.append(f"Highest known elevation is {helev:.0f} meters at {hx},{hy}, {relation} of center.")

    if low is not None and high is not None and low != high:
        lx, ly, lelev = low
        relation = _direction_from_center(view, lx, ly)
        lines.append(f"Lowest known elevation is {lelev:.0f} meters at {lx},{ly}, {relation} of center.")

    hazard_tiles = []
    for (x, y), row in view.tiles.items():
        data = row.data or {}
        if data.get("hazard") or data.get("hazards"):
            hazard_tiles.append((x, y))

    lines.append("")
    if hazard_tiles:
        lines.append(f"Known hazards: {len(hazard_tiles)} tile(s).")
        for x, y in sorted(hazard_tiles):
            lines.append(f"  {x},{y}: {_direction_from_center(view, x, y)} of center")
    else:
        lines.append("Known hazards: none in surveyed tiles.")

    if view.unknown_count:
        lines.append(f"Unsurveyed: {view.unknown_count} tiles in the requested region remain unknown.")

    lines.append("")
    lines.append("Use survey map list for directional tile-by-tile output.")
    lines.append("Use survey detail <x> <y> for a focused tile report.")

    return "\n".join(lines)


def render_survey_map_list(view: SurveyMapView) -> str:
    """Render tile list grouped by direction from center."""
    groups: dict[str, list[str]] = {
        "center": [],
        "north": [],
        "northeast": [],
        "east": [],
        "southeast": [],
        "south": [],
        "southwest": [],
        "west": [],
        "northwest": [],
    }

    for y in range(view.center_y - view.radius, view.center_y + view.radius + 1):
        for x in range(view.center_x - view.radius, view.center_x + view.radius + 1):
            row = view.tiles.get((x, y))
            direction = _direction_from_center(view, x, y)
            terrain = _tile_terrain(row)
            if row is None:
                entry = f"  {x},{y}: unknown"
            else:
                data = row.data or {}
                elevation = data.get("elevation_m") or data.get("elevation")
                radiation = data.get("radiation")
                parts = [terrain]
                if elevation is not None:
                    parts.append(f"elevation {elevation} m")
                if radiation is not None:
                    parts.append(f"radiation {radiation}")
                parts.append(f"resolution {row.resolution}")
                entry = f"  {x},{y}: " + ", ".join(str(part) for part in parts)
            groups.setdefault(direction, []).append(entry)

    lines = [
        f"Survey Map List: {view.system_name}/{view.body_name}",
        f"Reference point: {view.center_x},{view.center_y}. Radius {view.radius}.",
        f"Known: {view.known_count} of {view.requested_count} tiles.",
    ]

    order = ["center", "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    for direction in order:
        entries = groups.get(direction) or []
        if not entries:
            continue

        lines.append("")
        lines.append(direction.capitalize() + ":")
        lines.extend(entries)

    return "\n".join(lines)


def render_survey_detail(caller: Any, args: str) -> str:
    """
    Render focused survey detail.

    Usage:
        survey detail <x> <y>
        survey detail <x> <y> <body>
    """
    tokens = (args or "").split()
    if len(tokens) < 2:
        return "Usage: survey detail <x> <y>"

    x = _safe_int(tokens[0])
    y = _safe_int(tokens[1])
    if x is None or y is None:
        return "Usage: survey detail <x> <y>"

    body_query = " ".join(tokens[2:]).strip()
    owner_scope, owner_id = actor_owner_key(caller)
    body = _choose_body(caller, owner_scope, owner_id, body_query=body_query)

    if body is None:
        return "No survey coverage recorded yet."

    system_name, body_id, body_name = body

    rows = list(
        _coverage_queryset(owner_scope, owner_id)
        .filter(system_name=system_name, body_id=body_id, x=int(x), y=int(y))
        .order_by("scan_type")
    )

    if not rows:
        return f"No survey detail is known for {system_name}/{body_name} at {x},{y}."

    lines = [
        f"Survey Detail: {system_name}/{body_name} at {x},{y}",
    ]

    for row in rows:
        data = row.data or {}
        lines.append("")
        lines.append(f"Scan type: {row.scan_type}")
        lines.append(f"Terrain: {_tile_terrain(row)}")
        lines.append(f"Resolution: {row.resolution}")
        lines.append(f"Quality: {row.quality}")

        if data.get("scan_resolution_tier"):
            lines.append(f"Resolution tier: {data.get('scan_resolution_tier')}")

        if data.get("scan_layers"):
            lines.append(f"Scan layers: {_format_values(data.get('scan_layers'))}")

        elevation = data.get("elevation_m") if data.get("elevation_m") is not None else data.get("elevation")
        if elevation is not None:
            lines.append(f"Elevation: {elevation} meters")

        if data.get("temperature_k") is not None or data.get("temperature") is not None:
            temp = data.get("temperature_k") if data.get("temperature_k") is not None else data.get("temperature")
            lines.append(f"Temperature: {temp} K")

        if data.get("radiation") is not None:
            lines.append(f"Radiation: {data.get('radiation')}")

        gravity = data.get("gravity") if data.get("gravity") is not None else data.get("gravity_g")
        if gravity is not None:
            lines.append(f"Gravity: {gravity}g")

        if data.get("roughness") is not None:
            roughness = data.get("roughness")
            roughness_class = data.get("roughness_class")
            if roughness_class:
                lines.append(f"Roughness: {roughness} ({roughness_class})")
            else:
                lines.append(f"Roughness: {roughness}")

        bands = []
        if data.get("temperature_band"):
            bands.append(f"temperature {data.get('temperature_band')}")
        if data.get("radiation_band"):
            bands.append(f"radiation {data.get('radiation_band')}")
        if data.get("gravity_band"):
            bands.append(f"gravity {data.get('gravity_band')}")
        if bands:
            lines.append(f"Environment bands: {', '.join(bands)}")

        if data.get("feature_tags"):
            lines.append(f"Feature tags: {_format_values(data.get('feature_tags'))}")

        if data.get("hazards"):
            lines.append(f"Hazards: {_format_values(data.get('hazards'))}")
        elif data.get("hazard_level") and data.get("hazard_level") != "none":
            lines.append(f"Hazard level: {data.get('hazard_level')}")

        if data.get("hazard_score") is not None:
            lines.append(f"Hazard score: {data.get('hazard_score')}")

        if data.get("resource_signatures"):
            lines.append(f"Resource signatures: {_format_values(data.get('resource_signatures'))}")

        if data.get("anomaly_signatures"):
            lines.append(f"Anomaly signatures: {_format_values(data.get('anomaly_signatures'))}")

        traversal = data.get("traversal") if isinstance(data.get("traversal"), dict) else {}
        if traversal:
            blocked = _format_values(traversal.get("blocked_directions"))
            rough = _format_values(traversal.get("rough_directions"))
            easy = _format_values(traversal.get("easy_directions"))
            if blocked:
                lines.append(f"Blocked directions: {blocked}")
            if rough:
                lines.append(f"Rough directions: {rough}")
            if easy:
                lines.append(f"Easy directions: {easy}")

        if data.get("survey_notes"):
            lines.append(f"Survey notes: {_format_values(data.get('survey_notes'))}")

        if data.get("summary"):
            lines.append(f"Summary: {data.get('summary')}")

        if data.get("scan_method"):
            lines.append(f"Source method: {data.get('scan_method')}")

        if data.get("source_ship_name"):
            lines.append(f"Source ship: {data.get('source_ship_name')}")

        if data.get("loaded_from_dataset_name"):
            lines.append(f"Loaded from dataset: {data.get('loaded_from_dataset_name')}")

    return "\n".join(lines)


def render_survey_map(caller: Any, args: str = "") -> str:
    """
    Render a survey map in visual, brief, or list mode.
    """
    parsed = _parse_map_args(args)
    view = build_survey_map_view(
        caller,
        body_query=parsed["body_query"],
        center_x=parsed["center_x"],
        center_y=parsed["center_y"],
        radius=parsed["radius"],
    )

    if view is None:
        return "No survey coverage recorded yet."

    mode = parsed["mode"]
    if not parsed.get("explicit_mode"):
        mode = get_player_preference(caller, "survey_map", default="visual")
    if mode == "brief":
        return render_survey_map_brief(view)

    if mode == "list":
        return render_survey_map_list(view)

    return render_survey_map_visual(view)
