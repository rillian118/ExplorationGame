#!/usr/bin/env python3
"""
planetgen_prototype.py

Standalone prototype planetary surface generator for an Exploration MUD-style game.

This is intentionally not a full scientific simulation. It creates a plausible,
deterministic, gameable planetary map from a seed and a small PlanetProfile.

Core features:
- 1000x500-capable equirectangular/gameplay grid
- deterministic seed-based generation
- elevation, temperature, moisture, terrain, liquid, bedrock, hazard layers
- simple pseudo-tectonic ridges
- basic sea-level selection by target liquid coverage
- ASCII rendering for terminal/MUD-style preview
- optional ANSI color rendering for MUD/terminal clients
- 256-color topographic palette for improved terrain readability
- compact compressed .npz export

Dependencies:
    pip install numpy

Optional:
    pip install colorama
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np


# -----------------------------
# Data models
# -----------------------------

@dataclass(frozen=True)
class PlanetProfile:
    seed: int = 12345
    name: str = "Prototype"
    width: int = 200
    height: int = 100

    radius_km: float = 6371.0
    gravity_g: float = 1.0
    age_gyr: float = 4.5

    solar_flux: float = 1.0
    atmosphere_pressure_atm: float = 1.0
    greenhouse_factor: float = 1.0

    tectonic_activity: float = 0.65
    volcanic_activity: float = 0.25

    liquid: str = "water"
    liquid_coverage_target: float = 0.62

    # For first prototype only; later this can come from star/orbit models.
    average_surface_temp_k: float = 288.0


class TerrainCode:
    DEEP_LIQUID = 1
    SHALLOW_LIQUID = 2
    ICE = 3
    LOWLAND = 4
    PLAINS = 5
    HIGHLANDS = 6
    MOUNTAINS = 7
    DESERT = 8
    VOLCANIC = 9
    POLAR = 10


class BedrockCode:
    BASALTIC = 1
    GRANITIC = 2
    SEDIMENTARY = 3
    METAMORPHIC = 4
    VOLCANIC = 5
    IMPACT_MELT = 6


TERRAIN_SYMBOLS: Dict[int, str] = {
    TerrainCode.DEEP_LIQUID: "~",
    TerrainCode.SHALLOW_LIQUID: ",",
    TerrainCode.ICE: "*",
    TerrainCode.LOWLAND: ".",
    TerrainCode.PLAINS: ".",
    TerrainCode.HIGHLANDS: "#",
    TerrainCode.MOUNTAINS: "^",
    TerrainCode.DESERT: ":",
    TerrainCode.VOLCANIC: "!",
    TerrainCode.POLAR: "*",
}



ANSI_RESET = "[0m"
ANSI_BLACK_FG = "[30m"

# 256-color topographic palette:
# - blues for water
# - khaki/tan/brown -> gray -> white for increasing land altitude
# - avoids strong greens to reduce the implication of vegetation/life
TERRAIN_FG_COLORS: Dict[int, str] = {
    TerrainCode.DEEP_LIQUID: "[38;5;18m",     # deep ocean blue
    TerrainCode.SHALLOW_LIQUID: "[38;5;25m",  # shallower blue
    TerrainCode.ICE: "[38;5;255m",            # white ice
    TerrainCode.LOWLAND: "[38;5;187m",        # pale khaki
    TerrainCode.PLAINS: "[38;5;180m",         # tan
    TerrainCode.HIGHLANDS: "[38;5;137m",      # brown
    TerrainCode.MOUNTAINS: "[38;5;244m",      # gray
    TerrainCode.DESERT: "[38;5;222m",         # sand
    TerrainCode.VOLCANIC: "[38;5;166m",       # rust/orange-red
    TerrainCode.POLAR: "[38;5;251m",          # cold pale gray
}

TERRAIN_BG_COLORS: Dict[int, str] = {
    TerrainCode.DEEP_LIQUID: "[48;5;18m",     # deep ocean blue
    TerrainCode.SHALLOW_LIQUID: "[48;5;25m",  # shallower blue
    TerrainCode.ICE: "[48;5;255m",            # white ice
    TerrainCode.LOWLAND: "[48;5;187m",        # pale khaki
    TerrainCode.PLAINS: "[48;5;180m",         # tan
    TerrainCode.HIGHLANDS: "[48;5;137m",      # brown
    TerrainCode.MOUNTAINS: "[48;5;244m",      # gray
    TerrainCode.DESERT: "[48;5;222m",         # sand
    TerrainCode.VOLCANIC: "[48;5;166m",       # rust/orange-red
    TerrainCode.POLAR: "[48;5;251m",          # cold pale gray
}

TERRAIN_NAMES: Dict[int, str] = {
    TerrainCode.DEEP_LIQUID: "deep liquid",
    TerrainCode.SHALLOW_LIQUID: "shallow liquid",
    TerrainCode.ICE: "ice",
    TerrainCode.LOWLAND: "lowland",
    TerrainCode.PLAINS: "plains",
    TerrainCode.HIGHLANDS: "highlands",
    TerrainCode.MOUNTAINS: "mountains",
    TerrainCode.DESERT: "desert",
    TerrainCode.VOLCANIC: "volcanic",
    TerrainCode.POLAR: "polar",
}


MAP_MODES = (
    "terrain",
    "elevation",
    "temperature",
    "moisture",
    "hazard",
    "volcanic",
    "liquid",
    "bedrock",
)

BEDROCK_NAMES: Dict[int, str] = {
    BedrockCode.BASALTIC: "basaltic",
    BedrockCode.GRANITIC: "granitic",
    BedrockCode.SEDIMENTARY: "sedimentary",
    BedrockCode.METAMORPHIC: "metamorphic",
    BedrockCode.VOLCANIC: "volcanic",
    BedrockCode.IMPACT_MELT: "impact melt",
}

BEDROCK_SYMBOLS: Dict[int, str] = {
    BedrockCode.BASALTIC: "b",
    BedrockCode.GRANITIC: "g",
    BedrockCode.SEDIMENTARY: "s",
    BedrockCode.METAMORPHIC: "m",
    BedrockCode.VOLCANIC: "v",
    BedrockCode.IMPACT_MELT: "x",
}

BEDROCK_BG_COLORS: Dict[int, str] = {
    BedrockCode.BASALTIC: "\033[48;5;240m",
    BedrockCode.GRANITIC: "\033[48;5;250m",
    BedrockCode.SEDIMENTARY: "\033[48;5;180m",
    BedrockCode.METAMORPHIC: "\033[48;5;95m",
    BedrockCode.VOLCANIC: "\033[48;5;166m",
    BedrockCode.IMPACT_MELT: "\033[48;5;201m",
}

BEDROCK_FG_COLORS: Dict[int, str] = {
    BedrockCode.BASALTIC: "\033[38;5;240m",
    BedrockCode.GRANITIC: "\033[38;5;250m",
    BedrockCode.SEDIMENTARY: "\033[38;5;180m",
    BedrockCode.METAMORPHIC: "\033[38;5;95m",
    BedrockCode.VOLCANIC: "\033[38;5;166m",
    BedrockCode.IMPACT_MELT: "\033[38;5;201m",
}



def colorize_terrain_text(
    text: str,
    terrain_code: int,
    color: bool,
    color_style: str = "bg",
) -> str:
    """Apply the terrain color to arbitrary text when ANSI color is enabled."""
    if not color:
        return text

    code = int(terrain_code)

    if color_style == "bg":
        ansi = TERRAIN_BG_COLORS.get(code, "")
        if not ansi:
            return text
        return f"{ansi}{ANSI_BLACK_FG}{text}{ANSI_RESET}"

    ansi = TERRAIN_FG_COLORS.get(code, "")
    if not ansi:
        return text
    return f"{ansi}{text}{ANSI_RESET}"


def terrain_symbol(
    terrain_code: int,
    color: bool = False,
    color_style: str = "bg",
) -> str:
    """Return a terrain symbol, optionally ANSI-colored."""
    code = int(terrain_code)
    symbol = TERRAIN_SYMBOLS.get(code, "?")
    return colorize_terrain_text(symbol, code, color, color_style)


def terrain_name(
    terrain_code: int,
    color: bool = False,
    color_style: str = "bg",
) -> str:
    """Return a terrain display name, optionally ANSI-colored."""
    code = int(terrain_code)
    name = TERRAIN_NAMES.get(code, f"code_{code}")
    return colorize_terrain_text(name, code, color, color_style)



# -----------------------------
# Utility functions
# -----------------------------

def normalize(a: np.ndarray) -> np.ndarray:
    """Normalize array to 0..1, robust against constant arrays."""
    amin = float(np.min(a))
    amax = float(np.max(a))
    if math.isclose(amin, amax):
        return np.zeros_like(a, dtype=np.float32)
    return ((a - amin) / (amax - amin)).astype(np.float32)


def smooth_2d(a: np.ndarray, passes: int = 1) -> np.ndarray:
    """
    Cheap neighbor averaging. Wraps east/west, clamps north/south.
    This is intentionally simple and dependency-free.
    """
    out = a.astype(np.float32, copy=True)
    for _ in range(passes):
        north = np.vstack([out[0:1, :], out[:-1, :]])
        south = np.vstack([out[1:, :], out[-1:, :]])
        west = np.roll(out, 1, axis=1)
        east = np.roll(out, -1, axis=1)
        out = (out * 4.0 + north + south + west + east) / 8.0
    return out.astype(np.float32)


def value_noise(
    rng: np.random.Generator,
    height: int,
    width: int,
    coarse_h: int,
    coarse_w: int,
    smooth_passes: int,
) -> np.ndarray:
    """
    Create simple low-frequency noise by sampling a coarse grid and upscaling.
    Dependency-free alternative to Perlin/Simplex noise.
    """
    coarse = rng.random((coarse_h, coarse_w), dtype=np.float32)

    # Upscale by nearest neighbor, then smooth heavily.
    scale_y = int(math.ceil(height / coarse_h))
    scale_x = int(math.ceil(width / coarse_w))
    up = np.kron(coarse, np.ones((scale_y, scale_x), dtype=np.float32))
    up = up[:height, :width]
    return normalize(smooth_2d(up, smooth_passes))


def fractal_noise(
    rng: np.random.Generator,
    height: int,
    width: int,
    octaves: Tuple[Tuple[int, int, float, int], ...],
) -> np.ndarray:
    """
    Combine multiple value-noise octaves.

    octave tuple:
        (coarse_h, coarse_w, weight, smooth_passes)
    """
    acc = np.zeros((height, width), dtype=np.float32)
    total_weight = 0.0

    for coarse_h, coarse_w, weight, smooth_passes in octaves:
        acc += value_noise(rng, height, width, coarse_h, coarse_w, smooth_passes) * weight
        total_weight += weight

    acc /= max(total_weight, 0.0001)
    return normalize(acc)


def latitude_grid(height: int, width: int) -> np.ndarray:
    """Return approximate latitude in radians for each cell, north=+pi/2, south=-pi/2."""
    ys = np.linspace(1.0, -1.0, height, dtype=np.float32)
    lat = ys[:, None] * (math.pi / 2.0)
    return np.repeat(lat, width, axis=1)


def choose_sea_level(elevation: np.ndarray, coverage: float) -> float:
    """Choose elevation threshold so roughly coverage fraction is liquid."""
    coverage = float(np.clip(coverage, 0.0, 0.95))
    return float(np.quantile(elevation, coverage))


# -----------------------------
# Generation passes
# -----------------------------

def generate_base_elevation(profile: PlanetProfile, rng: np.random.Generator) -> np.ndarray:
    """
    Generate base elevation with continent-scale and regional variation.

    Output is normalized 0..1 before tectonics.
    """
    h, w = profile.height, profile.width

    continents = fractal_noise(
        rng, h, w,
        octaves=(
            (5, 10, 0.55, 20),
            (10, 20, 0.30, 10),
            (25, 50, 0.15, 4),
        ),
    )

    regional = fractal_noise(
        rng, h, w,
        octaves=(
            (20, 40, 0.7, 7),
            (50, 100, 0.3, 3),
        ),
    )

    elevation = 0.72 * continents + 0.28 * regional
    elevation = normalize(elevation)

    # Slightly depress polar regions for common ice/ocean basins, but do not overdo it.
    lat = latitude_grid(h, w)
    polar_factor = np.abs(np.sin(lat))
    elevation -= 0.06 * polar_factor.astype(np.float32)

    return normalize(elevation)


def apply_pseudo_tectonics(
    elevation: np.ndarray,
    profile: PlanetProfile,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Add pseudo-tectonic ridges using random great-circle-ish vertical/horizontal/diagonal bands.
    Returns modified elevation and a boundary intensity map.

    This is a gameplay approximation, not real plate mechanics.
    """
    h, w = elevation.shape
    boundary = np.zeros_like(elevation, dtype=np.float32)

    activity = float(np.clip(profile.tectonic_activity, 0.0, 1.0))
    plate_count = int(round(6 + activity * 22))

    yy, xx = np.mgrid[0:h, 0:w]

    for _ in range(plate_count):
        # Random line in normalized map coordinates.
        angle = rng.uniform(0, math.pi)
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, h)

        # Distance from line, with east/west wrap approximation by checking shifts.
        dx = xx - cx
        dy = yy - cy
        dist = np.abs(dx * math.sin(angle) - dy * math.cos(angle))

        # Try wrapped copies so boundaries can cross the map seam.
        dx_west = (xx - (cx - w))
        dx_east = (xx - (cx + w))
        dist = np.minimum(dist, np.abs(dx_west * math.sin(angle) - dy * math.cos(angle)))
        dist = np.minimum(dist, np.abs(dx_east * math.sin(angle) - dy * math.cos(angle)))

        width_cells = rng.uniform(2.0, 8.0 + activity * 12.0)
        ridge = np.exp(-(dist ** 2) / (2 * width_cells ** 2)).astype(np.float32)

        kind = rng.choice(["convergent", "divergent", "transform"], p=[0.48, 0.27, 0.25])
        strength = rng.uniform(0.04, 0.14) * activity

        if kind == "convergent":
            elevation += ridge * strength
            boundary += ridge * (0.7 + strength)
        elif kind == "divergent":
            elevation -= ridge * strength * 0.55
            boundary += ridge * (0.45 + strength)
        else:
            # Transform: roughen rather than purely raise/lower.
            rough = rng.normal(0.0, 1.0, size=elevation.shape).astype(np.float32)
            rough = smooth_2d(rough, passes=2)
            elevation += ridge * rough * strength * 0.30
            boundary += ridge * (0.35 + strength)

    return normalize(elevation), normalize(boundary)


def apply_volcanism(
    elevation: np.ndarray,
    boundary: np.ndarray,
    profile: PlanetProfile,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Add volcanic hotspots and volcanic hazard map.
    """
    h, w = elevation.shape
    volcanic = np.zeros_like(elevation, dtype=np.float32)

    activity = float(np.clip(profile.volcanic_activity, 0.0, 1.0))
    hotspot_count = int(round(activity * 35))

    yy, xx = np.mgrid[0:h, 0:w]

    for _ in range(hotspot_count):
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, h)
        radius = rng.uniform(2.0, 10.0 + activity * 12.0)
        strength = rng.uniform(0.04, 0.16) * activity

        dx = np.minimum(np.abs(xx - cx), w - np.abs(xx - cx))
        dy = yy - cy
        dist2 = dx * dx + dy * dy
        cone = np.exp(-dist2 / (2 * radius * radius)).astype(np.float32)

        elevation += cone * strength
        volcanic += cone * (0.6 + strength)

    # Plate boundaries can also be volcanic.
    volcanic += boundary * activity * 0.45

    return normalize(elevation), normalize(volcanic)


def apply_erosion(
    elevation: np.ndarray,
    profile: PlanetProfile,
) -> np.ndarray:
    """
    Basic erosion/weathering approximation.

    More atmosphere and older age smooth high-frequency terrain more strongly.
    High tectonic activity resists complete smoothing.
    """
    atmosphere = float(np.clip(profile.atmosphere_pressure_atm / 2.0, 0.0, 1.0))
    age = float(np.clip(profile.age_gyr / 8.0, 0.0, 1.0))
    tectonics = float(np.clip(profile.tectonic_activity, 0.0, 1.0))

    erosion_strength = np.clip((0.25 + atmosphere * 0.55 + age * 0.35) * (1.15 - tectonics * 0.45), 0.0, 1.0)
    passes = int(round(1 + erosion_strength * 8))

    smoothed = smooth_2d(elevation, passes=passes)
    # Blend; do not flatten everything.
    blended = elevation * (1.0 - erosion_strength * 0.45) + smoothed * (erosion_strength * 0.45)
    return normalize(blended)


def generate_temperature(
    elevation: np.ndarray,
    liquid_mask: np.ndarray,
    profile: PlanetProfile,
) -> np.ndarray:
    """
    Generate temperature in Kelvin.

    Driven by latitude, solar flux, greenhouse factor, elevation and liquid moderation.
    """
    h, w = elevation.shape
    lat = latitude_grid(h, w)

    solar_component = 278.0 * (max(profile.solar_flux, 0.01) ** 0.25)
    greenhouse = 10.0 * profile.greenhouse_factor * np.clip(profile.atmosphere_pressure_atm, 0.0, 5.0)

    # Warm equator, cold poles.
    lat_cooling = 65.0 * (np.abs(np.sin(lat)) ** 1.45)

    # Higher ground is colder.
    elevation_cooling = 35.0 * np.clip(elevation - 0.45, 0.0, 1.0)

    temp = solar_component + greenhouse - lat_cooling - elevation_cooling

    # Liquids moderate local temperature slightly.
    moderated = smooth_2d(liquid_mask.astype(np.float32), passes=8)
    temp = temp * (1.0 - moderated * 0.08) + profile.average_surface_temp_k * (moderated * 0.08)

    return temp.astype(np.float32)


def generate_moisture(
    elevation: np.ndarray,
    liquid_mask: np.ndarray,
    temperature_k: np.ndarray,
    profile: PlanetProfile,
) -> np.ndarray:
    """
    Simple moisture: distance-like diffusion from liquid, reduced by high elevation and extreme cold/heat.
    """
    moisture = liquid_mask.astype(np.float32)

    # Diffuse moisture inland.
    diffusion_passes = int(round(8 + 24 * np.clip(profile.atmosphere_pressure_atm / 2.0, 0.0, 1.0)))
    moisture = smooth_2d(moisture, passes=diffusion_passes)

    # Mountains and cold/hot extremes reduce moisture.
    moisture *= (1.0 - np.clip(elevation - 0.58, 0.0, 0.42) * 1.2)
    moisture *= np.clip((temperature_k - 220.0) / 65.0, 0.0, 1.0)
    moisture *= np.clip((360.0 - temperature_k) / 70.0, 0.0, 1.0)

    return normalize(moisture)


def assign_bedrock(
    elevation: np.ndarray,
    boundary: np.ndarray,
    volcanic: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Assign compact bedrock codes from elevation, tectonics, volcanic influence and regional noise.
    """
    h, w = elevation.shape
    regional = fractal_noise(
        rng, h, w,
        octaves=((10, 20, 0.6, 10), (30, 60, 0.4, 4)),
    )

    bedrock = np.full((h, w), BedrockCode.BASALTIC, dtype=np.uint8)

    bedrock[(elevation > 0.52) & (regional > 0.48)] = BedrockCode.GRANITIC
    bedrock[(elevation < 0.46) & (regional < 0.55)] = BedrockCode.SEDIMENTARY
    bedrock[(boundary > 0.50) & (elevation > 0.45)] = BedrockCode.METAMORPHIC
    bedrock[volcanic > 0.55] = BedrockCode.VOLCANIC

    # Sparse impact melt provinces.
    impact_noise = fractal_noise(rng, h, w, octaves=((35, 70, 1.0, 2),))
    bedrock[(impact_noise > 0.985)] = BedrockCode.IMPACT_MELT

    return bedrock


def classify_terrain(
    elevation: np.ndarray,
    liquid_depth: np.ndarray,
    temperature_k: np.ndarray,
    moisture: np.ndarray,
    volcanic: np.ndarray,
    sea_level: float,
) -> np.ndarray:
    """
    Convert numeric layers into game-facing terrain codes.
    """
    terrain = np.full(elevation.shape, TerrainCode.PLAINS, dtype=np.uint8)

    liquid = liquid_depth > 0.001
    freezing = temperature_k < 273.15

    terrain[liquid & (liquid_depth > 0.10)] = TerrainCode.DEEP_LIQUID
    terrain[liquid & (liquid_depth <= 0.10)] = TerrainCode.SHALLOW_LIQUID
    terrain[liquid & freezing] = TerrainCode.ICE

    land = ~liquid
    terrain[land & (elevation < sea_level + 0.05)] = TerrainCode.LOWLAND
    terrain[land & (elevation >= sea_level + 0.05) & (elevation < 0.62)] = TerrainCode.PLAINS
    terrain[land & (elevation >= 0.62) & (elevation < 0.78)] = TerrainCode.HIGHLANDS
    terrain[land & (elevation >= 0.78)] = TerrainCode.MOUNTAINS

    terrain[land & (temperature_k < 255.0)] = TerrainCode.POLAR
    terrain[land & (temperature_k > 300.0) & (moisture < 0.25)] = TerrainCode.DESERT
    terrain[land & (volcanic > 0.68)] = TerrainCode.VOLCANIC

    return terrain


def generate_hazard(
    terrain: np.ndarray,
    volcanic: np.ndarray,
    temperature_k: np.ndarray,
    profile: PlanetProfile,
) -> np.ndarray:
    """
    Hazard as uint8 0..255. Later this can be split into hazard categories.
    """
    hazard = np.zeros(terrain.shape, dtype=np.float32)

    # Thermal hazards.
    hazard += np.clip((temperature_k - 320.0) / 80.0, 0.0, 1.0) * 90.0
    hazard += np.clip((240.0 - temperature_k) / 70.0, 0.0, 1.0) * 55.0

    # Volcanic hazard.
    hazard += volcanic * 120.0

    # Thin atmosphere / radiation proxy.
    shielding = np.clip(profile.atmosphere_pressure_atm / 1.0, 0.0, 1.0)
    hazard += (1.0 - shielding) * 45.0

    # Terrain-specific roughness.
    hazard[terrain == TerrainCode.MOUNTAINS] += 25.0
    hazard[terrain == TerrainCode.VOLCANIC] += 80.0
    hazard[terrain == TerrainCode.DEEP_LIQUID] += 15.0

    return np.clip(hazard, 0, 255).astype(np.uint8)


def generate_planet(profile: PlanetProfile) -> Dict[str, np.ndarray | float | PlanetProfile]:
    """
    Full prototype generation pipeline.
    """
    rng = np.random.default_rng(profile.seed)

    elevation = generate_base_elevation(profile, rng)
    elevation, boundary = apply_pseudo_tectonics(elevation, profile, rng)
    elevation, volcanic = apply_volcanism(elevation, boundary, profile, rng)
    elevation = apply_erosion(elevation, profile)

    sea_level = choose_sea_level(elevation, profile.liquid_coverage_target)
    liquid_depth = np.clip(sea_level - elevation, 0.0, 1.0).astype(np.float32)
    liquid_mask = liquid_depth > 0.0

    temperature_k = generate_temperature(elevation, liquid_mask, profile)
    moisture = generate_moisture(elevation, liquid_mask, temperature_k, profile)
    bedrock = assign_bedrock(elevation, boundary, volcanic, rng)
    terrain = classify_terrain(elevation, liquid_depth, temperature_k, moisture, volcanic, sea_level)
    hazard = generate_hazard(terrain, volcanic, temperature_k, profile)

    return {
        "profile": profile,
        "elevation": elevation.astype(np.float32),
        "boundary": boundary.astype(np.float32),
        "volcanic": volcanic.astype(np.float32),
        "sea_level": sea_level,
        "liquid_depth": liquid_depth.astype(np.float32),
        "temperature_k": temperature_k.astype(np.float32),
        "moisture": moisture.astype(np.float32),
        "bedrock": bedrock.astype(np.uint8),
        "terrain": terrain.astype(np.uint8),
        "hazard": hazard.astype(np.uint8),
    }



def ansi_256(code: int, background: bool = True) -> str:
    """Return a 256-color ANSI foreground/background escape sequence."""
    return f"\033[{'48' if background else '38'};5;{int(code)}m"


def colorize_text_with_ansi(text: str, ansi: str, color: bool, color_style: str = "bg") -> str:
    """Colorize arbitrary text using an ANSI color sequence."""
    if not color or not ansi:
        return text
    if color_style == "bg":
        return f"{ansi}{ANSI_BLACK_FG}{text}{ANSI_RESET}"
    return f"{ansi}{text}{ANSI_RESET}"


def ramp_symbol(value: float, symbols: str = " .:-=+*#%@") -> str:
    """Map a normalized 0..1 value to a density symbol."""
    value = float(np.clip(value, 0.0, 1.0))
    idx = min(len(symbols) - 1, int(value * (len(symbols) - 1)))
    return symbols[idx]


def ramp_color(value: float, palette: tuple[int, ...]) -> int:
    """Map a normalized 0..1 value to one 256-color code from a palette."""
    value = float(np.clip(value, 0.0, 1.0))
    idx = min(len(palette) - 1, int(value * (len(palette) - 1)))
    return palette[idx]


ELEVATION_PALETTE = (18, 25, 31, 187, 180, 137, 95, 244, 250, 255)
TEMPERATURE_PALETTE = (17, 18, 19, 25, 31, 45, 82, 226, 214, 202, 196)
MOISTURE_PALETTE = (236, 240, 244, 110, 74, 38, 32, 26, 20)
HAZARD_PALETTE = (236, 240, 244, 100, 136, 166, 196, 201)
VOLCANIC_PALETTE = (236, 240, 52, 88, 124, 160, 196, 202)
LIQUID_PALETTE = (236, 18, 19, 20, 25, 31, 39, 45, 51)


def normalize_for_render(a: np.ndarray) -> np.ndarray:
    """Normalize an array to 0..1 for rendering without changing source data."""
    amin = float(np.nanmin(a))
    amax = float(np.nanmax(a))
    if math.isclose(amin, amax):
        return np.zeros_like(a, dtype=np.float32)
    return ((a - amin) / (amax - amin)).astype(np.float32)


def mode_display_name(mode: str) -> str:
    return mode.replace("_", " ").title()



# -----------------------------
# Rendering and export
# -----------------------------

def render_ascii(
    terrain: np.ndarray,
    max_width: int = 120,
    max_height: int = 40,
    x0: int = 0,
    y0: int = 0,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    color: bool = False,
    color_style: str = "bg",
) -> str:
    """
    Render terrain to plain ASCII.

    For large maps, this samples the requested viewport down to max_width/max_height.
    """
    h, w = terrain.shape

    if viewport_width is None:
        viewport_width = w
    if viewport_height is None:
        viewport_height = h

    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x0 + viewport_width, w))
    y1 = max(y0 + 1, min(y0 + viewport_height, h))

    view = terrain[y0:y1, x0:x1]
    vh, vw = view.shape

    out_h = min(max_height, vh)
    out_w = min(max_width, vw)

    ys = np.linspace(0, vh - 1, out_h).astype(int)
    xs = np.linspace(0, vw - 1, out_w).astype(int)

    lines = []
    for y in ys:
        chars = []
        for x in xs:
            code = int(view[y, x])
            chars.append(terrain_symbol(code, color=color, color_style=color_style))
        lines.append("".join(chars))
    return "\n".join(lines)


def render_numeric_layer(
    layer: np.ndarray,
    palette: tuple[int, ...],
    max_width: int = 120,
    max_height: int = 40,
    x0: int = 0,
    y0: int = 0,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    color: bool = False,
    color_style: str = "bg",
    symbols: str = " .:-=+*#%@",
    normalize_values: bool = True,
) -> str:
    """Render a numeric layer as ASCII density symbols, optionally 256-colorized."""
    h, w = layer.shape

    if viewport_width is None:
        viewport_width = w
    if viewport_height is None:
        viewport_height = h

    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x0 + viewport_width, w))
    y1 = max(y0 + 1, min(y0 + viewport_height, h))

    view = layer[y0:y1, x0:x1].astype(np.float32)
    if normalize_values:
        view_norm = normalize_for_render(view)
    else:
        view_norm = np.clip(view, 0.0, 1.0)

    vh, vw = view_norm.shape
    out_h = min(max_height, vh)
    out_w = min(max_width, vw)
    ys = np.linspace(0, vh - 1, out_h).astype(int)
    xs = np.linspace(0, vw - 1, out_w).astype(int)

    lines = []
    for y in ys:
        chars = []
        for x in xs:
            value = float(view_norm[y, x])
            symbol = ramp_symbol(value, symbols=symbols)
            ansi = ansi_256(ramp_color(value, palette), background=(color_style == "bg"))
            chars.append(colorize_text_with_ansi(symbol, ansi, color=color, color_style=color_style))
        lines.append("".join(chars))
    return "\n".join(lines)


def render_bedrock_layer(
    bedrock: np.ndarray,
    max_width: int = 120,
    max_height: int = 40,
    x0: int = 0,
    y0: int = 0,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    color: bool = False,
    color_style: str = "bg",
) -> str:
    """Render categorical bedrock codes."""
    h, w = bedrock.shape

    if viewport_width is None:
        viewport_width = w
    if viewport_height is None:
        viewport_height = h

    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x0 + viewport_width, w))
    y1 = max(y0 + 1, min(y0 + viewport_height, h))

    view = bedrock[y0:y1, x0:x1]
    vh, vw = view.shape
    out_h = min(max_height, vh)
    out_w = min(max_width, vw)
    ys = np.linspace(0, vh - 1, out_h).astype(int)
    xs = np.linspace(0, vw - 1, out_w).astype(int)

    lines = []
    for y in ys:
        chars = []
        for x in xs:
            code = int(view[y, x])
            symbol = BEDROCK_SYMBOLS.get(code, "?")
            color_table = BEDROCK_BG_COLORS if color_style == "bg" else BEDROCK_FG_COLORS
            ansi = color_table.get(code, "")
            chars.append(colorize_text_with_ansi(symbol, ansi, color=color, color_style=color_style))
        lines.append("".join(chars))
    return "\n".join(lines)


def render_mode(
    data: Dict[str, np.ndarray | float | PlanetProfile],
    mode: str,
    max_width: int = 120,
    max_height: int = 40,
    x0: int = 0,
    y0: int = 0,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    color: bool = False,
    color_style: str = "bg",
) -> str:
    """Render one named map mode."""
    if mode == "terrain":
        return render_ascii(
            data["terrain"],  # type: ignore[arg-type]
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
        )

    if mode == "elevation":
        return render_numeric_layer(
            data["elevation"],  # type: ignore[arg-type]
            ELEVATION_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .:-=+*#%@",
        )

    if mode == "temperature":
        return render_numeric_layer(
            data["temperature_k"],  # type: ignore[arg-type]
            TEMPERATURE_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .:-=+*#%@",
        )

    if mode == "moisture":
        return render_numeric_layer(
            data["moisture"],  # type: ignore[arg-type]
            MOISTURE_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .:-=+*#%@",
            normalize_values=False,
        )

    if mode == "hazard":
        hazard = data["hazard"]  # type: ignore[assignment]
        assert isinstance(hazard, np.ndarray)
        return render_numeric_layer(
            hazard.astype(np.float32) / 255.0,
            HAZARD_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .:-=+*#%@",
            normalize_values=False,
        )

    if mode == "volcanic":
        return render_numeric_layer(
            data["volcanic"],  # type: ignore[arg-type]
            VOLCANIC_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .:-=+*#%@",
            normalize_values=False,
        )

    if mode == "liquid":
        return render_numeric_layer(
            data["liquid_depth"],  # type: ignore[arg-type]
            LIQUID_PALETTE,
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
            symbols=" .,:;irsXA",
            normalize_values=True,
        )

    if mode == "bedrock":
        return render_bedrock_layer(
            data["bedrock"],  # type: ignore[arg-type]
            max_width=max_width,
            max_height=max_height,
            x0=x0,
            y0=y0,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            color=color,
            color_style=color_style,
        )

    raise ValueError(f"Unsupported map mode: {mode}")



def render_numeric_legend(label_low: str, label_high: str, color: bool = False, color_style: str = "bg", palette: tuple[int, ...] = ELEVATION_PALETTE) -> str:
    """Render a simple low-to-high legend for numeric map modes."""
    symbols = " .:-=+*#%@"
    parts = []
    for idx, symbol in enumerate(symbols):
        value = idx / (len(symbols) - 1)
        ansi = ansi_256(ramp_color(value, palette), background=(color_style == "bg"))
        parts.append(colorize_text_with_ansi(symbol, ansi, color=color, color_style=color_style))
    return f"Legend: {label_low} {''.join(parts)} {label_high}"


def render_bedrock_legend(color: bool = False, color_style: str = "bg") -> str:
    """Render the bedrock legend."""
    parts = []
    color_table = BEDROCK_BG_COLORS if color_style == "bg" else BEDROCK_FG_COLORS
    for code in sorted(BEDROCK_NAMES):
        symbol = BEDROCK_SYMBOLS.get(code, "?")
        ansi = color_table.get(code, "")
        parts.append(f"{colorize_text_with_ansi(symbol, ansi, color=color, color_style=color_style)}={BEDROCK_NAMES[code]}")
    return "Legend: " + ", ".join(parts)


def render_mode_legend(mode: str, color: bool = False, color_style: str = "bg") -> str:
    """Render a mode-specific legend."""
    if mode == "terrain":
        return render_legend(color=color, color_style=color_style)
    if mode == "elevation":
        return render_numeric_legend("low", "high", color=color, color_style=color_style, palette=ELEVATION_PALETTE)
    if mode == "temperature":
        return render_numeric_legend("cold", "hot", color=color, color_style=color_style, palette=TEMPERATURE_PALETTE)
    if mode == "moisture":
        return render_numeric_legend("dry", "wet", color=color, color_style=color_style, palette=MOISTURE_PALETTE)
    if mode == "hazard":
        return render_numeric_legend("safe", "danger", color=color, color_style=color_style, palette=HAZARD_PALETTE)
    if mode == "volcanic":
        return render_numeric_legend("inactive", "active", color=color, color_style=color_style, palette=VOLCANIC_PALETTE)
    if mode == "liquid":
        return render_numeric_legend("dry/shallow", "deep", color=color, color_style=color_style, palette=LIQUID_PALETTE)
    if mode == "bedrock":
        return render_bedrock_legend(color=color, color_style=color_style)
    raise ValueError(f"Unsupported map mode: {mode}")


def render_legend(color: bool = False, color_style: str = "bg") -> str:
    """Render the terrain legend, optionally with ANSI-colored symbols."""
    entries = [
        (TerrainCode.DEEP_LIQUID, "deep liquid"),
        (TerrainCode.SHALLOW_LIQUID, "shallow liquid"),
        (TerrainCode.ICE, "ice/polar"),
        (TerrainCode.LOWLAND, "plains/lowland"),
        (TerrainCode.HIGHLANDS, "highlands"),
        (TerrainCode.MOUNTAINS, "mountains"),
        (TerrainCode.DESERT, "desert"),
        (TerrainCode.VOLCANIC, "volcanic"),
    ]
    parts = [
        f"{terrain_symbol(code, color=color, color_style=color_style)}={label}"
        for code, label in entries
    ]
    return "Legend: " + ", ".join(parts)



def layer_stats(data: Dict[str, np.ndarray | float | PlanetProfile]) -> Dict[str, object]:
    terrain = data["terrain"]
    assert isinstance(terrain, np.ndarray)

    unique, counts = np.unique(terrain, return_counts=True)
    total = terrain.size

    terrain_mix = {
        TERRAIN_NAMES.get(int(code), f"code_{int(code)}"): round(float(count) / total, 4)
        for code, count in zip(unique, counts)
    }

    elevation = data["elevation"]
    temp = data["temperature_k"]
    hazard = data["hazard"]
    liquid_depth = data["liquid_depth"]

    assert isinstance(elevation, np.ndarray)
    assert isinstance(temp, np.ndarray)
    assert isinstance(hazard, np.ndarray)
    assert isinstance(liquid_depth, np.ndarray)

    return {
        "terrain_mix": terrain_mix,
        "elevation_min": round(float(elevation.min()), 4),
        "elevation_max": round(float(elevation.max()), 4),
        "sea_level": round(float(data["sea_level"]), 4),
        "actual_liquid_coverage": round(float((liquid_depth > 0).sum()) / total, 4),
        "temperature_min_k": round(float(temp.min()), 2),
        "temperature_avg_k": round(float(temp.mean()), 2),
        "temperature_max_k": round(float(temp.max()), 2),
        "hazard_avg": round(float(hazard.mean()), 2),
        "hazard_max": int(hazard.max()),
    }


def export_npz(data: Dict[str, np.ndarray | float | PlanetProfile], path: Path) -> None:
    profile = data["profile"]
    assert isinstance(profile, PlanetProfile)

    arrays = {
        "elevation": data["elevation"],
        "boundary": data["boundary"],
        "volcanic": data["volcanic"],
        "liquid_depth": data["liquid_depth"],
        "temperature_k": data["temperature_k"],
        "moisture": data["moisture"],
        "bedrock": data["bedrock"],
        "terrain": data["terrain"],
        "hazard": data["hazard"],
        "profile_json": np.array(json.dumps(asdict(profile))),
        "sea_level": np.array(float(data["sea_level"]), dtype=np.float32),
    }
    np.savez_compressed(path, **arrays)


def write_summary(data: Dict[str, np.ndarray | float | PlanetProfile], path: Path) -> None:
    profile = data["profile"]
    assert isinstance(profile, PlanetProfile)

    summary = {
        "profile": asdict(profile),
        "stats": layer_stats(data),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototype deterministic planetary map generator.")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--name", type=str, default="Prototype")
    parser.add_argument("--width", type=int, default=200)
    parser.add_argument("--height", type=int, default=100)

    parser.add_argument("--solar-flux", type=float, default=1.0)
    parser.add_argument("--age-gyr", type=float, default=4.5)
    parser.add_argument("--atmosphere", type=float, default=1.0)
    parser.add_argument("--greenhouse", type=float, default=1.0)
    parser.add_argument("--tectonics", type=float, default=0.65)
    parser.add_argument("--volcanism", type=float, default=0.25)
    parser.add_argument("--liquid-coverage", type=float, default=0.62)
    parser.add_argument("--avg-temp-k", type=float, default=288.0)

    parser.add_argument("--preview-width", type=int, default=120)
    parser.add_argument("--preview-height", type=int, default=40)
    parser.add_argument("--x0", type=int, default=0, help="Viewport origin X coordinate.")
    parser.add_argument("--y0", type=int, default=0, help="Viewport origin Y coordinate.")
    parser.add_argument("--viewport-width", type=int, default=None, help="Viewport width before preview sampling.")
    parser.add_argument("--viewport-height", type=int, default=None, help="Viewport height before preview sampling.")
    parser.add_argument("--mode", choices=MAP_MODES, default=None, help="Render only one map mode. If omitted, all modes are written to files.")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Directory for default all-mode render outputs.")
    parser.add_argument("--color", action="store_true", help="Render ANSI color output using the topographic 256-color palette.")
    parser.add_argument(
        "--color-style",
        choices=["fg", "bg"],
        default="bg",
        help="ANSI color style: fg colors the symbol, bg colors the symbol background.",
    )

    parser.add_argument("--export", type=Path, default=None, help="Optional compressed .npz export path.")
    parser.add_argument("--summary", type=Path, default=None, help="Optional JSON summary path.")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    profile = PlanetProfile(
        seed=args.seed,
        name=args.name,
        width=args.width,
        height=args.height,
        age_gyr=args.age_gyr,
        solar_flux=args.solar_flux,
        atmosphere_pressure_atm=args.atmosphere,
        greenhouse_factor=args.greenhouse,
        tectonic_activity=args.tectonics,
        volcanic_activity=args.volcanism,
        liquid_coverage_target=args.liquid_coverage,
        average_surface_temp_k=args.avg_temp_k,
    )

    data = generate_planet(profile)
    stats = layer_stats(data)

    print(f"Planet: {profile.name}")
    print(f"Seed: {profile.seed}")
    print(f"Size: {profile.width}x{profile.height}")
    print(f"Sea level: {stats['sea_level']}")
    print(f"Actual liquid coverage: {stats['actual_liquid_coverage']}")
    print(f"Temperature K min/avg/max: {stats['temperature_min_k']} / {stats['temperature_avg_k']} / {stats['temperature_max_k']}")
    print(f"Hazard avg/max: {stats['hazard_avg']} / {stats['hazard_max']}")
    print("Terrain mix:")
    terrain_items = []
    terrain = data["terrain"]
    assert isinstance(terrain, np.ndarray)
    unique, counts = np.unique(terrain, return_counts=True)
    total = terrain.size
    for code, count in zip(unique, counts):
        name = terrain_name(int(code), color=args.color, color_style=args.color_style)
        frac = float(count) / total
        sort_name = TERRAIN_NAMES.get(int(code), f"code_{int(code)}")
        terrain_items.append((sort_name, name, frac))
    for _sort_name, display_name, frac in sorted(terrain_items, key=lambda item: item[0]):
        # ANSI escape codes affect visible width, so do not rely on alignment when colored.
        if args.color:
            print(f"  {display_name} {frac:.2%}")
        else:
            print(f"  {display_name:16s} {frac:.2%}")

    selected_modes = [args.mode] if args.mode else list(MAP_MODES)

    if args.mode:
        print(f"\nMap Mode: {mode_display_name(args.mode)}")
        print(f"{render_mode_legend(args.mode, color=args.color, color_style=args.color_style)}\n")
        print(render_mode(
            data,
            args.mode,
            max_width=args.preview_width,
            max_height=args.preview_height,
            x0=args.x0,
            y0=args.y0,
            viewport_width=args.viewport_width,
            viewport_height=args.viewport_height,
            color=args.color,
            color_style=args.color_style,
        ))
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        extension = "ansi" if args.color else "txt"
        for mode in selected_modes:
            output_path = args.output_dir / f"{profile.name.lower().replace(' ', '_')}_{mode}.{extension}"
            rendered = (
                f"Planet: {profile.name}\n"
                f"Seed: {profile.seed}\n"
                f"Size: {profile.width}x{profile.height}\n"
                f"Map Mode: {mode_display_name(mode)}\n"
                f"{render_mode_legend(mode, color=args.color, color_style=args.color_style)}\n\n"
                f"{render_mode(data, mode, max_width=args.preview_width, max_height=args.preview_height, x0=args.x0, y0=args.y0, viewport_width=args.viewport_width, viewport_height=args.viewport_height, color=args.color, color_style=args.color_style)}\n"
            )
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Wrote {mode_display_name(mode)} render: {output_path}")

    if args.export:
        export_npz(data, args.export)
        print(f"\nExported compressed arrays to: {args.export}")

    if args.summary:
        write_summary(data, args.summary)
        print(f"Exported summary JSON to: {args.summary}")


if __name__ == "__main__":
    main()
