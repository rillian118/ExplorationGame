# Staging Environment

Last verified: 2026-07-25

This document records the observed staging environment. It is an operational
snapshot, not a commitment to preserve every dependency version indefinitely.
Update it deliberately when the server runtime changes.

## Host and Runtime

- Hostname: `SpaceMUD-Dev`
- Operating system: Ubuntu 24.04.4 LTS
- Python: 3.12.3
- Evennia: 6.0.0
- Django: 6.0.5
- Twisted: 24.11.0
- PostgreSQL client/server family: 16
- Verified PostgreSQL client: 16.14

The exact installed Python package snapshot is recorded in
`requirements-staging.txt`.

## Deployment

- Game root: `/home/mud/games/exploration`
- Virtual environment: `/home/mud/games/evennia-env`
- Deployment branch: `systemgen`
- Systemd service: `exploration-mud.service`
- Service state when last verified: enabled and active
- Normal game update helper: `./gameupdate`

For a documentation-only fast-forward that does not require restart or
migrations:

```bash
sudo -u mud -H git -C /home/mud/games/exploration pull --ff-only origin systemgen
```

For normal code deployments, inspect `gameupdate` and use the documented
server workflow. Stop and investigate rather than fake-applying a migration
when Django reports that a table already exists.

## Audit Access

A dedicated non-root `codex-audit` account provides read-only access to the
source checkout. It has:

- No `sudo` access.
- No project write access.
- No access to secret settings or a project `.env`.
- No access to runtime log contents.
- Read access to the tracked `server/logs/README.md`.
- Permission to inspect public process and systemd status.

The checkout is registered as a Git safe directory only in the audit account's
personal Git configuration.

Do not commit SSH keys, passwords, environment files, database credentials, or
other operational secrets. Local agent SSH material is excluded through
`.gitignore`.

## Local Development Status

As of 2026-07-25, the Windows development computer does not have a usable
Python installation, pip, Evennia, or project virtual environment. Windows
Store placeholder executables exist for `python` and `python3`, but they cannot
run in the development environment.

Before relying on local compilation or tests:

1. Install a supported 64-bit Python 3.12 release.
2. Create a project-local virtual environment.
3. Install the verified dependency snapshot or a deliberately curated
   development requirements set.
4. Confirm Evennia imports successfully.
5. Add automated tests before treating local verification as comprehensive.
