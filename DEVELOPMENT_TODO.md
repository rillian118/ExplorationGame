# Exploration MUD Development Todo

Shared working list for future development stages. Keep entries concise and
move items forward as they are implemented, tested, or superseded.

## Now

- [ ] Pull and smoke-test the ship sensor package feature on the server.
- [ ] Verify `ship sensors packages`, `ship sensors install`, and `ship capabilities clear` in-game.
- [ ] Verify survey radius/resolution caps respond to installed sensor packages.

## Next

- [ ] Add richer survey scan progression beyond radius/resolution caps.
- [ ] Add survey target selection improvements.
- [ ] Add survey route/readout commands.
- [ ] Add dataset valuation metadata.
- [ ] Decide the first shape of survey data market/sale mechanics.

## Later

- [ ] Add cartridge transfer/copy/licensing rules.
- [ ] Add organization-owned survey archives.
- [ ] Add broader accessibility preferences.
- [ ] Add screen-reader verbosity settings.
- [ ] Add ANSI/color preference.
- [ ] Add room description verbosity preference.
- [ ] Expand ship interiors beyond the canonical airlock.
- [ ] Add sensor effects from damage, power allocation, crew skill, and environment.
- [ ] Make ship survey datasets extend to crew access where appropriate.
- [ ] Revisit survey dataset ownership so ship-generated data can be tied to the ship, not only the player.

## Design Questions

- [ ] Should manual ship capability overrides remain builder-only long-term, or become debug-only?
- [ ] How should sensor packages be acquired: builder command, vendor, crafting, loot, or shipyard service?
- [ ] Should survey datasets carry value based on tile count, resolution, novelty, body traits, hazards, or market demand?
- [ ] What should be the first playable loop for selling or sharing survey data?

## Confirmed Working

- [x] System import and inspection.
- [x] Generated surface rooms.
- [x] Surface movement.
- [x] Landed ship overlays.
- [x] Ship embark/disembark.
- [x] Ship land/takeoff.
- [x] Canonical ship airlock.
- [x] Ship access roles.
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
