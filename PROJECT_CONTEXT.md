# Exploration MUD Project Context

This document preserves the high-level vision, design principles, and current
open questions for the project. It should be updated as earlier design
conversations are recovered and as decisions are made.

For implementation status and near-term work, see `DEVELOPMENT_TODO.md`.

The complete reconstruction of earlier ChatGPT design conversations is
preserved in `docs/EXPLORATION_MUD_PROJECT_CONTEXT_RECOVERED.md`. That document
contains substantially more detail about planetary generation, surveys,
interfaces, ships, politics, media, commercial considerations, engineering
practice, and the historical server environment. Read it before planning
substantial feature work.

When project sources disagree:

1. Current code and database state determine what is implemented.
2. Confirmed user decisions determine intended direction.
3. Historically reported behavior must be verified before being treated as
   currently working.
4. Proposals and illustrative examples are not canon unless adopted.
5. Genuine conflicts should be brought to the project owner rather than
   resolved silently.

Use these labels when recording recovered design material:

- **CANON** — established setting or project premise.
- **DECIDED** — a direction explicitly accepted by the project owner.
- **HISTORICALLY IMPLEMENTED** — reported as implemented; verify in the
  current checkout.
- **HISTORICALLY WORKING** — reported as tested; verify against the current
  checkout and database.
- **PROPOSED** — a recommendation or brainstorm not explicitly adopted.
- **OPEN** — unresolved and not to be decided silently.

## Project Background

The project is led by a former Iron Realms Entertainment developer who served
as head developer of Midkemia Online (MKO). It is an independent attempt to
build a persistent space-themed MUD around the systems, themes, and forms of
player agency that most interest its creator.

The game should provide enough interconnected simulation and player control
for players to create their own stories. Smaller authored campaigns and
stories can then be built on top of that systemic foundation.

The initial audience is expected to be established MUD players. A normal
concurrent population may be no more than a few dozen players unless the game
becomes unusually popular. The architecture and presentation should not
preclude eventually reaching a wider audience.

## High-Level Vision

The game combines individual character play with a larger ship and space
layer. Very loose genre comparisons include aetherships in Lusternia and
seafaring in Achaea, but the intended mechanics and setting are specific to
this project.

Players should eventually be able to:

- Explore and survey star systems.
- Own and operate ships.
- Claim land and resource rights.
- Establish modest personal bases and mining claims.
- Mine, retrieve, transport, trade, and process resources.
- Create and govern player-run organizations.
- Establish organization-scale colonies, industry, bases, and fleets.
- Protect trade, engage in piracy, and wage sanctioned wars.
- Generate stories through economic, political, territorial, and military
  interaction.

The broad systemic chain is:

`exploration -> surveying -> claims -> extraction -> shipping -> production -> colonization -> political and military conflict`

Features should strengthen this connected world rather than become isolated
minigames.

A further core stage is **recording**. Discoveries, settlements, conflicts,
charters, losses, and other significant player actions should become durable
world history through registries, archives, news, organizational records, and
memorials. The world remembering what players did is a defining part of the
project rather than incidental flavor.

## Tone and Scientific Approach

The desired tone is relatively realistic, harder modern science fiction in the
general vein of *The Expanse*. Realism is a tool for creating meaningful
constraints and texture, not a requirement to simulate every physical detail.
Gameplay needs may justify abstraction.

Important physical assumptions include:

- Crewed ships normally use thrust and acceleration as gravity.
- Ship interiors are arranged with acceleration-gravity in mind.
- Inertia, thrust changes, microgravity, and securing oneself can matter.
- These systems may affect boarding actions, combat, injury, movement, loose
  cargo, and other interior interactions.
- Artificial gravity should not be the ordinary default.
- Ship AI and autopilot normally plan survivable thrust profiles and warn the
  crew before routine changes.

The game should use understandable state abstractions where detailed physics
would create friction without improving decisions or stories.

## Setting

Human civilization has expanded from Earth into the Solar System. Earth has a
unified planetary government, but distance and the scale of space make direct
control progressively harder.

Earth responds by issuing charters to organizations for exploration, commerce,
colonization, and related activity. This charter system is intended to become
part of the foundation for player-run organizations.

Earth is also initially the only natural source of the complete,
human-compatible biosphere needed for large-scale settlement and
terraforming. Alien life is not assumed to be biologically compatible with
terrestrial life. Biosphere packages, seed stock, quarantine, and ecological
licenses can therefore remain important logistical and political instruments
even as humanity expands.

Earth itself is politically and mechanically sacrosanct:

- It is a safe area for new players.
- Offensive space combat near Earth is prohibited by hard game rules.
- Some restrictions remain absolute even when ordinary ship controls are
  bypassed.

Authority, enforcement, and practical independence should change as players
move farther from Earth. The setting should create a gradient from protected
core territory to increasingly autonomous and dangerous frontiers.

## Sol and Expansion

The Solar System is the initial playable region and training ground. Players
should learn navigation, ship operation, surveying, exploration, and the
beginnings of the economic loop within Sol before pushing outward.

Sol should use realistic source data where practical, supplemented by
plausible procedural generation where necessary.

The final faster-than-light model remains undecided. Leading possibilities
include:

- Alcubierre-style compression paths connecting stars.
- Traversable gates.
- A hybrid network.

Whatever model is selected should create meaningful interstellar geography,
including commercial corridors, choke points, strategic infrastructure,
piracy opportunities, and military objectives.

Expansion should be released in controlled frontier bands. New stellar
content can be generated deterministically offline, reviewed, exported in a
canonical format, and imported before longer-range travel becomes available.
An earlier two-light-year proposal does not reach a conventional neighboring
star and remains an open planning issue; it may instead describe a deep-Sol
phase, with a later range sufficient to reach Alpha/Proxima Centauri.

## Ships and Ship AI

Space navigation and combat require complex calculations, so ships carry AI
assistants or governors. These systems plot courses and operate combat systems
with minimal human intervention.

Ship AI also provides an in-world mechanism for law and an out-of-world
mechanism for controlling combat and piracy:

- Unmodified AI generally prevents offensive combat outside sanctioned wars
  between organizations.
- A prospective pirate may need to corrupt or otherwise subvert the ship AI
  before it permits aggressive behavior.
- Some prohibitions, such as combat near Earth, remain fully hardcoded and
  cannot be defeated through ordinary AI corruption.

The exact rules for AI corruption, detection, repair, self-defense,
jurisdiction, evidence, and punishment remain to be designed. This is expected
to be a defining system rather than merely a PvP toggle.

Ship systems should eventually retain structured evidence about authorization,
identity, demands, responses, weapons fire, damage, location, and applicable
charters or warrants. These records can support law, insurance, bounties,
politics, news, and staff investigation.

## Characters and Skills

Character advancement should use skillsets that affect:

- Which abilities are available.
- How quickly abilities are performed.
- Capacity limits.
- Effectiveness and other multipliers.

Skills should primarily improve through relevant use. Certain items or other
mechanisms may accelerate learning.

Surveying is an early example. Performing and recording surveys should improve
surveying-related skills, unlock additional capabilities, affect action speed
or effectiveness, and increase limits such as the amount of survey data a ship
can hold.

The exact skill taxonomy, progression curves, anti-grinding rules, and
relationship among character skill, equipment, crew, and ship capability
remain open.

## Character Injury and Death

Cloning will provide the setting explanation for effective player-character
immortality. The consequences of death have not yet been decided.

Injury should resemble affliction-based MUD combat systems. Shipboard
acceleration, microgravity, unsecured movement, boarding, and combat may all
interact with injuries and status effects.

Open questions include cloning cost, recovery time, lost state, body recovery,
and the degree of consequence appropriate for character death.

## Ship Loss

Ship destruction should be a meaningful setback without permanently removing
a player's ability to participate. Insurance and replacement systems are
expected, but their form is undecided.

The design must eventually address:

- Replacement cost and delay.
- Coverage levels and eligibility.
- Cargo and equipment loss.
- Insurance fraud and duplication exploits.
- Starter or fallback ship access.
- Organization-owned vessels.
- Recovery after catastrophic losses.

## Economy and Resources

The economy should be built primarily around:

- Resource surveys.
- Mining and retrieval operations.
- Physical or otherwise meaningful shipping.
- Industrial production at starbases and planetary bases.
- Player and organization demand.

Planets should contain a wide range of resources, with some much more common
and easier to survey or extract than others. Resource depletion should occur
at the level of deposits, sites, or local areas. A geologically abundant
resource such as iron on an iron-rich world may be effectively inexhaustible
at planetary scale while individual extraction locations are depleted.

The economy should eventually create visible traffic and opportunities for
trade, protection, interception, piracy, and territorial competition.

Piracy should be a profession rather than random killing. Disablement, cargo
seizure, ransom, boarding, smuggling, laundering, and negotiated passage
should normally be more useful than destroying the victim. In general, piracy
should be more profitable when its victim survives.

Important unresolved subjects include economic sinks, offline production,
ownership during cooperative operations, abandoned assets, market recovery,
and protection against unattended accumulation.

## Ownership, Bases, Colonies, and Organizations

Individual players should be able to:

- Own ships.
- Claim land or extraction rights.
- Establish modest bases.
- Establish mining claims and similar small operations.

True colonies should be created through the organization system. NPC-run
colonies should be limited so that players and player organizations remain the
primary drivers of expansion.

Player-controlled organizations should eventually enable:

- Formal charters.
- Large-scale bases and colonies.
- Major industrial production.
- NPC fleets.
- Large-scale shipping.
- Territorial administration.
- Diplomacy and sanctioned war.

The relationships among character, crew, ship, organization, claim, colony,
and territorial ownership still require a formal model.

## Time and Travel

The current general time assumption is approximately one real hour to one game
day. This ratio is not sufficient by itself to make realistic travel times
across a solar system enjoyable.

Travel should therefore be adjusted or abstracted to meet gameplay needs. The
game may avoid stating an exact universal conversion where doing so would
create contradictions.

Still to be determined:

- How long common journeys should take in real time.
- Whether travel is continuous, staged, or event-driven.
- What characters can do aboard a ship while traveling.
- What happens to travel and operations while players are offline.
- How interception and route changes work.
- Which physical consequences remain visible despite compressed time.

## Interface and Accessibility

The authoritative game must work as a text-based MUD. Graphical presentation
is optional enhancement rather than a requirement for play.

Screen-reader accessibility for blind and low-vision players is a core design
requirement. Important information must not depend solely on color, ANSI maps,
spatial formatting, or graphical overlays.

Important state should ideally support:

- A concise textual view.
- A detailed textual view.
- An optional ANSI or spatial visualization.
- A screen-reader-friendly alternative.
- Structured data that enhanced clients can consume.

Possible enhanced interfaces include:

- A web-client overlay.
- Mudlet packages and graphical overlays.
- More visually intensive maps, ship displays, and informational panels.

Previously created screen concepts and mockups should be added as references
when recovered, while keeping the underlying commands fully usable in plain
text.

### Recovered Interface Concepts

Three previously generated interface examples establish a progression of
increasing visual complexity. They are design references rather than a final
UI specification.

#### 1. Basic Text Interface

The basic interface remains recognizably a MUD client. It presents:

- Timestamped room and event text.
- Descriptive prose and command output.
- Explicit keyboard-oriented exits or available actions.
- Semantic sensor and planetary data.
- A text/ANSI sector map with a labeled legend.
- A tabular sensor-contact list.
- A normal command prompt.

The concept demonstrates that navigation, surveying, contact identification,
and environmental state remain fully usable without graphical controls.

#### 2. Enhanced Overlay

The enhanced concept retains a large conventional console while adding
structured panels and controls:

- Tabs for console, navigation, scanning, cargo, maps, logs, and settings.
- Persistent ship-system status.
- A compact sensor-contact table.
- A graphical or richly rendered sector map.
- Connection and network status.
- A visible command entry field and ordinary textual transcript.

This tier reorganizes the same information rather than replacing command play.
It is a plausible model for a Mudlet package or enhanced web client.

#### 3. Full Graphical Dashboard

The most complex concept provides a workstation-like ship interface:

- Role or subsystem tabs such as helm, sensors, survey, tactical,
  communications, cargo, crew, logs, and settings.
- A large planetary or spatial visualization with selectable scan overlays.
- A detailed surface survey map with surveyed/unsurveyed regions, hazards,
  anomalies, deposits, and landing sites.
- Ship systems, contacts, ship identity, and visual ship status.
- Separate event and command-output panes.
- A persistent text command line.

Even at this level, commands and semantic output remain visible. The graphical
planet, maps, gauges, icons, and panels should be alternate views of
authoritative structured state, not separate game mechanics.

### Shared Interface Architecture

The concepts imply a useful implementation boundary:

`game services -> structured state/events -> semantic text renderer and optional graphical renderers`

Likely reusable data domains include:

- Current location and environmental description.
- Available contextual actions.
- Ship system status.
- Sensor contacts.
- Orbital or local spatial maps.
- Planetary survey layers and coverage.
- Event history and command output.
- Connection state.

The plain-text client must receive all gameplay-critical information. Enhanced
clients may add persistence, layout, filtering, selection, imagery, animation,
and convenience controls.

The labels “Enhanced Tier” and “Premium Tier” appeared in the concepts. They do
not by themselves establish paid access, product tiers, or a monetization
decision. Whether different interfaces are free, paid, supporter benefits, or
simply alternative clients remains **OPEN**.

Accessibility is part of the definition of done for player-facing features.
New work should verify semantic text output, labeled ANSI and symbols,
reasonable screen-reader ordering and verbosity, explicit dangerous actions,
summary/list/detail alternatives for maps, alias-friendly command syntax, and
controllable output volume.

## Persistent Events and World Memory

Systems should emit structured events when actions matter to law, news,
history, markets, organizations, or operational analysis.

Useful event fields may include:

- Timestamp and spatial location.
- Involved characters, ships, and organizations.
- Event type and severity.
- Visibility and secrecy classification.
- Legal status and authorization.
- A factual summary and structured metadata.
- Confirmation, uncertainty, and newsworthiness.

Potential consumers include public news, government and organization
bulletins, discovery registries, legal and insurance records, market reports,
war histories, rumors, memorials, and staff tools.

Periodic AI-assisted news is a possible later presentation layer. If used, it
should operate on selected and redacted structured facts, initially require
human review, and never become the authority for game rules or important NPC
decisions.

## Current Implementation Direction

The repository currently has working foundations for:

- Stellar-system generation, import, persistence, and inspection.
- Generated planetary surfaces and movement.
- Landed ship overlays, embarkation, landing, and takeoff.
- Canonical ship airlocks and ship access roles.
- Ship sensor packages and survey capability limits.
- Orbital surveying and timed survey operations.
- Survey maps, reports, routes, targeting, coverage, and datasets.
- Survey-data cartridges, loading, valuation, sales, licensed copies, lineage,
  and player trade offers.
- Player display preferences related to survey maps.

See `DEVELOPMENT_TODO.md` and Git history for detailed implementation status.
The roadmap currently understates some completed survey-commerce and licensing
work and should be reconciled before selecting the next feature.

## First Playable Milestone

The first complete player experience has not yet been formally defined. A
candidate shape is:

`arrive on Earth -> learn basic movement and ship interaction -> obtain crew or
ship access -> travel within Sol -> perform a useful survey -> record or export
the data -> sell or share it -> use the proceeds or reputation to gain greater
independence`

This is a provisional framing, not a confirmed design. Defining the first few
sessions of play and the achievement that marks leaving the introductory phase
is the highest-value product decision still needed.

## Major Open Questions

- What is the precise first playable release?
- What is a new character's legal, economic, and social starting condition?
- How viable should solo play be compared with crew and organization play?
- How are alternate characters and shared account assets handled?
- How do sanctioned war, self-defense, jurisdiction, AI corruption, evidence,
  and legal consequences work?
- Which systems continue operating while players are offline?
- How are offline assets protected without making conflict meaningless?
- What are the principal economic sinks?
- How do ship insurance and character cloning preserve consequence?
- What travel times produce good play within Sol and between stars?
- What FTL model best supports strategic geography?
- What is the era, current settlement map, and existing political landscape?
- How common are cloning, augmentation, and advanced AI outside ships?
- What command and presentation conventions should all systems follow?

## Context Still to Recover

Earlier ChatGPT conversations and previously generated interface screens may
contain decisions or examples not yet represented here. As they are recovered,
capture:

- Confirmed design decisions and their reasoning.
- Rejected alternatives where they prevent repeated discussion.
- Gameplay-loop and command examples.
- Interface and accessibility conventions.
- Setting details that constrain mechanics.
- Milestone definitions.
- Known technical limitations and operational procedures.
