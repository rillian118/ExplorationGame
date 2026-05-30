\
STAR_CLASS_WEIGHTS = [
    ("M", 45),
    ("K", 20),
    ("G", 15),
    ("F", 8),
    ("A", 4),
    ("white_dwarf", 3),
    ("red_giant", 2),
]

STAR_PROFILES = {
    "M": {
        "label": "red dwarf",
        "mass_range": (0.12, 0.55),
        "radius_range": (0.15, 0.65),
        "luminosity_range": (0.003, 0.08),
        "temperature_range": (2400, 3900),
        "color": "deep red",
    },
    "K": {
        "label": "orange dwarf",
        "mass_range": (0.55, 0.85),
        "radius_range": (0.65, 0.9),
        "luminosity_range": (0.08, 0.45),
        "temperature_range": (3900, 5200),
        "color": "orange",
    },
    "G": {
        "label": "yellow dwarf",
        "mass_range": (0.85, 1.1),
        "radius_range": (0.9, 1.1),
        "luminosity_range": (0.45, 1.5),
        "temperature_range": (5200, 6000),
        "color": "yellow-white",
    },
    "F": {
        "label": "white-yellow main-sequence star",
        "mass_range": (1.1, 1.5),
        "radius_range": (1.1, 1.5),
        "luminosity_range": (1.5, 5.0),
        "temperature_range": (6000, 7500),
        "color": "white-yellow",
    },
    "A": {
        "label": "white main-sequence star",
        "mass_range": (1.5, 2.3),
        "radius_range": (1.5, 2.4),
        "luminosity_range": (5.0, 25.0),
        "temperature_range": (7500, 10000),
        "color": "white",
    },
    "white_dwarf": {
        "label": "white dwarf remnant",
        "mass_range": (0.5, 1.2),
        "radius_range": (0.008, 0.02),
        "luminosity_range": (0.0005, 0.02),
        "temperature_range": (6000, 30000),
        "color": "pale white",
    },
    "red_giant": {
        "label": "red giant",
        "mass_range": (0.8, 2.0),
        "radius_range": (10.0, 80.0),
        "luminosity_range": (50.0, 1000.0),
        "temperature_range": (3000, 5000),
        "color": "red-orange",
    },
}

ARCHITECTURES = [
    "compact_inner_system",
    "standard_system",
    "wide_outer_system",
    "gas_giant_dominated",
    "belt_heavy_system",
    "sparse_system",
    "post_disruption_system",
]

ATMOSPHERES = [
    "none",
    "trace",
    "thin",
    "breathable",
    "dense",
    "toxic",
    "corrosive",
    "exotic",
]

HYDROSPHERES = [
    "none",
    "ice",
    "liquid_water",
    "brine",
    "methane",
    "lava",
    "exotic",
]

WORLD_CLASSES = {
    "inner": [
        "scorched_rock",
        "barren_rock",
        "iron_world",
        "greenhouse_world",
        "lava_world",
    ],
    "habitable": [
        "desert_world",
        "temperate_world",
        "ocean_world",
        "toxic_world",
        "barren_rock",
        "greenhouse_world",
    ],
    "outer": [
        "gas_giant",
        "ice_giant",
        "ice_world",
        "dwarf_ice",
        "barren_rock",
    ],
    "frozen": [
        "ice_world",
        "dwarf_ice",
        "dwarf_rock",
        "captured_asteroid",
    ],
}

MOON_CLASSES = [
    "barren_moon",
    "frozen_moon",
    "volcanic_moon",
    "captured_asteroid",
    "ice_moon",
    "subsurface_ocean_moon",
    "toxic_moon",
]

RESOURCE_TYPES = [
    "common_metals",
    "rare_metals",
    "volatiles",
    "radioactives",
    "crystals",
    "organics",
]

SYSTEM_NAME_ROOTS = [
    "Kharon", "Vesta", "Aster", "Orison", "Naraka", "Helion", "Tamar",
    "Rook", "Caldera", "Istria", "Sable", "Eos", "Nyx", "Aurel",
    "Hadeon", "Lys", "Mire", "Cairn", "Thale", "Oros",
]
