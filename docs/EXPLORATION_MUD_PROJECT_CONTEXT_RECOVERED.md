# Exploration MUD — Reconstructed Project Context

Compiled from the prior ChatGPT conversations attached to the **Exploration MUD** project.

Last reconstructed: 2026-07-25

## How Codex Should Use This File

Read this file before planning substantial work on the project.

This document records design intent and the historically reported implementation state. It is not a substitute for inspecting the current repository. When the two disagree:

1. The current code and database determine what actually exists.
2. This document determines the intended direction unless the user says otherwise.
3. Never overwrite working code merely to match an old example.
4. Ask before resolving a genuine conflict between current behavior and a confirmed design decision.

The following labels are used throughout:

- **CANON** — explicitly established setting or project premise.
- **DECIDED** — a design direction explicitly accepted by the user.
- **HISTORICALLY IMPLEMENTED** — described as present in the old code; verify in the recovered checkout.
- **HISTORICALLY WORKING** — reported and tested as working in the archived conversations; verify against the current checkout.
- **PROPOSED** — an assistant recommendation or brainstorm that was not explicitly adopted in full.
- **OPEN** — unresolved and should not be silently decided.

Names used in examples are not automatically canon. In particular:

- **Astalon** was the primary generated test system.
- **Astalon I** was the primary test planet.
- **Wayfarer** was the primary test ship.
- **Kharon**, **Vathros**, **Khepri**, and **Meros** were illustrative names.
- Proposed names for Earth institutions and AI rules are placeholders until adopted.

---

# 1. Project Identity and Vision

## 1.1 Core Premise

**CANON**

Exploration MUD is a text-based science-fiction MUD set in the Milky Way. Its central fantasy is not merely traveling through a prewritten map. Players should help open, survey, settle, supply, contest, and record a gradually expanding human frontier.

The project is being built on Evennia and is intended to support:

- exploration and discovery;
- procedural stellar and planetary generation;
- player-owned ships and shipboard play;
- orbital surveys and surface expeditions;
- player expansion and construction;
- crafting, extraction, trade, and logistics;
- corporations and formal politics;
- piracy and bounded PvP;
- large-scale, objective-driven warfare;
- persistent records of discoveries and player history.

The desired experience is a persistent text MMO with strong simulation and world-history elements, not a conventional room-by-room fantasy MUD with a space skin.

## 1.2 High-Level Gameplay Loop

**DECIDED DIRECTION**

The discussions converged on this loop:

1. **Explore**
   - detect stars and bodies;
   - scan systems;
   - survey planets;
   - identify anomalies, hazards, resources, and routes.
2. **Claim**
   - register discoveries;
   - place beacons;
   - obtain legal recognition or a charter;
   - establish outposts and concessions.
3. **Extract and Build**
   - mine and harvest;
   - refine materials;
   - craft components;
   - manufacture modules, ships, stations, and colonial infrastructure.
4. **Move**
   - operate supply chains;
   - haul fuel and cargo;
   - organize convoys;
   - trade, smuggle, and maintain remote settlements.
5. **Contest**
   - compete economically and politically;
   - pirate, escort, interdict, sabotage, blockade, or fight;
   - negotiate treaties and resolve charter disputes.
6. **Record**
   - update atlases, registries, archives, news, organizational histories, and memorials;
   - allow player actions to become the shared history of the setting.

The final step is a core differentiator. The world should remember what players did.

## 1.3 Controlled Expansion Model

**CANON**

The game should begin with the Sol system so core systems can be developed and planetary generation can be improved in a controlled environment.

Expansion is gated by jump-engine range:

- Initial play and testing occur inside Sol.
- The original proposed first range increase was to **2 light-years from Sol**.
- Additional stellar content is generated offline, reviewed, exported in a canonical format, and imported into the live game.
- Later jump engines extend the reachable radius as existing content becomes sufficiently developed.

This creates a controllable live-content cadence:

```text
improve core systems
→ generate the next frontier band
→ validate/import it
→ release a longer-range jump engine
→ let players explore the new band
```

**OPEN / DESIGN WARNING**

There are no ordinary neighboring star systems within 2 light-years of Sol. The archived discussion suggested using an early 2-ly phase for the Kuiper Belt, Oort Cloud, probes, rogue bodies, or other deep-Sol content, and using roughly 5 ly for the first conventional interstellar expansion to Alpha/Proxima Centauri. The user did not formally revise the 2-ly plan, so this remains a content-planning question.

## 1.4 Design Pillars

**DECIDED**

- The game remains fully playable as text.
- Graphics and ANSI enhance state; they never become the only source of information.
- Simulation should create decisions, consequences, and atmosphere, not demand pointless busywork.
- World truth, player knowledge, presentation, and persistent player impact are separate layers.
- Systems should be extensible without building every late-game feature in the first version.
- Important activity should emit structured records so it can feed history, law, media, and analytics.
- Exploration should create economically and politically valuable information, not just fill a progress bar.
- PvP should be meaningful and dangerous where appropriate, but should not consume the entire game.

## 1.5 Collaboration Context

The project owner has professional commercial MUD/MMO experience, including work as a Producer/game head for Iron Realms Entertainment, and prior technical experience with the older Rapture engine. They are not new to game systems, persistent worlds, player politics, or commercial MUD design. Their gap was primarily familiarity with the modern engine/tooling ecosystem after roughly a decade away.

Codex should therefore:

- collaborate at a systems-designer/developer level;
- explain Evennia-, Django-, Python-, or modern-tooling-specific details when useful;
- avoid treating established MUD design concepts as unfamiliar;
- distinguish its own recommendations from the owner's decisions;
- preserve the owner's intent while still raising concrete technical or design risks.

The historical workflow used ChatGPT for design discussion and Codex/VS Code for code. This file now carries that design context into Codex so implementation and design can be reconciled in one place.

---

# 2. Setting and Lore

## 2.1 Earth and the Human Biosphere

**CANON**

At the start of the setting, Earth is the only naturally viable source of the complete biosphere needed by human civilization.

Earth supplies or ultimately anchors:

- compatible soil ecologies and microbial communities;
- seed banks and crop lines;
- algae and closed-loop life-support organisms;
- pollinators and animal genomes;
- human-compatible food webs;
- ecological starter packages needed for large-scale settlement or terraforming.

Alien life may be discovered, but it is expected to be extremely unlikely to be biologically compatible with terrestrial life, even as food. Finding life elsewhere therefore does not automatically end humanity's dependence on Earth.

Earth remains indispensable unless a genuinely self-sufficient, fully terraformed human-compatible world is eventually created. Such a world would be a major historical and political transformation, not routine content.

This makes biosphere shipments, seed vaults, quarantine, ecological licenses, and terraforming packages strategically important.

## 2.2 Starting Political Order

**CANON / DECIDED**

Human space initially recognizes one legitimate sovereign authority: a UN-like organization based on Earth.

Earth is:

- humanity's political and legal root;
- materially indispensable because of the biosphere;
- treated as sacrosanct;
- the source of recognized charters, licenses, concessions, and lawful force.

Player organizations initially are not sovereign nations. They are more likely to be:

- corporations;
- exploration companies;
- scientific institutes;
- logistics combines;
- colonial authorities;
- security contractors;
- semi-governmental bodies operating under an Earth-granted mandate.

A model example is a company receiving a charter to develop a colony on Ceres. That charter might grant governance and defensive authority within a defined area while imposing restrictions, taxes, reporting duties, inspection rights, and biosphere rules.

The analogy is intentionally similar to chartered trading companies of the seventeenth and eighteenth centuries, adapted to space.

## 2.3 Legitimacy Versus Reach

**DECIDED DIRECTION**

Earth should possess ultimate legitimacy without possessing effortless operational reach everywhere.

The frontier tension is:

> Earth is legitimate, but space is vast.

Earth law can define what is permitted, but actual enforcement may depend on:

- nearby patrols;
- local charter security;
- sensor and communications coverage;
- admissible evidence;
- corporate influence;
- political will;
- travel time and logistics.

This allows frontier autonomy, corruption, piracy, and conflict without making Earth weak or irrelevant.

## 2.4 Charters as Mechanics

**DECIDED DIRECTION**

Charters should eventually be first-class game records rather than background prose.

A charter may contain:

- issuing authority;
- holder organization;
- geographic or orbital jurisdiction;
- authorized activities;
- prohibited activities;
- construction and extraction rights;
- defense and interdiction rights;
- tax and fee authority;
- reporting and inspection duties;
- biosphere and quarantine permissions;
- duration and renewal date;
- violation history;
- current status.

Potential charter families discussed:

- exploration;
- extraction;
- settlement;
- security;
- logistics;
- research;
- terraforming/biosphere.

Other systems should eventually be able to ask the charter service questions such as:

- May this organization place a beacon here?
- May it extract this resource?
- May it build a refinery or habitat?
- May it tax local docking?
- May it use force against a trespasser?
- May it import protected biosphere material?
- May it claim salvage?

**PROPOSED**

Possible institutional names included an Earth Authority/Terran Mandate, Survey Bureau, Colonial Office, Biosphere Authority, Commerce Directorate, and Security Tribunal. These are useful functional placeholders but are not established names.

## 2.5 Political Evolution

**PROPOSED LONG ARC**

The single-authority opening creates a possible multi-year political arc:

1. Earth Mandate — all recognized power descends from Earth.
2. Corporate Frontier — large charter holders accumulate practical power.
3. Colonial Identity — remote settlements develop distinctive interests and cultures.
4. Secession Pressure — frontier powers begin challenging the charter order.
5. Multipolar Human Space — Earth remains sacred and central but is no longer the sole practical center of power.

Do not begin with unrestricted player nations or easy sovereignty. If independent polities emerge, they should be earned through world history.

## 2.6 Ship Intelligence and the Rules of Force

**CANON / DECIDED**

Advanced ship intelligences are necessary for ad hoc calculations involved in course plotting, interstellar travel, navigation, and other automatic ship functions. Ordinary non-intelligent computers are insufficient for these tasks.

Earth firms created ship-integrated AI systems with hard constraints analogous in purpose—but not necessarily name or wording—to Asimov-style laws.

These systems prevent or refuse to assist unsanctioned combat unless recognized conditions apply, such as:

- the ship or protected party is under attack;
- a recognized government or charter authorizes force;
- a valid warrant, bounty, war declaration, enforcement writ, or letter of marque applies;
- the action protects humanity or critical infrastructure.

The AI can enforce this by refusing capabilities such as:

- weapon synchronization;
- targeting solutions;
- pursuit or intercept plotting;
- reactor overcharge for weapons;
- attack-vector navigation.

The AI is not merely a moral commentator. It is an indispensable operational component whose cooperation is required for effective combat.

## 2.7 Piracy and Corrupted Shipminds

**CANON / DECIDED DIRECTION**

Pirates cannot simply replace the required ship intelligence or remove every constraint. They can corrupt or reinterpret it so its engagement conditions are looser.

The intended pirate pattern is bounded coercion:

- piracy occurs away from protected core areas;
- the pirate issues demands;
- the victim is given an opportunity to comply, refuse, flee, or resist;
- force follows refusal or resistance;
- disablement, cargo seizure, ransom, or boarding are preferred to indiscriminate destruction;
- actions that pose excessive danger to humanity or critical biosphere infrastructure remain prohibited even to many corrupted systems.

This provides an in-world reason a hardcore PvPer cannot simply attack every ship with guns blazing.

**PROPOSED TERMINOLOGY**

The assistant proposed **Continuity Protocols** as a possible name, with concepts such as:

- human continuity;
- lawful authority;
- proportionality;
- evidentiary integrity.

The name and exact protocol text remain open, but the underlying constraint system is part of the setting direction.

## 2.8 Evidence and Ship Logs

**DECIDED DIRECTION**

Ship AIs and combat systems should preserve structured records of:

- authorization state;
- transponder identity;
- demands and responses;
- weapons fire;
- damage;
- location and timestamps;
- warrants, charters, or letters of marque used to justify force.

These records support:

- legal proceedings;
- bounty validation;
- insurance;
- charter enforcement;
- public news;
- political disputes;
- anti-cheat and staff investigation where appropriate.

This connects the lore of constrained ship intelligence directly to the project's event-logging architecture.

---

# 3. Space, Stellar Systems, and Navigation

## 3.1 Simulation Philosophy

**DECIDED**

Use a deterministic, simplified ephemeris model rather than continuous N-body simulation.

Natural bodies should appear to move, rotate, and orbit consistently, but the server should calculate their state from orbital parameters and game time when needed. It should not update every planet every tick.

The goal is believable and gameable astronomy, not a research-grade physics engine.

## 3.2 Stellar Hierarchy

**DECIDED**

```text
Universe
└── Star System
    ├── Star or stars
    ├── Natural bodies
    │   ├── planets
    │   ├── moons
    │   ├── dwarf planets
    │   └── major asteroids
    ├── Spatial fields
    │   ├── asteroid belts
    │   ├── rings
    │   ├── debris fields
    │   └── clouds or hazard regions
    ├── Persistent artificial objects
    │   ├── stations
    │   ├── shipyards
    │   ├── beacons
    │   ├── ships
    │   └── player structures
    └── Temporary objects
        ├── wrecks
        ├── salvage clouds
        ├── derelicts
        ├── distress signals
        └── mission or survey anomalies
```

## 3.3 Natural Bodies

**DECIDED**

Natural bodies use orbital/rotational parameters:

- parent body;
- semi-major axis or orbital radius;
- orbital period;
- phase;
- eccentricity;
- inclination;
- prograde/retrograde direction;
- rotation period;
- axial tilt;
- rotation phase;
- tidal-lock state.

Their position is derived from these values and game time.

This should support:

- moving planets and moons;
- day/night cycles;
- changing travel and intercept times;
- local solar time;
- launch windows and rendezvous;
- comets and high-inclination bodies;
- surface lighting and temperature differences.

## 3.4 Moons

**DECIDED**

Moons should be part of the hierarchy from the beginning. A moon uses the same basic orbital abstraction as a planet, but its parent is a planet rather than a star.

Moons are expected to be major gameplay destinations for mining, colonies, shipyards, hidden bases, research sites, and ruins.

## 3.5 Internal 3D, Player-Facing 2.5D

**DECIDED**

The simulation should be capable of three-dimensional coordinates and vectors:

```text
position: x, y, z
velocity: vx, vy, vz
```

The default MUD presentation should remain comprehensible and mostly use:

- bearing;
- range;
- inner/outer system;
- orbit and parent body;
- plane offset or above/below ecliptic;
- relative motion;
- estimated travel time.

Full vectors may be exposed through advanced piloting commands later. Most players should be able to use named targets and autoplotting.

## 3.6 Artificial and Dynamic Objects

**DECIDED**

Ships, stations, wrecks, beacons, probes, and player-built structures should be first-class spatial entities.

Unlike deterministic natural bodies, they may store current position and velocity directly, or reference a defined orbit.

Temporary entities need:

- creation time;
- optional expiration time;
- decay policy;
- visibility/sensor state;
- salvage or interaction state;
- a rule allowing meaningful player interaction to stabilize or promote them into persistent content.

Example design:

```text
battle creates wreck
→ wreck decays after a defined interval
→ salvage may remove it sooner
→ a player may stabilize and claim it
→ a stabilized derelict may become a permanent site or rebuilt outpost
```

## 3.7 Flight Fidelity

**DECIDED STAGING**

Implement flight in layers.

### Baseline: Strategic Travel

Players select a destination. The ship computer calculates:

- intercept;
- travel time;
- fuel or energy cost;
- risk;
- relative motion.

Typical interaction:

```text
plot course <target>
engage course
estimate <target>
```

### Later: Vector Flight

Advanced players may control thrust, heading, coasting, and velocity matching.

### Later Still: Orbital Operations

Transfer orbits, insertion, slingshots, station keeping, and advanced intercepts may exist, but the ship computer should do the mathematics. The player makes operational choices rather than solving equations manually.

## 3.8 Generation Pipeline

**DECIDED**

The stellar generator is an offline/data-generation component with deterministic seeds and a stored generation version.

The original pipeline:

1. Initialize deterministic RNG.
2. Generate system identity and coordinates.
3. Generate primary and optional companion stars.
4. Determine broad system architecture.
5. Generate ordered planetary orbits.
6. Generate planets and physical profiles.
7. Generate rotations.
8. Generate moons.
9. Generate belts, rings, and fields.
10. Generate optional artificial objects.
11. Generate dynamic-spawn profiles rather than filling the system with temporary objects immediately.
12. Validate references and orbital ordering.
13. Export JSON and human/MUD summaries.
14. Import validated results into Evennia.

Systems need stable identifiers and a generation version so generator changes do not silently rewrite existing worlds.

## 3.9 Historical System-Generation State

**HISTORICALLY WORKING — VERIFY**

The archived work reported:

- deterministic system generation;
- stable JSON export/import;
- persistent imported systems in Evennia;
- commands for listing systems, scanning a system, listing bodies, and viewing body details;
- more readable unit formatting for stars, planets, and moons;
- a successful Astalon test import with five bodies.

The core demonstrated loop was:

```text
generate system
→ export canonical JSON
→ import into Evennia
→ persist
→ inspect in-game
```

---

# 4. Planetary Generation

## 4.1 Architectural Principle

**DECIDED**

Planetary generation should be a standalone tool or module outside the live Evennia gameplay loop.

The conceptual chain is:

```text
star supplies constraints
→ orbit modifies those constraints
→ planet profile interprets them
→ map generator creates layered geography
→ Evennia imports the result and stores mutable gameplay state
```

The generator aims for plausible, coherent, gameable worlds inspired by astrophysics and geology. It is not intended to reconstruct a planet from perfect first-principles simulation.

## 4.2 Resolution

**DECIDED**

The early idea used a 1000×1000 grid for an Earth-sized body. The adopted prototype moved to a **1000×500** Earth-scale map, which better fits a 2:1 planetary projection.

Map scale should vary with body size.

During algorithm development, smaller maps such as 100×100 or 250×125/250 were recommended for rapid tuning.

The grid is a gameplay/geographic data grid, not a million Evennia rooms.

## 4.3 Planet Profile Versus Map

**DECIDED**

Generate and inspect a high-level planet profile before generating the full map.

A profile may include:

- deterministic seed and generation version;
- radius, mass, and gravity;
- orbit and solar flux;
- age;
- body class;
- tectonic and volcanic activity;
- magnetosphere;
- atmospheric pressure and composition;
- average temperature and greenhouse effects;
- surface liquids and target coverage;
- crust/elemental biases;
- radiation and environmental threats;
- habitability.

This separation permits planets that are known astronomically but do not yet need a full surface map.

## 4.4 Layered Map Data

**DECIDED**

A cell is not simply "mountain" or "ocean." The map should expose separate data layers, commonly stored as efficient arrays:

- elevation;
- temperature;
- moisture;
- pressure;
- liquid depth/type;
- terrain classification;
- bedrock/geology;
- regolith;
- volcanic activity;
- hazards;
- radiation;
- resource abundance;
- resource accessibility;
- biome/ecology when applicable;
- points of interest;
- survey state or confidence.

Renderers choose which layers to display.

## 4.5 Generation Passes

**DECIDED DIRECTION**

Keep passes independent enough to inspect and tune:

1. Star and orbital context.
2. Planet profile.
3. Base elevation/noise.
4. Pseudo-tectonic shaping.
5. Volcanic shaping.
6. Impacts/cratering where appropriate.
7. Erosion and weathering.
8. Bedrock and geological provinces.
9. Mineral/resource enrichment.
10. Sea level, liquids, and ice.
11. Temperature and climate.
12. Atmosphere/environmental hazards.
13. Surface/terrain classification.
14. Render and export.

Do not combine geology, altitude, erosion, and resources into one opaque pass.

## 4.6 Pseudo-Tectonics

**DECIDED DIRECTION**

The early practical approach uses stylized plate tectonics:

- generate Voronoi-like plates;
- assign plate type, density, age, and movement vector;
- create mountains and trenches at convergent boundaries;
- create rifts and ridges at divergent boundaries;
- create fault zones at transform boundaries;
- add volcanic hotspot chains.

The objective is plausible large-scale structure, not a full geodynamic simulation.

## 4.7 Erosion and Age

**DECIDED DIRECTION**

Age should not simply equal "more generic smoothing passes." Erosion depends on atmosphere, liquids, temperature, tectonic renewal, and ice.

Examples:

- old wet active world: mature drainage and eroded ranges;
- old airless world: ancient craters remain;
- young volcanic world: rough fresh flows;
- old tectonically dead world: broad worn plains;
- old but active world: new mountains plus old sediments.

The first useful erosion model can remain simple: slope smoothing plus downhill liquid/river tracing.

## 4.8 Liquids and Atmospheres

**DECIDED**

Choose the likely liquid profile before terrain placement but apply sea level after elevation generation.

Possible surface liquids are not restricted to water and may include methane/ethane, ammonia mixtures, brines, sulfur compounds, or exotic fluids when physically and fictionally appropriate.

The generator should:

1. select a primary liquid and target surface coverage;
2. generate terrain;
3. choose the elevation threshold that reaches the target coverage;
4. flood low areas;
5. apply temperature-dependent freezing, evaporation, or dry-basin behavior.

Atmosphere affects:

- heat distribution and day/night contrast;
- weather and erosion;
- radiation protection;
- liquid stability;
- toxicity and corrosiveness;
- entry and surface hazard.

## 4.9 Resources

**DECIDED DIRECTION**

Resources should arise from geology rather than arbitrary loot-node placement.

The intended logic is:

```text
bedrock and province
→ tectonic/volcanic/impact enrichment
→ erosion and exposure
→ resource abundance
→ resource accessibility
```

Abundance and accessibility must remain separate. A rich deposit under kilometers of ice or ocean is not equivalent to an exposed deposit.

## 4.10 PlanetGen v0.1 Historical Baseline

**HISTORICALLY WORKING — VERIFY**

The Planetary Generation v0.1 stopping point reportedly included:

- deterministic seed-based generation;
- maps up to 1000×500;
- full-world generation at requested granularity;
- viewports that select from an already generated world rather than generating extra detail;
- terrain, elevation, temperature, moisture, hazard, volcanic, liquid, and bedrock render modes;
- generation of every render mode when no single mode is selected;
- plain and ANSI output;
- foreground/background styles;
- a 256-color topographic palette that avoids implying vegetation through green;
- compressed array export;
- summary JSON export.

The last referenced prototype was `planetgen_prototype_v004.py`. That file is not present in this local project mirror and must be recovered from the actual repository or backups if still needed.

## 4.11 Storage Strategy

**DECIDED DIRECTION**

Use deterministic generation aggressively, but do not assume every final layer can always be recreated cheaply or identically forever.

Long-term storage should distinguish:

- seed, generation parameters, and generation version;
- cached generated arrays/chunks;
- manual overrides;
- player-built structures and terrain modification;
- discovered/surveyed knowledge;
- depleted resources;
- persistent points of interest.

Generate once and cache/load for repeated map viewing. Chunking or lazy local regeneration is a later optimization and must preserve global coherence for sea level, tectonics, and climate.

---

# 5. Interfaces, Maps, and Accessibility

## 5.1 Two Player Interfaces

**CANON**

The user envisioned two major interaction contexts:

1. A conventional personal MUD interface for characters, rooms, inventory, social play, and commands.
2. A piloting/ship interface for navigation, sensors, systems, surveys, and maps.

These are modes over the same authoritative world, not separate games.

## 5.2 Planetary Maps Are Data, Not Rooms

**DECIDED**

Planetary maps should be surveyable data grids.

Do not create one Evennia room for every planetary tile.

Use three layers:

1. **Objective source map** — what actually exists.
2. **Survey knowledge** — what a player, ship, organization, or public source knows.
3. **Renderer** — how the permitted knowledge is expressed as text, ANSI, lists, or optional graphics.

Only instantiate actual surface rooms where characters physically travel or where a meaningful site exists.

## 5.3 Map Modes

**DECIDED**

The same underlying map should support semantic modes such as:

- terrain/topography;
- elevation;
- thermal/temperature;
- moisture/hydrology;
- atmosphere/weather;
- radiation;
- hazards;
- geology/bedrock;
- minerals/resources;
- biosignatures;
- anomalies;
- political control;
- survey confidence/completeness;
- landing suitability.

Map symbols and colors are renderer choices. They are not the authoritative stored value.

## 5.4 Text and ANSI Rendering

**DECIDED**

ANSI/ASCII maps should remain compact and readable.

The historical survey renderer used a small vocabulary similar to:

```text
S  reference/selected point
?  unsurveyed
.  open/plain terrain
d  dusty terrain
^  ridge or high ground
o  crater
_  basin
~  liquid, flow, molten, or water terrain
!  known hazard
```

Do not treat this exact vocabulary as immutable. The durable requirement is that every symbol have a textual legend and a semantic alternative.

## 5.5 Optional Graphical Overlay

**DECIDED DIRECTION**

A retro graphical presentation may be offered as progressive enhancement.

Architecture:

```text
authoritative server state
├── text renderer → any MUD/telnet/web client
└── structured UI events → optional enhanced client
```

Potential tiers:

- baseline text client;
- enhanced Mudlet plugin with panels, gauges, maps, and miniwindows;
- richer web or custom client with pixel-art maps, ship schematics, and tactical overlays.

The graphical layer is a client capability, not a separate ruleset and not a required premium game mode.

The server may emit machine-readable map and ship-state events alongside ordinary text. A client that does not understand them should lose no gameplay information.

## 5.6 Accessibility Is a Standing Requirement

**DECIDED**

Every new system must be evaluated for screen-reader use.

The baseline experience must never require:

- ANSI color as the sole signal;
- visual alignment as the sole relationship;
- a map glyph as the sole warning;
- rapid scanning of decorative output;
- reflex-speed command chains.

A toggleable screen-reader/accessibility mode may optimize presentation, but semantic accessibility should not exist only behind that toggle.

Required considerations:

- plain-text alternatives for maps and charts;
- stable labels and ordering;
- concise versus verbose output;
- reduced decorative ASCII;
- clean exit, object, contact, and ship lists;
- prose summaries of spatial information;
- directional and coordinate summaries;
- filters for combat and alert spam;
- configurable ANSI/color use;
- explicit hazard and state messages;
- no dependence on tables whose meaning disappears when read serially.

## 5.7 Historical Accessible Survey Views

**HISTORICALLY WORKING — VERIFY**

The survey system reportedly supported:

- `survey map visual` — compact ASCII;
- `survey map brief` — screen-reader-friendly semantic summary;
- `survey map list` — directional tile-by-tile listing;
- `survey detail <x> <y>` — focused semantic report.

The preference:

```text
player preferences survey_map visual|brief|list
```

controlled the default for plain `survey map`, while an explicit mode overrode it.

## 5.8 Voice and External Input Tools

**DECIDED LOW-PRIORITY PRINCIPLE**

Native voice control is not an early priority. Tools such as VoiceAttack can translate spoken phrases into commands if the command language is predictable.

Commands should therefore be:

- alias-friendly;
- tolerant of reasonable synonyms;
- free of unnecessary punctuation;
- clear about dangerous actions;
- compatible with macros;
- not excessively timing-sensitive.

The main accessibility bottleneck is often serial output load, not blind players' typing speed. Optimize output first.

---

# 6. Survey and Exploration Knowledge

## 6.1 Foundational Rule

**DECIDED**

```text
World truth is global.
Knowledge of world truth is scoped.
Access to knowledge is permissioned.
Presentation is filtered through available knowledge.
```

Or, in the shorter formulation:

```text
Planets are shared reality.
Survey data is scoped knowledge.
Maps are permission-filtered views.
```

Never mark a planet globally "surveyed" merely because one player scanned it.

## 6.2 Survey Ownership Scopes

**DECIDED DIRECTION**

Survey information may belong to:

- a character or account;
- a ship computer;
- an organization;
- a fleet or temporary sharing group;
- a purchaser/license holder;
- the public.

The initial minimal scopes were personal, ship, and public. Organization, fleet, marketplace, encryption, and temporary sharing are later layers.

When a player requests a map, the game builds an effective view from sources they may access. A simple first merge rule is to take the best confidence per tile and layer while preserving provenance.

## 6.3 Confidence, Not Binary Discovery

**DECIDED**

Survey data should use coverage and confidence rather than a single known/unknown flag.

Suggested interpretation:

- 0% — unknown;
- 1–25% — rough estimate;
- 26–50% — preliminary;
- 51–75% — reliable;
- 76–95% — high confidence;
- 96–100% — verified.

Different tools improve different layers and at different rates.

## 6.4 Survey Layers

**DECIDED DIRECTION**

Potential layers include:

- visual;
- topography;
- thermal;
- spectral/surface chemistry;
- mineral;
- atmosphere;
- hydrology;
- gravimetric/subsurface;
- biosignature;
- anomaly;
- hazards;
- confidence and source provenance.

A tile may be well known topographically but unknown mineralogically.

## 6.5 Tiered Survey Gameplay

**DECIDED**

### Tier 1: Passive or Initial Orbital Scan

Fast, broad metadata:

- radius/gravity;
- atmosphere;
- hydrosphere;
- mean temperature;
- major hazards;
- rough body classification.

### Tier 2: Orbital Survey Passes

The core map-building mechanic.

Players make choices about:

- equatorial versus polar orbit;
- high/broad versus low/detailed orbit;
- synchronous/focused scanning;
- sensor mode;
- target region.

Atmosphere, weather, altitude, body rotation, sensor quality, and terrain affect results.

### Tier 3: Drone Investigation

Drones investigate local questions raised by orbital scans.

They may:

- confirm or reject anomalies;
- make high-confidence mineral or atmospheric readings;
- collect samples;
- enter hazardous terrain;
- suffer damage, signal loss, or loss.

Core design phrase:

> Orbital scans create questions. Drones answer them.

Drones should initially receive task assignments rather than require manual tile-by-tile piloting.

## 6.6 Survey as an Economy

**DECIDED DIRECTION**

Survey information is a resource that may be:

- kept private;
- stored on a ship;
- shared;
- sold or licensed;
- uploaded to an organization;
- published;
- copied;
- encrypted;
- stolen;
- damaged or lost.

Data may support:

- cartography;
- scientific reputation;
- territorial claims;
- resource speculation;
- exploration contracts;
- corporate espionage;
- news and public archives.

## 6.7 Progress Versus Product

**DECIDED / HISTORICALLY IMPLEMENTED**

The later implementation formalized:

```text
SurveyCoverage
  mutable knowledge/progress owned by a scope

SurveyDataset
  packaged snapshot of coverage

SurveyDatasetTile
  immutable tile rows in a packaged dataset

Survey Data Cartridge
  physical Evennia object linked to a dataset
```

The key rule is:

> Survey progress is not the same object as a transferable survey product.

This prevents trade, copying, or sale mechanics from mutating the live knowledge record by accident.

## 6.8 Historical Survey Command State

**HISTORICALLY WORKING — VERIFY**

Reported commands included:

```text
survey
survey scan
survey status
survey datasets
survey cartridges
survey map
survey map visual
survey map brief
survey map list
survey detail <x> <y>
survey inspect <dataset id or cartridge>
survey export <name>
survey materialize <dataset id>
survey load <cartridge>
```

Reported behavior:

- `survey scan` required an orbiting ship and appropriate crew/owner/admin access;
- it wrote mutable coverage;
- scans returned semantic reports with body, center, footprint, new/updated tiles, terrain, elevation, radiation, temperature, hazards, and follow-up suggestions;
- export created a dataset snapshot;
- materialize created a physical cartridge;
- load merged cartridge information into the holder's coverage.

## 6.9 Next Survey Work Identified in the Archives

**PROPOSED NEAR-TERM**

- scan radius and resolution progression;
- hooks for ship sensor equipment, skill, power, and environmental interference;
- improved target selection;
- dataset valuation metadata;
- transfer, sale, copy, and licensing rules;
- organization archives;
- broader accessibility preferences.

---

# 7. Surface Exploration and Persistent Overlays

## 7.1 Three-Layer Surface Model

**DECIDED**

```text
Space layer
  ships, orbits, navigation

Planet map layer
  procedural grid, surveys, sensor overlays

Room layer
  instantiated locations where characters physically go
```

The map remains large and data-driven. Surface rooms are created on demand for active coordinates and meaningful sites.

## 7.2 Canonical Surface Address

**HISTORICALLY IMPLEMENTED — VERIFY**

The archived project brief used:

```python
{
    "system_name": "Astalon",
    "body_id": "planet-1",
    "body_name": "Astalon I",
    "x": 10,
    "y": 25,
}
```

Canonical planet key:

```python
f"{system_name}:{body_id}"
```

Example:

```text
Astalon:planet-1
```

Generated rooms were tagged:

```text
generated_surface_room
category: surface
```

## 7.3 Generated Rooms Are Cache Objects

**DECIDED**

Core rule:

> Terrain is generated. Player impact is overlaid. Generated rooms are cache objects. Overlays are persistent world state.

Generated rooms may be created, regenerated, cleaned up, or replaced without erasing meaningful activity.

Room descriptions should compose:

1. base planetary terrain;
2. local environmental conditions;
3. procedural flavor;
4. persistent overlays;
5. player-impact overlays;
6. dynamic occupants and objects.

## 7.4 Surface Overlays

**DECIDED / HISTORICALLY IMPLEMENTED**

Persistent surface features live independently from generated room text, preferably in Django models.

Overlay examples:

- landed ship anchor;
- player-built point of interest;
- beacon or claim marker;
- construction site;
- mining/extraction site;
- wreckage;
- survey marker;
- discovered ruin;
- hazard;
- terrain scar or damage.

Typical overlay fields:

- planet key;
- x/y coordinate;
- overlay type;
- optional source object and owner;
- JSON payload;
- permanence;
- whether it blocks room cleanup;
- visibility;
- creation/update timestamps.

## 7.5 Landed Ships

**DECIDED / HISTORICALLY WORKING — VERIFY**

Landing creates or updates a persistent `landed_ship_anchor` at the surface coordinate.

Taking off removes the anchor. Once no blocking overlay or meaningful content remains, the generated room may become cleanup-eligible.

The test flow using Wayfarer reportedly worked:

```text
ship lands at Astalon I / coordinate
→ surface room exists
→ player disembarks
→ room describes Wayfarer resting nearby
→ player moves across generated terrain
→ returning to the landing coordinate shows the ship
→ player boards/embarks
```

## 7.6 Cleanup Safety

**DECIDED / HISTORICALLY IMPLEMENTED**

A generated surface room is cleanup-safe only when it is:

- positively identified as generated;
- unoccupied by players;
- free of meaningful persistent contents;
- not manually protected;
- not referenced by pending events;
- free of blocking overlays;
- otherwise marked ephemeral.

Do not delete a room simply because it was procedurally generated.

## 7.7 Regeneration

**DECIDED**

Regeneration updates procedural terrain and environmental data while reapplying overlays.

An ordinary regeneration command must not delete:

- ships;
- structures;
- player modifications;
- POIs;
- markers;
- surface damage;
- persistent discoveries.

Wiping overlays is a separate destructive administrative action.

## 7.8 Historical Surface Commands

**HISTORICALLY WORKING — VERIFY**

Reported player/dev commands included:

```text
surface
surface where
surface move <direction>
surface ships
surface board <ship>
surface takeoff <ship>

@surfaceoverlays
@addsurfacepoi
@removesurfaceoverlay
@regensurface
@surfacecleanupcheck
@surfacecleanuphere
@surfacecleanupsweep
```

Generated surface rooms eventually used a dedicated typeclass so ordinary movement and `look` rendered the procedural view exactly once.

---

# 8. Ships and Ship Interiors

## 8.1 Unique Purchased Ships

**DECIDED DIRECTION**

A purchased ship is a unique persistent authoritative object, not merely a copied collection of rooms.

The model:

```text
ship template/recipe
→ factory creates unique Ship object
→ factory creates interior rooms and exits
→ rooms point back to Ship
→ Ship stores mutable mechanics, registry, ownership, and important room references
```

The template is preferably structured Python/JSON data rather than a live in-game prototype room tree.

## 8.2 Identity and Ownership

**DECIDED DIRECTION**

Use a real immutable/stable registry attribute rather than relying on aliases.

Potential identifiers:

```text
SCOUT-000001
SOL-SCOUT-000001
```

Account-level ownership plus character authorization was recommended so ships can support:

- owner;
- captain;
- crew;
- passengers;
- organizational ownership;
- future transfers and leases.

## 8.3 Historical Ship State and Access

**HISTORICALLY WORKING — VERIFY**

Reported ship states:

```text
unknown
in_system
orbiting
landed
docked
in_transit
```

Reported access roles:

```text
owner      full control/manage
crew       operate, survey, land, take off, board
passenger  board/disembark
admin      override
```

Reported commands included:

```text
ship
ship status
ship list
ship board <ship>
ship create <name>
ship land <x> <y>
ship takeoff
ship embark
ship disembark
ship interior
ship access
ship access add <player> <owner|crew|passenger>
ship access remove <player>
```

The historical prototype used a canonical airlock room rather than a complete interior.

## 8.4 Default Ship Architecture: Thrust Towers

**CANON / DECIDED — LATEST SHIP DESIGN**

The default crewed ship should use acceleration as gravity.

Ships are tower-like:

```text
Nose / Sensors
Command
Habitation
Operations / Utility
Cargo / Drones / Vehicles
Engineering
Reactor / Drive
Exhaust
```

Under normal sustained thrust:

- the drive is downship;
- the nose is upship;
- decks are stacked perpendicular to the thrust axis;
- the interior is normally usable;
- the ship AI plans an "optimal-ish" course that keeps useful thrust when practical.

Artificial gravity was rejected as the default because it would imply a much larger technological leap and downstream setting consequences than desired.

Other profiles—spin, microgravity, artificial, hybrid—may exist later, but acceleration gravity is the primary design target.

## 8.5 Ship Gravity States

**DECIDED**

Use a simple ship-wide operational state rather than simulating full interior vectors.

Suggested states:

```text
thrust        normal livable acceleration gravity
microgravity  engines off/disabled, coasting, drifting, or some docked states
maneuver      temporary acceleration transition/event
```

Interior orientation is mostly conveyed by descriptions and metadata. Do not make players constantly solve changing orientation.

## 8.6 Microgravity

**DECIDED**

Microgravity is meaningful but deliberately abstracted.

Initial effects:

- heavy movement delay/penalty;
- slower or interrupted repair actions;
- melee and rescue penalties;
- increased difficulty with bulky cargo;
- hazards from unsecured objects.

The first implementation only needs a clear movement penalty and appropriate messaging.

Possible later skills/traits:

- zero-G training;
- spacer background;
- EVA specialist;
- shipboard combat training.

## 8.7 Bracing, Seating, and Maneuver Risk

**DECIDED**

When thrust engages, cuts out, or changes sharply, unsecured occupants may be injured by being thrown around rooms and corridors.

Player safety states:

```text
unsecured < braced < seated < strapped < crash couch
```

The `brace` command is emergency mitigation while a player moves toward a proper seat. It is helpful but inferior to a harness or acceleration couch.

Suggested commands:

```text
sit
stand
strap in
unstrap
brace
release
```

Maneuver severity may range from minor corrections through hard burns and evasive maneuvers to catastrophic acceleration events.

Consequences should eventually include statuses, not merely hit-point loss:

- dazed;
- bruised;
- knocked down;
- floating/disoriented;
- pinned;
- bleeding;
- unconscious.

## 8.8 Routine Versus Emergency Operation

**DECIDED**

Routine travel should not punish players without warning.

Ship AI normally:

- announces thrust changes;
- provides a grace period;
- smooths ordinary course corrections;
- maintains safe/livable profiles;
- recommends seats or handholds.

Combat, sabotage, damage, evasive action, or sudden engine recovery may shorten or eliminate warnings.

Guardrails:

- ordinary departures should be readable and usually survivable;
- emergency and combat maneuvers may be dangerous;
- rooms must clearly describe handholds, seats, harnesses, couches, and loose-object hazards;
- microgravity should be a meaningful abnormal state, not constant annoyance.

## 8.9 Interior Layout and Metadata

**DECIDED DIRECTION**

Tower ships should use stacked decks with lateral rooms/rings around a central shaft so they do not become a boring single vertical line.

Usable direction vocabulary:

- up / upship / noseward;
- down / downship / driveward;
- port / starboard;
- fore / aft;
- inboard / outboard.

Simple aliases should always be available.

Suggested room metadata:

```text
ship_id
deck_index
deck_name
zone
gravity_profile
gravity_state
has_handholds
has_seating
has_harnesses
has_crash_couches
loose_object_risk
microgravity_move_modifier
maneuver_risk_modifier
```

**HISTORICAL STATUS**

The tower-ship gravity design was the latest major design addition. The archived brief stated that it had not yet been implemented.

---

# 9. Conflict, Piracy, and Warfare

## 9.1 PvP Philosophy

**DECIDED DIRECTION**

PvP should exist and matter, but it should be strategic and geographically/politically bounded.

The intended intensity gradient:

- core systems and starter/social areas: safe or heavily restricted;
- regulated colonies: limited conflict under law/crime systems;
- frontier: meaningful piracy and risk;
- unclaimed deep space: high risk;
- declared war zones: open conflict between authorized belligerents;
- simulations/arenas: no-loss practice.

High-value frontier activity should carry more danger than ordinary life in core space.

## 9.2 What PvP Should Threaten

**DECIDED DIRECTION**

PvP should more often threaten:

- missions;
- cargo;
- survey data;
- ships and repair costs;
- routes and schedules;
- outposts and infrastructure;
- territorial claims;
- reputation and legal status;
- political objectives.

Avoid making permanent character destruction or weeks of lost progress the default result.

Loss must matter without routinely becoming a rage-quit event.

## 9.3 Ship and Fleet Focus

**DECIDED DIRECTION**

The major competitive game should center on ships, crews, infrastructure, sensors, logistics, and objectives rather than IRE-style individual affliction duels.

Promising combat dimensions:

- range bands and maneuver;
- heat and reactor load;
- armor, shields, and facings;
- sensors, locks, signatures, and jamming;
- weapon and ammunition state;
- subsystem damage;
- communications;
- boarding;
- formations;
- repairs and power rerouting.

Crew roles may include pilot, tactical, engineering, sensors/electronic warfare, security/marines, and captain.

Solo operation must remain possible, while coordinated crews gain advantages.

## 9.4 Piracy

**DECIDED**

Piracy should be a profession, not a synonym for random killing.

Pirate mechanics should support:

- cargo scanning;
- demands and negotiation;
- jamming;
- disablement;
- boarding;
- ransom;
- cargo seizure;
- false transponders;
- hidden bases;
- laundering;
- reputation and safe-passage deals.

Counterplay should include escorts, insurance, convoys, decoys, alternate routes, beacons, patrols, countermeasures, bounties, and retaliation.

Crucial economy rule:

> Piracy should usually be more profitable when the victim survives.

## 9.5 Warfare

**DECIDED DIRECTION**

Large-scale war should use legible strategic objectives rather than kill counts.

Examples:

- capture or disable a relay;
- blockade a corridor;
- seize a fuel depot;
- sabotage a sensor array or refinery;
- protect or interdict a convoy;
- evacuate a colony;
- raid a shipyard;
- contest a construction site;
- recover a rare artifact;
- enforce or challenge a charter ruling.

This ensures explorers, miners, crafters, haulers, diplomats, spies, and engineers contribute to war.

## 9.6 Development Order

**DECIDED STAGING**

Do not build warfare before there is anything worth fighting over.

1. Exploration, generation, surveys, ships, discoveries.
2. Resources, crafting, cargo, markets, supply chains.
3. Organizations, claims, outposts, charters, diplomacy.
4. Piracy, law, interdiction, bounties, smuggling.
5. Declared war, fleet objectives, treaties, reparations.

---

# 10. Media, News, Ads, and Historical Memory

## 10.1 Structured Event Logging

**DECIDED STANDING REQUIREMENT**

Every new system should be evaluated for newsworthy/auditable events.

Events should contain, where relevant:

- timestamp;
- system/body/coordinate;
- involved characters, ships, and organizations;
- event type and severity;
- public/private/secret visibility;
- legal status and authorization;
- short factual summary;
- structured metadata;
- newsworthiness;
- confirmation or uncertainty.

Potential consumers:

- generated news;
- official bulletins;
- organization and character histories;
- public archives;
- rumors;
- legal records;
- market/logistics reports;
- war and discovery histories.

## 10.2 Periodic AI-Assisted News

**DECIDED DIRECTION, OPTIONAL EXTERNAL SERVICE**

The project may use an LLM API periodically—not continuously—to turn structured public events into in-universe news.

Do not send raw logs directly.

Preferred pipeline:

```text
game emits structured events
→ selector ranks public/newsworthy events
→ compact factual summaries are prepared
→ model drafts an article in a defined publication voice
→ staff review initially
→ approved article is published and archived
```

Important safeguards:

- never expose secret/private events;
- forbid invented casualties, quotes, officials, laws, or facts;
- distinguish confirmed reports from rumors;
- validate referenced entities;
- provide a correction process;
- start with human review;
- use batch/asynchronous processing and spending caps;
- keep important NPC decisions and game rules deterministic.

A weekly frontier digest was proposed as the safest first experiment.

## 10.3 In-Game Media Framework

**DECIDED DIRECTION**

Media is gameplay infrastructure, not merely flavor.

Potential channels:

- news;
- Earth/government bulletins;
- organization notices and press releases;
- classifieds and services;
- crew recruitment and personals;
- contracts;
- trade/market reports;
- rumors and pirate channels;
- survey/discovery digest;
- obituaries and memorials.

## 10.4 Advertisements, Personals, and Contracts

**DECIDED DIRECTION**

Players and organizations should be able to advertise, recruit, socialize, and create public political theater.

Ads/personals may support:

- crew recruitment;
- hauling and escort work;
- crafted goods and station services;
- colony recruitment;
- business and expedition partners;
- mentors/apprentices;
- political campaigns and propaganda;
- social invitations and RP hooks.

Keep **ads** and **contracts** distinct:

- an ad is speech and visibility;
- a contract is a mechanical record with issuer, task, reward, collateral, expiry, acceptance, and completion state.

Distribution may be local, regional, system-wide, interstellar, official, or black-market. Geography and relay access may affect reach.

## 10.5 Player-Authored History

**CANON / CORE PILLAR**

The game should record:

- first discoveries;
- first surveys and landings;
- named regions;
- lost expeditions and destroyed ships;
- colony and outpost founding;
- charter grants and revocations;
- political crises and wars;
- public maps and registries;
- memorials.

Player activity should become canon history where the rules permit.

---

# 11. Commercial and Community Design

## 11.1 Commercial Context

The user previously worked as a Producer/game head for Iron Realms Entertainment and supplied historical comparison figures:

- Midkemia Online: roughly 30 average concurrent users and approximately USD 30,000–150,000 annual revenue during the user's tenure.
- Achaea: roughly 100–150 average concurrent users and generally seven-figure annual revenue, as recalled by the user.

These are user-provided historical comparisons, not current forecasts.

The project does not presently have a fixed commercial-success target. The discussion was intended to recalibrate what "small but successful" could mean outside the IRE flagship model.

## 11.2 Monetization Is Not Settled

**OPEN**

The user raised a possible USD 5 character-permanence purchase that would exempt a character from inactivity purges. Weekly purges were considered.

The discussion recommended reframing this as legacy registration and warned that weekly deletion or "pay or lose your character" would feel punitive. Longer inactivity thresholds and generous free preservation rules were proposed.

No monetization model or purge schedule should be treated as final.

## 11.3 Ethical Direction

**DECIDED PREFERENCE**

There is strong concern about pay-to-win systems, particularly premium artifacts or upgrades that directly affect combat, surveying, travel, extraction, or economic dominance.

The favored principle:

> Sell permanence, expression, breadth, and personal narrative space—not victory.

Potential lower-risk categories:

- character/account legacy protection;
- extra character slots;
- additional ship ownership/registry capacity, if all ships remain earnable;
- cosmetic ship and room customization;
- personal quarters and display/archive spaces;
- organization identity infrastructure;
- map/archive organization tools that do not reveal more data;
- supporter subscription with cosmetic/archive benefits;
- staff-reviewed custom descriptions and memorials;
- cosmetic ad placement.

High-risk categories:

- superior paid ships or modules;
- sensor range/resolution;
- resource or crafting multipliers;
- faster travel;
- combat advantages;
- exclusive strategic territory/resources;
- paid automation that produces economic power.

The middle-ground concept was **horizontal breadth rather than vertical dominance**.

## 11.4 Marketing Position

**DECIDED DIRECTION**

Do not market only through nostalgia or "remember MUDs?"

Potential audiences:

- blind and low-vision players;
- interactive-fiction readers;
- tabletop roleplayers;
- science-fiction readers and worldbuilders;
- MMO veterans seeking persistence and consequence;
- strategy/logistics players;
- mappers, catalogers, and systems thinkers;
- people seeking slower, non-twitch multiplayer;
- roleplayers who want mechanics and geography beyond freeform chat;
- players on low-end hardware or limited connections.

Useful umbrella description:

> A persistent text-based space MMO where players survey planets, chart unknown systems, command ships, form crews and corporations, and leave permanent marks on a shared galactic history.

## 11.5 Environmental Transparency

**DECIDED INTEREST, METHOD NOT FINAL**

The user wants transparent disclosure of generative-AI use and its environmental cost.

The archived recommendation was:

- do not claim false precision when providers do not expose per-request energy, water, and carbon data;
- report bounded estimates and assumptions;
- separate AI-assistance, development infrastructure, runtime hosting, and hardware;
- track approximate development sessions and server uptime;
- periodically publish a range with limitations;
- re-research current factors before any public report.

No historical numerical estimate should be copied into a public disclosure without fresh sourcing.

---

# 12. Engineering Principles

## 12.1 Engine and License

**DECIDED**

Evennia was selected as the engine because its Python/Django/Twisted architecture and flexible object/command/web stack fit custom simulation better than a traditional Diku/ROM-derived engine.

Use Evennia primarily for:

- networking and sessions;
- accounts and characters;
- persistence;
- commands;
- web/admin tools;
- instantiated rooms and objects.

Use custom data/model layers for:

- stars and orbits;
- planetary grids;
- surveys;
- spatial simulation;
- generated content;
- event and media systems.

Evennia uses the BSD 3-Clause License. The prior review concluded that commercial and proprietary use is permitted, provided required copyright/license/disclaimer notices are preserved when distributing the engine and its authors are not represented as endorsing the game.

Verify the current upstream license text before distribution.

## 12.2 Data-Driven World

**DECIDED**

Avoid modeling the entire galaxy or every planet as rooms.

Use durable IDs, deterministic generation, database models, structured imports, and on-demand materialization.

## 12.3 Service Layers

**DECIDED ENGINEERING PRACTICE**

Commands should parse intent and call services/helpers.

Prefer:

```text
commands.py
  access checks, parsing, messages

services.py / scanning.py / generation.py / map_readout.py
  actual behavior
```

Do not place entire subsystems inside command classes.

## 12.4 Root Command Indexes

**DECIDED / HISTORICALLY USED**

Every major command group should have an access-aware root index:

```text
ship
surface
survey
player
system
```

A bare root should normally explain available subcommands instead of silently executing a major action.

Keep command-index files updated when adding commands.

## 12.5 Accessibility Definition of Done

**DECIDED**

Before completing a new player-facing feature, verify:

- all state has a semantic text representation;
- ANSI and symbols have labels;
- screen-reader output is ordered and reasonably concise;
- dangerous actions are explicit;
- maps/charts have summary/list/detail alternatives;
- command syntax works with aliases/macros;
- output spam can be controlled.

## 12.6 Event Definition of Done

**DECIDED**

Before completing a new system, ask:

- Does this action matter to law, news, history, markets, organizations, or analytics?
- If so, what structured event should it emit?
- What visibility classification applies?
- What facts can safely become public?

## 12.7 Database and Migration Practice

**HISTORICAL SERVER PRACTICE — VERIFY**

Use Evennia migration commands from the game root, not a nonexistent raw `manage.py`:

```bash
/home/mud/games/evennia-env/bin/evennia makemigrations <app>
/home/mud/games/evennia-env/bin/evennia migrate
```

Compile changed modules before restart where practical.

## 12.8 Preserve Tested Work

**DECIDED ENGINEERING PRACTICE**

The archived collaboration suffered from generated replacement files falling behind the repository.

Codex should:

- inspect current files before editing;
- patch minimally;
- preserve unrelated local changes;
- confirm imports and command registration;
- test the actual working tree;
- avoid replacing a whole module with an older generated version.

---

# 13. Historical Implementation Snapshot

Everything in this section is **HISTORICALLY WORKING** according to archived conversations and must be verified in the recovered repository/database.

## 13.1 Reported Stack

- Evennia 6.0.0 at the time of troubleshooting.
- Ubuntu 24.04 DigitalOcean development server.
- PostgreSQL 16.x.
- Python virtual environment.
- GitHub repository.
- systemd service for automatic startup.

## 13.2 Reported Repository and Paths

```text
Repository: github.com/rillian118/ExplorationGame
Historical working branch: systemgen
Server game root: /home/mud/games/exploration
Evennia executable: /home/mud/games/evennia-env/bin/evennia
Python executable: /home/mud/games/evennia-env/bin/python
Historical public IP: 137.184.26.215
Telnet port: 4000
Web client: 4001
Web admin: 4001/admin
```

Treat the IP, branch, paths, versions, credentials, and hosting state as historical notes to verify, not current truth.

## 13.3 Reported Working Features

- PostgreSQL-backed Evennia setup.
- GitHub push/pull workflow.
- systemd auto-start.
- generated stellar systems and JSON import.
- system list/scan/body displays.
- procedural surface rooms.
- cardinal and diagonal surface movement.
- generated-room typeclass and normal appearance.
- persistent surface overlays.
- landed ship anchors.
- cleanup-safe generated rooms.
- ship create/list/status and location state.
- ship land/takeoff and embark/disembark.
- canonical ship airlock.
- owner/crew/passenger access.
- orbital survey scans.
- semantic scan reports.
- survey coverage and accessible map renderers.
- dataset export.
- physical survey data cartridges.
- loading cartridge data.
- player preferences for survey-map output.

## 13.4 Known Historical Test Entities

```text
System: Astalon
Body: Astalon I / planet-1
Ship: Wayfarer
Common test coordinate: 10,25 or nearby
```

These are fixtures/examples unless adopted as canon elsewhere.

---

# 14. Recommended Recovery Workflow for the New Codex

1. Read this file completely.
2. Locate or clone the actual `rillian118/ExplorationGame` repository.
3. Inspect branches and recent commits; do not assume `systemgen` is still current.
4. Read any current development-map/roadmap file.
5. Run tests or compile checks before changing anything.
6. Inventory which historical features are actually present.
7. Reconcile the code inventory with Section 13.
8. Preserve the latest tower-ship design even though it may not yet be implemented.
9. Confirm priorities with the user after the code audit if the current development map is ambiguous.

A useful first audit should answer:

- Is the stellar generator and importer present?
- Is PlanetGen v0.1 present, and where are its generated/cached artifacts?
- Are Django models and migrations for surface overlays and surveys present?
- Which ship commands and access rules exist?
- Are survey datasets/cartridges implemented?
- Are visual/brief/list/detail maps working?
- Does a development-map file identify the next task?
- Does the database containing Astalon/Wayfarer still exist, or must fixtures be recreated?

---

# 15. Open Questions

Do not decide these silently.

## Setting

- Final game title.
- Calendar/era and exact technology timeline.
- Name and structure of Earth's authority.
- Exact name and wording of the AI combat constraints.
- How jump drives work beyond their range gate.
- Whether a 2-ly content phase remains useful or the first interstellar engine should reach roughly 5 ly.
- Rarity and role of spin or artificial gravity.
- Conditions under which a second human-compatible biosphere can exist.

## Politics and PvP

- Exact charter application, renewal, and enforcement process.
- Degree of staff versus automated authority.
- Death, insurance, ship loss, capture, salvage, and ransom rules.
- Precise geographical PvP boundaries.
- How pirate AI corruption is acquired, detected, and punished.
- Whether engine restart is a deliberate anti-boarder tactic and how it is balanced.
- Population level required before multi-faction warfare becomes viable.

## Ships

- First complete tower-ship template and room graph.
- Whether docked ships are normally in microgravity.
- Availability and strength of mag boots.
- Warning time before routine burns.
- Lethality of catastrophic maneuvers.
- How ship AI behaves when damaged, corrupted, or partially offline.

## Generation

- Canonical projection and coordinate wrapping at the poles/seam.
- Long-term cached/chunked world storage format.
- Version migration when generation algorithms change.
- How much geology/resources are generated in advance versus on activation.
- Rules for mutable terrain and resource depletion.

## Surveys

- Final confidence merge rules and provenance display.
- Sensor equipment, crew skill, power, weather, and orbit effects.
- Dataset copy, licensing, encryption, theft, and degradation.
- Organization archives and public publication.
- Drone object model and loss/recovery loop.

## Economy and Monetization

- Whether the game will monetize at all.
- Inactivity/purge policy.
- Legacy registration price and guarantees.
- Subscription, ship slots, organization services, ads, and commissions.
- Hard published anti-pay-to-win boundaries.

## Media and Accessibility

- Publication names and editorial voices.
- Event visibility/redaction policies.
- Human-review requirements for generated news.
- Exact screen-reader preference set.
- ANSI/Unicode defaults per client.
- Which structured UI protocol should support enhanced clients.

---

# 16. Conversation Provenance

This reconstruction used the project-linked conversations available in the Codex app:

- **MUD Engine Selection Guide**
  - engine selection, controlled frontier expansion, server setup, unique ship creation.
- **Planetary Map Generator**
  - PlanetGen architecture, geology, storage, render modes, v0.1 stopping point.
- **Piloting UI Planet Maps**
  - map/survey layering, ASCII interface, data grids versus rooms.
- **MUD Graphical Overlay Ideas**
  - optional Mudlet/web graphical enhancement and structured UI events.
- **Stellar System Design MUD**
  - deterministic ephemerides, rotation, moons, 2.5D navigation, temporary spatial objects.
- **Next Steps for System Design**
  - system import, surface generation, ships, landed state, historical milestones.
- **Ship-Survey Mechanics Ideas**
  - orbital passes, drones, scoped knowledge, confidence, transferable data.
- **Surface Overlays Design**
  - persistent overlays, cleanup, ship access, surveys, cartridges, accessible maps, preferences, prior Codex brief.
- **Ship Design Models**
  - tower ships, acceleration gravity, microgravity, bracing, maneuver injury.
- **Monetization in MUDs**
  - monetization, market position, gameplay pillars, PvP, Earth politics, ship AI, media, accessibility.
- **Evennia License Stipulations**
  - BSD 3-Clause implications.
- **Server Auto-Startup Configuration**
  - historical systemd setup.
- **VS Code Setup Guide**
  - historical local/remote workflow.
- **SSH Key GitHub Setup**
  - repository identity and initial push.

Pure troubleshooting details were intentionally condensed unless they reveal a design rule, implemented subsystem, server fact, or known recovery risk.
