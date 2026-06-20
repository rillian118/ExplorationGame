# Exploration MUD Development Todo

Shared working list for future development stages. Keep entries concise and
move items forward as they are implemented, tested, or superseded.

## Now

- [x] Pull and smoke-test the ship sensor package feature on the server.
- [x] Verify `ship sensors packages`, `ship sensors install`, and `ship capabilities clear` in-game.
- [x] Verify survey radius/resolution caps respond to installed sensor packages.
- [x] Add first-pass ANSI survey map and scan-footprint visualization.

## Next

- [x] Add richer survey scan progression beyond radius/resolution caps.
- [x] Add survey target selection improvements.
- [x] Add survey route/readout commands.
- [ ] Add dataset valuation metadata.
- [ ] Decide the first shape of survey data market/sale mechanics.

## Later

- [ ] Add cartridge transfer/copy/licensing rules.
- [ ] Add organization-owned survey archives.
- [ ] Add broader accessibility preferences.
- [ ] Add screen-reader verbosity settings.
- [ ] Add ANSI/color preference.
- [ ] Add room description verbosity preference.
- [ ] Integrate survey visuals with planet-generation map layers and palettes where practical.
- [ ] Expand ship interiors beyond the canonical airlock.
- [ ] Add sensor effects from damage, power allocation, crew skill, and environment.
- [ ] Make ship survey datasets extend to crew access where appropriate.
- [ ] Revisit survey dataset ownership so ship-generated data can be tied to the ship, not only the player.
- [ ] Build ship interiors as acceleration-gravity tower ships with stacked decks.
- [ ] Add upship/downship, noseward/driveward, port/starboard, fore/aft, and inboard/outboard interior language.
- [ ] Add simple aliases such as `up` = upship/noseward and `down` = downship/driveward.
- [ ] Reserve or implement `gravity_profile` and `gravity_state` for ships and ship rooms.
- [ ] Add ship-room metadata for deck, zone, handholds, seating, harnesses, crash couches, loose-object risk, and gravity/maneuver modifiers.
- [ ] Implement first-pass ship room templates for bridge, habitation, operations, cargo, engineering, reactor, and drive sections.
- [ ] Add player safety states: unsecured, braced, seated, strapped, and crash couch.
- [ ] Add basic safety commands: brace, release, sit, stand, strap in, and unstrap.
- [ ] Add first-pass microgravity movement/action penalties.
- [ ] Add maneuver severity events: minor, hard burn, evasive, and catastrophic.
- [ ] Add maneuver injury/status effects such as dazed, bruised, prone, floating, disoriented, pinned, bleeding, and unconscious.
- [ ] Add ship AI warnings for routine burns and thrust changes.
- [ ] Add cargo bay loose-object hazards during maneuvers.
- [ ] Add zero-g training or spacer traits that reduce microgravity penalties.
- [ ] Add specialized ship gravity profiles later: spin, microgravity, artificial, and hybrid.
- [ ] Generate the Sol system using realistic sourcing where available and realistic procedural generation where needed.
- [ ] Generate at least one landable city on Earth.
- [ ] Design and implement player skilling.
- [ ] Include survival, technical, tradesman, and piloting skill families.
- [ ] Design and implement NPC ships and denizens.
- [ ] Define a usable AI path for NPC ships and denizens.
- [ ] Generate NPC ship traffic reactively from generated POIs, player-created POIs, player organizations, Earth's planetary organization, and economic needs.
- [ ] Build a physicalized moving economy that players can interact with, prey on, and protect.
- [ ] Design and balance PC and NPC individual combat.
- [ ] Design and balance PC and NPC space combat.
- [ ] Add a general status effect system and mitigation paths.
- [ ] Design and implement player organizations.

## Design Direction

- [x] Default crewed ships should use acceleration-gravity thrust tower architecture.
- [x] Avoid common artificial gravity as the default ship assumption.
- [x] Treat the drive section as downship and the nose/command/sensor sections as upship under thrust.
- [x] Use simple gravity state abstraction instead of detailed room-by-room physics simulation.
- [x] Treat microgravity as an abnormal or contextual state, not constant friction for normal ship life.
- [x] Assume ship AI/autopilot usually plans comfortable thrust profiles and warns crew before routine burns.

## Design Questions

- [ ] Should manual ship capability overrides remain builder-only long-term, or become debug-only?
- [ ] How should sensor packages be acquired: builder command, vendor, crafting, loot, or shipyard service?
- [ ] Should survey datasets carry value based on tile count, resolution, novelty, body traits, hazards, or market demand?
- [ ] What should be the first playable loop for selling or sharing survey data?
- [ ] How much warning should players receive before routine thrust changes?
- [ ] Should docked ships normally be in microgravity?
- [ ] Should mag boots exist, and if so, are they common or specialized?
- [ ] Should crash couches be required for high-G maneuvers?
- [ ] Should engine restart during boarding be usable as a tactical anti-boarder action?
- [ ] How lethal should catastrophic maneuver events be?
- [ ] Should microgravity penalties affect NPCs and boarders equally?
- [ ] Should room descriptions dynamically change between thrust and microgravity states?
- [ ] What sources should be canonical for Sol system data, and how should gaps be procedurally filled?
- [ ] What is the first playable scope for Earth cities: single landing site, district map, or broader city generator?
- [ ] Should skills improve through use, training, instruction, implants/tools, or a hybrid model?
- [ ] How granular should survival, technical, tradesman, and piloting skills be?
- [ ] What NPC AI architecture is sufficient for ships, denizens, traffic, and economy without overbuilding?
- [ ] How physical should the economy be at first: route simulation, spawned cargo, actual inventory movement, or market abstraction?
- [ ] What kinds of player organizations are needed first: crews, companies, factions, settlements, or governments?

## Confirmed Working

- [x] System import and inspection.
- [x] Generated surface rooms.
- [x] Surface movement.
- [x] Landed ship overlays.
- [x] Ship embark/disembark.
- [x] Ship land/takeoff.
- [x] Canonical ship airlock.
- [x] Ship access roles.
- [x] Ship sensor packages and manual capability overrides.
- [x] Orbital survey scan.
- [x] Timed orbital band survey operations.
- [x] Survey semantic scan reports.
- [x] Survey coverage, datasets, cartridges, export, materialize, and load.
- [x] Survey map visual, brief, list, and detail.
- [x] Player `survey_map` preference.
- [x] Survey and surface migrations tracked and applied on the server.
- [x] `gameupdate` tracked as the server update helper.

## Server Notes

- Use `./gameupdate` on the server for normal git pull, Python compile, migration-plan check, and restart.
- Stop and inspect output before fake-applying migrations if Django reports existing tables.
- Generated world/system artifacts should stay untracked.
